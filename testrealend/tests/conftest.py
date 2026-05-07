import pytest
import os

# Set test environment before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'

from app import create_app
from extension.extension import db as _db


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60
    yield app


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        # Import all models to register them
        from model import (  # noqa: F401
            Adm_Account, Adm_Info, Employee_Account, Employee_Info,
            Application, Log_Info, Announcement, Download_Record,
        )
        # Create tables per bind, skipping models with unsupported column types
        for bind_key in app.config.get('SQLALCHEMY_BINDS', {}):
            try:
                _db.create_all(bind_key=bind_key)
            except Exception:
                # Fallback: create tables individually
                for mapper in _db.Model.registry.mappers:
                    model = mapper.class_
                    if getattr(model, '__bind_key__', None) == bind_key:
                        try:
                            engine = _db.session.get_bind(mapper=model)
                            model.__table__.create(bind=engine, checkfirst=True)
                        except Exception:
                            pass
        _seed_test_data(_db)
        yield _db
        _db.session.rollback()


def _seed_test_data(db):
    """Seed minimal test data for auth-dependent tests."""
    from werkzeug.security import generate_password_hash
    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo
    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo

    # Check if already seeded
    if AdmAccount.query.filter_by(adm_user_name='admin1').first():
        return

    # Admin info (must exist before account due to FK)
    admin_info = AdmInfo(
        adm_number='admin1',
        name='管理员1',
        job_number='ADM001',
        id_number='ID001',
        phone_number='13800000001',
        address='Test Address'
    )
    db.session.add(admin_info)
    db.session.flush()

    admin = AdmAccount(
        adm_user_name='admin1',
        adm_user_password=generate_password_hash('admin123'),
        role='admin',
        adm_number='admin1'
    )
    db.session.add(admin)

    # Employee info (must exist before account due to FK)
    emp_info = EmployeeInfo(
        employee_number='E001',
        name='员工1',
        job_number='EMP001',
        id_number='ID002',
        phone_number='13800000002',
        address='Test Address'
    )
    db.session.add(emp_info)
    db.session.flush()

    emp = EmployeeAccount(
        employee_user_name='employee1',
        employee_user_password=generate_password_hash('emp123'),
        role='employee',
        employee_number='E001'
    )
    db.session.add(emp)

    db.session.commit()


@pytest.fixture
def auth_headers(client, db):
    """Get authenticated headers by logging in as admin."""
    response = client.post('/api/login', json={
        'username': 'admin1',
        'password': 'admin123',
        'role': 'admin'
    })
    if response.status_code == 200:
        data = response.get_json()
        return {'Authorization': f'Bearer {data["access_token"]}'}
    return {}


@pytest.fixture
def employee_headers(client, db):
    """Get authenticated headers by logging in as employee."""
    response = client.post('/api/login', json={
        'username': 'employee1',
        'password': 'emp123',
        'role': 'employee'
    })
    if response.status_code == 200:
        data = response.get_json()
        return {'Authorization': f'Bearer {data["access_token"]}'}
    return {}
