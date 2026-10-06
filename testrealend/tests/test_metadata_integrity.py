"""Metadata integrity and insert-order regression tests.

Guards the E2E finding that POST /api/adm/add_employee returned 500 on
FK-enforcing MySQL (employee_account_ibfk_1): two FK targets in the
mysql_db MetaData were unresolvable - "permissions.id" was miscased vs
Permission.__tablename__ == "Permissions", and "data.id" was dangling
(no such table in any bind). That poisoned metadata.sorted_tables, and the
endpoint additionally relied on implicit flush ordering instead of pinning
the parent EmployeeInfo row before inserting its account.
"""

from sqlalchemy import event
from sqlalchemy.exc import NoReferencedTableError

from extension.extension import db as _db


class TestMetadataIntegrity:
    def test_all_foreign_key_targets_resolve_within_their_metadata(self, app):
        """Every ForeignKey must resolve to a table in its own bind MetaData."""
        with app.app_context():
            problems = []
            total = 0
            for bind_key, md in _db.metadatas.items():
                for tname in sorted(md.tables):
                    table = md.tables[tname]
                    for fk in sorted(table.foreign_keys, key=str):
                        total += 1
                        try:
                            # Resolving .column raises NoReferencedTableError when the
                            # FK target cannot be found in this same MetaData.
                            _ = fk.column
                        except NoReferencedTableError as exc:
                            problems.append(
                                f"bind={bind_key!r} {table.name}.{fk.parent.name} -> {fk.target_fullname}: {exc}"
                            )
            assert total > 0, "no foreign keys discovered - model registration regressed?"
            assert not problems, "Unresolvable ForeignKey targets:\n" + "\n".join(problems)

    def test_mysql_metadata_sorted_tables_parent_before_child(self, app):
        """metadata.sorted_tables must evaluate and rank employee tables parent-first."""
        with app.app_context():
            names = [t.name for t in _db.metadatas["mysql_db"].sorted_tables]
            assert names.index("employee_info") < names.index("employee_account")


class TestAddEmployeeWithEnforcedForeignKeyOrder:
    def test_add_employee_and_login_with_sqlite_fk_enforced(self, app, client, auth_headers):
        """POST /api/adm/add_employee with SQLite FK enforcement on must return 201,
        persist both rows, and the created account must be able to log in."""
        from model.Employee_Account import EmployeeAccount
        from model.Employee_Info import EmployeeInfo

        def _enable_fk_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        emp_number = "E2EFK001"
        password = "e2e-fk-pass"
        with app.app_context():
            engine = _db.engines["mysql_db"]
            event.listen(engine, "connect", _enable_fk_pragma)
            # Drop pooled connections opened before the pragma so the endpoint's
            # INSERTs run on FK-enforcing connections.
            engine.dispose()
            try:
                resp = client.post(
                    "/api/adm/add_employee",
                    headers=auth_headers,
                    data={
                        "employee_number": emp_number,
                        "name": "FK顺序回归员工",
                        "job_number": "E2EFKJOB001",
                        "id_number": "E2EFKID001",
                        "phone_number": "13900000099",
                        "address": "test-address",
                        "password": password,
                    },
                )
                assert resp.status_code == 201, resp.get_data(as_text=True)
                assert resp.get_json()["status"] is True
                assert EmployeeInfo.query.filter_by(employee_number=emp_number).first() is not None
                assert EmployeeAccount.query.filter_by(employee_user_name=emp_number).first() is not None

                login = client.post(
                    "/api/login",
                    json={"username": emp_number, "password": password, "role": "employee"},
                )
                assert login.status_code == 200, login.get_data(as_text=True)
                assert login.get_json().get("access_token")
            finally:
                # The endpoint commits its own transaction; remove the test rows
                # (child first - FK is enforced on this connection) to keep the
                # shared SQLite test DB clean for later tests.
                EmployeeAccount.query.filter_by(employee_user_name=emp_number).delete()
                EmployeeInfo.query.filter_by(employee_number=emp_number).delete()
                _db.session.commit()
                event.remove(engine, "connect", _enable_fk_pragma)
                # Drop pragma-enabled pooled connections so other tests keep the
                # default FK-off behavior they were written against.
                engine.dispose()
