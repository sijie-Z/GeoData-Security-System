import os

import pytest
from sqlalchemy.engine import make_url

# Set test environment before importing app
os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"

from config import BASE_DIR, TestingConfig


def _delete_stale_sqlite_test_databases():
    """Delete file-backed SQLite test databases so every run starts clean.

    Must run BEFORE `app` is imported: importing app.py builds an app instance
    at module level, whose engines open pooled connections to instance/test.db
    and on Windows keep the file locked, so it could never be removed later.
    Stale rows from a previous run otherwise break the next one (UNIQUE
    constraint violations, dashboard date aggregation crashes).
    """
    instance_path = os.path.join(BASE_DIR, "instance")
    os.makedirs(instance_path, exist_ok=True)
    for uri in TestingConfig.SQLALCHEMY_BINDS.values():
        url = make_url(str(uri))
        if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
            continue
        path = url.database
        if not os.path.isabs(path):
            path = os.path.join(instance_path, path)
        path = os.path.normpath(path)
        for candidate in (path, f"{path}-journal", f"{path}-wal", f"{path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


_delete_stale_sqlite_test_databases()

from app import create_app
from extension.extension import db as _db


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 60
    yield app


@pytest.fixture(scope="function")
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        # Import all models to register them
        # Create tables per bind, skipping models with unsupported column types
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            try:
                _db.create_all(bind_key=bind_key)
            except Exception:
                # Fallback: create tables individually
                for mapper in _db.Model.registry.mappers:
                    model = mapper.class_
                    if getattr(model, "__bind_key__", None) == bind_key:
                        try:
                            engine = _db.session.get_bind(mapper=model)
                            model.__table__.create(bind=engine, checkfirst=True)
                        except Exception:
                            pass
        _seed_test_data(_db)
        yield _db
        _db.session.rollback()


@pytest.fixture(autouse=True)
def _allow_pytest_temp_roots(tmp_path_factory, monkeypatch, request):
    """Treat pytest's temp tree as an allowed data root for the test suite.

    The download / personalized-delivery / raster layers now open files only
    inside ``utils.path_guard.allowed_roots()`` (configured storage folders +
    ``runtime/``). The long-standing fixtures build their source files under
    pytest's temp directories instead of the configured folders, so the temp
    tree is injected as an extra root here. Tests that assert real out-of-root
    rejection opt out with ``@pytest.mark.strict_path_roots`` and keep observing
    the production root set.
    """
    if request.node.get_closest_marker("strict_path_roots"):
        return

    from utils import path_guard

    temp_root = str(tmp_path_factory.getbasetemp())
    original_allowed_roots = path_guard.allowed_roots

    def _roots_with_pytest_temp():
        roots = list(original_allowed_roots())
        if temp_root not in roots:
            roots.append(temp_root)
        return roots

    monkeypatch.setattr(path_guard, "allowed_roots", _roots_with_pytest_temp)


def _seed_test_data(db):
    """Seed minimal test data for auth-dependent tests."""
    from werkzeug.security import generate_password_hash

    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo
    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo

    # Check if already seeded
    if AdmAccount.query.filter_by(adm_user_name="admin1").first():
        return

    # Admin info (must exist before account due to FK)
    admin_info = AdmInfo(
        adm_number="admin1",
        name="管理员1",
        job_number="ADM001",
        id_number="ID001",
        phone_number="13800000001",
        address="Test Address",
    )
    db.session.add(admin_info)
    db.session.flush()

    admin = AdmAccount(
        adm_user_name="admin1", adm_user_password=generate_password_hash("admin123"), role="admin1", adm_number="admin1"
    )
    db.session.add(admin)

    # Admin2 info and account (for adm2 approval tests)
    admin2_info = AdmInfo(
        adm_number="admin2",
        name="管理员2",
        job_number="ADM002",
        id_number="ID003",
        phone_number="13800000003",
        address="Test Address",
    )
    db.session.add(admin2_info)
    db.session.flush()

    admin2 = AdmAccount(
        adm_user_name="admin2", adm_user_password=generate_password_hash("admin123"), role="admin2", adm_number="admin2"
    )
    db.session.add(admin2)

    # Admin3 info and account (for adm3-only endpoints such as vector extract)
    admin3_info = AdmInfo(
        adm_number="admin3",
        name="管理员3",
        job_number="ADM003",
        id_number="ID004",
        phone_number="13800000004",
        address="Test Address",
    )
    db.session.add(admin3_info)
    db.session.flush()

    admin3 = AdmAccount(
        adm_user_name="admin3", adm_user_password=generate_password_hash("admin123"), role="admin3", adm_number="admin3"
    )
    db.session.add(admin3)

    # Employee info (must exist before account due to FK)
    emp_info = EmployeeInfo(
        employee_number="E001",
        name="员工1",
        job_number="EMP001",
        id_number="ID002",
        phone_number="13800000002",
        address="Test Address",
    )
    db.session.add(emp_info)
    db.session.flush()

    emp = EmployeeAccount(
        employee_user_name="employee1",
        employee_user_password=generate_password_hash("emp123"),
        role="employee",
        employee_number="E001",
    )
    db.session.add(emp)

    db.session.commit()


@pytest.fixture
def auth_headers(client, db):
    """Get authenticated headers by logging in as admin."""
    response = client.post("/api/login", json={"username": "admin1", "password": "admin123", "role": "admin"})
    if response.status_code == 200:
        data = response.get_json()
        return {"Authorization": f"Bearer {data['access_token']}"}
    return {}


@pytest.fixture
def adm2_headers(client, db):
    """Get authenticated headers by logging in as admin2."""
    response = client.post("/api/login", json={"username": "admin2", "password": "admin123", "role": "admin"})
    if response.status_code == 200:
        data = response.get_json()
        return {"Authorization": f"Bearer {data['access_token']}"}
    return {}


@pytest.fixture
def adm3_headers(client, db):
    """Get authenticated headers by logging in as admin3."""
    response = client.post("/api/login", json={"username": "admin3", "password": "admin123", "role": "admin"})
    if response.status_code == 200:
        data = response.get_json()
        return {"Authorization": f"Bearer {data['access_token']}"}
    return {}


@pytest.fixture
def employee_headers(client, db):
    """Get authenticated headers by logging in as employee."""
    response = client.post("/api/login", json={"username": "employee1", "password": "emp123", "role": "employee"})
    if response.status_code == 200:
        data = response.get_json()
        return {"Authorization": f"Bearer {data['access_token']}"}
    return {}
