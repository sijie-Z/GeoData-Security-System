"""Seed a FLASK_ENV=testing SQLite database for the CI axe a11y job.

Replicates the minimal setup from ``tests/conftest.py``:
  * delete stale file-backed SQLite test databases BEFORE importing app.py
    (importing app.py builds an app at module level whose engines keep file
    handles open — on Windows the file could then never be removed);
  * create all tables per SQLAlchemy bind, falling back to per-model creation
    for models whose column types SQLite cannot compile;
  * seed one admin (admin / admin123, sub-role admin1) and one employee
    (TEST001 / test123456) so the a11y-smoke script can log in.

Usage (from testrealend/):
    FLASK_ENV=testing SECRET_KEY=ci-a11y-secret JWT_SECRET_KEY=ci-a11y-jwt-secret \
        python scripts/ci_seed.py

Idempotent: re-running only fills in missing accounts.
"""

import os
import sys

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "ci-a11y-secret")
os.environ.setdefault("JWT_SECRET_KEY", "ci-a11y-jwt-secret")

# Running `python scripts/ci_seed.py` puts scripts/ (not testrealend/) on
# sys.path; put the backend root first so `config`/`app` resolve to this repo
# (there is an unrelated `config` package installed in some Python envs).
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from sqlalchemy.engine import make_url

from config import BASE_DIR, TestingConfig


def _delete_stale_sqlite_test_databases():
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

# Importing app executes app.py's module-level create_app() exactly like
# tests/conftest.py does; call create_app() again for the seeding session.
from app import create_app
from extension.extension import db as _db


def _create_all_tables(app):
    with app.app_context():
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            try:
                _db.create_all(bind_key=bind_key)
            except Exception:
                # Fallback: create tables individually, skipping unsupported types.
                for mapper in _db.Model.registry.mappers:
                    model = mapper.class_
                    if getattr(model, "__bind_key__", None) == bind_key:
                        try:
                            engine = _db.session.get_bind(mapper=model)
                            model.__table__.create(bind=engine, checkfirst=True)
                        except Exception:
                            pass


def _seed(app):
    from werkzeug.security import generate_password_hash

    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo
    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo

    with app.app_context():
        created_admin = False
        if not AdmAccount.query.filter_by(adm_user_name="admin").first():
            _db.session.add(
                AdmInfo(
                    adm_number="admin",
                    name="CI 管理员",
                    job_number="ADM001",
                    id_number="ID001",
                    phone_number="13800000001",
                    address="CI Address",
                )
            )
            _db.session.flush()
            _db.session.add(
                AdmAccount(
                    adm_user_name="admin",
                    adm_user_password=generate_password_hash("admin123"),
                    role="admin1",
                    adm_number="admin",
                )
            )
            created_admin = True

        created_employee = False
        if not EmployeeAccount.query.filter_by(employee_user_name="TEST001").first():
            _db.session.add(
                EmployeeInfo(
                    employee_number="TEST001",
                    name="CI 员工",
                    job_number="EMP001",
                    id_number="ID002",
                    phone_number="13800000002",
                    address="CI Address",
                )
            )
            _db.session.flush()
            _db.session.add(
                EmployeeAccount(
                    employee_user_name="TEST001",
                    employee_user_password=generate_password_hash("test123456"),
                    role="employee",
                    employee_number="TEST001",
                )
            )
            created_employee = True

        _db.session.commit()

        admins = AdmAccount.query.count()
        employees = EmployeeAccount.query.count()

    print(
        f"[ci_seed] OK: admins={admins} employees={employees} "
        f"(created admin={created_admin}, employee={created_employee}) db={app.config.get('SQLALCHEMY_DATABASE_URI')}"
    )


def main():
    app = create_app()
    app.config["TESTING"] = True
    _create_all_tables(app)
    _seed(app)
    return 0


if __name__ == "__main__":
    sys.exit(main())
