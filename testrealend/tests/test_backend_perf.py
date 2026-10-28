"""Wave 6 · backend performance & operations hardening.

Covers the dependency upper bounds, the new download/audit indexes + migration
declarations, the forensics deliveries list N+1 batch (constant query count),
the 503 announcement outage contract, fail-closed password verification, and
the §0 security follow-ups (registration prechecks, refresh account recheck,
legacy download audit, concurrent logout, strict boolean review status).
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy import func, inspect

from config import BASE_DIR
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo
from model.anchor_record import AnchorRecord
from model.Application import Application
from model.download_delivery import DownloadDelivery
from model.Download_Record import DownloadRecord
from model.Employee_Account import EmployeeAccount
from model.Employee_Info import EmployeeInfo
from model.evidence_event import EvidenceEvent


@pytest.fixture(autouse=True)
def _cleanup_perf_rows(db):
    """Keep wave-6 tests out of the shared file-backed test database.

    Later suites aggregate row counts (download-stats top-10, forensics list),
    so every Application / delivery / evidence / anchor / download row created
    by this module is deleted when the test finishes. Admin rows have string
    primary keys, so they are removed via their autoincrement account ids.
    """
    max_app = db.session.query(func.max(Application.id)).scalar() or 0
    max_delivery = db.session.query(func.max(DownloadDelivery.delivery_id)).scalar() or 0
    max_event = db.session.query(func.max(EvidenceEvent.id)).scalar() or 0
    max_anchor = db.session.query(func.max(AnchorRecord.id)).scalar() or 0
    max_record = db.session.query(func.max(DownloadRecord.id)).scalar() or 0
    max_admin = db.session.query(func.max(AdmAccount.id)).scalar() or 0
    yield
    admin_numbers = [row[0] for row in db.session.query(AdmAccount.adm_number).filter(AdmAccount.id > max_admin)]
    DownloadRecord.query.filter(DownloadRecord.id > max_record).delete(synchronize_session=False)
    EvidenceEvent.query.filter(EvidenceEvent.id > max_event).delete(synchronize_session=False)
    AnchorRecord.query.filter(AnchorRecord.id > max_anchor).delete(synchronize_session=False)
    DownloadDelivery.query.filter(DownloadDelivery.delivery_id > max_delivery).delete(synchronize_session=False)
    Application.query.filter(Application.id > max_app).delete(synchronize_session=False)
    AdmAccount.query.filter(AdmAccount.id > max_admin).delete(synchronize_session=False)
    if admin_numbers:
        AdmInfo.query.filter(AdmInfo.adm_number.in_(admin_numbers)).delete(synchronize_session=False)
    # The delete-account refresh test removes its account before this cleanup;
    # its info row (only this module uses the ADM- number prefix) still goes.
    AdmInfo.query.filter(AdmInfo.adm_number.like("ADM-%")).delete(synchronize_session=False)
    db.session.commit()


def _uniq(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _admin_form(username, password="Passw0rd1"):
    return {
        "name": "管理员预检",
        "employeeId": username,
        "idNumber": _uniq("ID"),
        "phone": "137" + str(uuid.uuid4().int)[:8],
        "password": password,
    }


def _seed_admin(db, username, stored_password):
    """Create an admin info/account pair with an exact stored password value."""
    number = _uniq("ADM")
    info = AdmInfo(
        adm_number=number,
        name=_uniq("管理员"),
        job_number=_uniq("ADMJOB"),
        id_number=_uniq("ADMID"),
        phone_number="137" + str(uuid.uuid4().int)[:8],
        address="Test",
    )
    db.session.add(info)
    db.session.flush()
    db.session.add(
        AdmAccount(
            adm_user_name=username,
            adm_user_password=stored_password,
            role="admin1",
            adm_number=number,
        )
    )
    db.session.commit()
    return number


def _seed_application(db, **overrides):
    values = {
        "data_id": 501,
        "data_name": "perf-data",
        "data_alias": "perf-data",
        "data_type": "vector",
        "applicant_name": "员工1",
        "applicant_user_number": "E001",
        "reason": "perf test",
        "adm1_statu": True,
        "adm2_statu": True,
        "application_submission_time": datetime.now(UTC) - timedelta(days=30),
    }
    values.update(overrides)
    item = Application(**values)
    db.session.add(item)
    db.session.commit()
    return item


# --------------------------------------------------------------------------- #
# A · dependency upper bounds                                                  #
# --------------------------------------------------------------------------- #


def test_requirements_pin_major_versions():
    with open(os.path.join(BASE_DIR, "requirements.txt"), encoding="utf-8") as fh:
        lines = [line.strip() for line in fh if line.strip() and not line.lstrip().startswith("#")]
    joined = "\n".join(lines)
    assert "openai>=2.44.0,<3" in joined
    assert "pandas>=3.0.6,<3.1" in joined
    assert "numpy<3" in joined
    assert "pillow<14" in joined


# --------------------------------------------------------------------------- #
# B · indexes + migration declarations                                         #
# --------------------------------------------------------------------------- #


def test_model_indexes_exist_on_mysql_bind(db):
    inspector = inspect(db.get_engine(bind="mysql_db"))
    download_indexes = {index["name"] for index in inspector.get_indexes("download_record")}
    assert {
        "ix_download_record_timestamp",
        "ix_download_record_application_id",
        "ix_download_record_download_user_number",
        "ix_download_record_data_id",
    } <= download_indexes
    for table in ("download_token", "embed_file_record", "send_file_record"):
        names = {index["name"] for index in inspector.get_indexes(table)}
        assert f"ix_{table}_application_id" in names


def test_migration_declares_the_same_indexes():
    from migrate_add_columns import MYSQL_ALTERS

    joined = "\n".join(MYSQL_ALTERS)
    for name in (
        "ix_download_record_timestamp",
        "ix_download_record_application_id",
        "ix_download_record_download_user_number",
        "ix_download_record_data_id",
        "ix_download_token_application_id",
        "ix_embed_file_record_application_id",
        "ix_send_file_record_application_id",
    ):
        assert f"CREATE INDEX {name}" in joined


# --------------------------------------------------------------------------- #
# C · forensics deliveries list is a constant number of queries                #
# --------------------------------------------------------------------------- #


def test_deliveries_list_query_count_stays_constant(db, client, auth_headers):
    from tests.test_forensics_api import _seed_delivery

    item = _seed_application(db, data_alias="perf-list")
    deliveries = [_seed_delivery(db, item, user="E001") for _ in range(8)]
    db.session.add(
        DownloadRecord(
            application_id=item.id,
            delivery_id=deliveries[0].delivery_id,
            data_id=item.data_id,
            data_name=item.data_name,
            download_user_number="E001",
            download_ip="1.2.3.4",
            applicant_user_number="E001",
            filename="artifact.zip",
        )
    )
    db.session.add(
        AnchorRecord(
            batch_id=_uniq("batch"),
            root_hex="0" * 64,
            provider="ots",
            status="SUBMITTED",
            created_at=datetime.now(UTC) + timedelta(seconds=5),
        )
    )
    db.session.commit()

    statements = []
    engine = db.get_engine(bind="mysql_db")

    def _capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    sa_event.listen(engine, "before_cursor_execute", _capture)
    try:
        resp = client.get(f"/api/forensics/deliveries?application_id={item.id}", headers=auth_headers)
    finally:
        sa_event.remove(engine, "before_cursor_execute", _capture)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    rows = resp.get_json()["deliveries"]
    assert len(rows) == 8
    selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
    # 1 blacklist + deliveries + anchors + downloaded flags + events + keys = 6.
    # The pre-wave-6 loop ran ~5 queries per delivery (41 for this seed).
    assert len(selects) <= 8, selects

    by_uuid = {row["uuid"]: row for row in rows}
    for delivery in deliveries:
        row = by_uuid[delivery.uuid]
        assert row["chain"] == {"valid": True, "length": 1}
        assert row["anchor"]["status"] == "SUBMITTED"
        assert row["anchor"]["batch_id"]
        assert row["downloaded"] is (delivery.delivery_id == deliveries[0].delivery_id)


# --------------------------------------------------------------------------- #
# D · outage semantics + fail-closed password verification                     #
# --------------------------------------------------------------------------- #


def test_announcements_db_error_returns_503(client, auth_headers, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    import resource.announcement_resource as announcement_resource

    def _boom():
        raise SQLAlchemyError("database down")

    monkeypatch.setattr(announcement_resource, "_ensure_announcement_table", _boom)
    resp = client.get("/api/announcements", headers=auth_headers)
    assert resp.status_code == 503, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] is False
    assert "不可用" in body["msg"]


def test_malformed_hash_never_falls_back_to_plaintext(client, db):
    username = _uniq("legacy-admin")
    stored = "argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"
    _seed_admin(db, username, stored)

    resp = client.post("/api/login", json={"username": username, "password": stored, "role": "admin"})
    assert resp.status_code == 401, resp.get_data(as_text=True)
    assert resp.get_json()["status"] is False


def test_legacy_plaintext_login_still_upgrades(client, db):
    from werkzeug.security import check_password_hash

    username = _uniq("plain-admin")
    _seed_admin(db, username, "LegacyPass1")

    resp = client.post("/api/login", json={"username": username, "password": "LegacyPass1", "role": "admin"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    account = AdmAccount.query.filter_by(adm_user_name=username).first()
    assert account.adm_user_password != "LegacyPass1"
    assert check_password_hash(account.adm_user_password, "LegacyPass1")


# --------------------------------------------------------------------------- #
# E① · registration prechecks                                                  #
# --------------------------------------------------------------------------- #


class TestRegistrationPrechecks:
    def test_admin_number_collision_returns_400(self, client, db):
        resp = client.post("/api/register", data=_admin_form("admin1"))
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "管理员" in resp.get_json()["msg"]

    def test_existing_job_number_returns_400(self, client, db):
        job_number = _uniq("JOB")
        info = EmployeeInfo(
            employee_number=_uniq("EMP"),
            name="占用工号",
            job_number=job_number,
            id_number=_uniq("ID"),
            phone_number="137" + str(uuid.uuid4().int)[:8],
            address="Test",
        )
        db.session.add(info)
        db.session.commit()

        data = _admin_form(job_number)
        resp = client.post("/api/register", data=data)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "工号" in resp.get_json()["msg"]

    def test_existing_account_username_returns_400(self, client, db):
        employee_number = _uniq("EMP")
        username = _uniq("USER")
        info = EmployeeInfo(
            employee_number=employee_number,
            name="占用账号名",
            job_number=_uniq("JOB"),
            id_number=_uniq("ID"),
            phone_number="137" + str(uuid.uuid4().int)[:8],
            address="Test",
        )
        db.session.add(info)
        db.session.flush()
        db.session.add(
            EmployeeAccount(
                employee_user_name=username,
                employee_user_password="pbkdf2:sha256:600000$salt$hash",
                employee_number=employee_number,
                role="employee",
            )
        )
        db.session.commit()

        resp = client.post("/api/register", data=_admin_form(username))
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "账号名" in resp.get_json()["msg"]


# --------------------------------------------------------------------------- #
# E② · refresh rechecks the account behind the role claim                       #
# --------------------------------------------------------------------------- #


class TestRefreshAccountRecheck:
    @staticmethod
    def _login_refresh_token(client, username, password="Passw0rd1"):
        resp = client.post("/api/login", json={"username": username, "password": password, "role": "admin"})
        assert resp.status_code == 200, resp.get_data(as_text=True)
        return resp.get_json()["refresh_token"]

    def test_refresh_after_account_deleted_returns_401(self, client, db):
        username = _uniq("refresh-del")
        _seed_admin(db, username, "Passw0rd1")
        token = self._login_refresh_token(client, username)

        AdmAccount.query.filter_by(adm_user_name=username).delete(synchronize_session=False)
        db.session.commit()

        resp = client.post("/api/refresh-token", json={"refresh_token": token})
        assert resp.status_code == 401, resp.get_data(as_text=True)
        assert resp.get_json()["status"] is False

    def test_refresh_after_role_change_returns_401(self, client, db):
        username = _uniq("refresh-role")
        _seed_admin(db, username, "Passw0rd1")
        token = self._login_refresh_token(client, username)

        account = AdmAccount.query.filter_by(adm_user_name=username).first()
        account.role = "admin2"
        db.session.commit()

        resp = client.post("/api/refresh-token", json={"refresh_token": token})
        assert resp.status_code == 401, resp.get_data(as_text=True)

    def test_legacy_identity_without_role_claim_still_refreshes(self, client, app):
        from flask_jwt_extended import create_refresh_token

        with app.app_context():
            legacy = create_refresh_token(identity={"number": "E-LEGACY-R6", "username": "legacy-r6"})
        resp = client.post("/api/refresh-token", json={"refresh_token": legacy})
        assert resp.status_code == 200, resp.get_data(as_text=True)


# --------------------------------------------------------------------------- #
# E③ · server-side download audit fields                                      #
# --------------------------------------------------------------------------- #


class TestDownloadAuditFields:
    def test_emp_download_zip_writes_download_record(self, client, db, employee_headers, tmp_path):
        payload = tmp_path / "perf.bin"
        payload.write_bytes(b"PERF-DOWNLOAD")
        item = _seed_application(
            db,
            data_id=7331,
            data_name="legacy-zip",
            watermark_path=str(payload),
        )

        resp = client.post("/api/emp_download_zip", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.data == b"PERF-DOWNLOAD"

        record = DownloadRecord.query.filter_by(application_id=item.id).first()
        assert record is not None
        assert record.data_id == 7331
        assert record.data_name == "legacy-zip"
        assert record.download_user_number == "E001"
        assert record.filename == "perf.bin"

    def test_record_download_file_ignores_client_data_id(self, client, db, employee_headers):
        item = _seed_application(db, data_id=4242, data_name="server-name")
        resp = client.post(
            "/api/record_download_file",
            headers=employee_headers,
            json={
                "application_id": item.id,
                "data_id": 999999,
                "dataName": "client-name",
                "fileName": "claimed.zip",
            },
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)

        record = DownloadRecord.query.filter_by(application_id=item.id).order_by(DownloadRecord.id.desc()).first()
        assert record.data_id == 4242
        assert record.data_name == "server-name"
        assert record.filename == "claimed.zip"


# --------------------------------------------------------------------------- #
# E④/E⑤ · concurrent logout + strict boolean review status                     #
# --------------------------------------------------------------------------- #


def test_concurrent_logout_integrity_error_is_idempotent(client, db, auth_headers, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    def _boom():
        raise IntegrityError(
            "INSERT INTO token_blacklist", {}, Exception("UNIQUE constraint failed: token_blacklist.jti")
        )

    monkeypatch.setattr(db.session, "commit", _boom)
    resp = client.post("/api/logout", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["status"] is True


@pytest.mark.parametrize("bad_statu", ["true", 1, None, "False", []])
def test_re_review_rejects_non_boolean_statu(client, adm2_headers, bad_statu):
    resp = client.post(
        "/api/admin/re_review",
        headers=adm2_headers,
        json={"id": 1, "stage": "adm2", "statu": bad_statu},
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)
    assert resp.get_json()["status"] is False


@pytest.mark.parametrize("bad_statu", ["true", 1, None, "False", {}])
def test_adm3_additional_review_rejects_non_boolean_statu(client, adm3_headers, bad_statu):
    resp = client.post(
        "/api/adm3_additional_review",
        headers=adm3_headers,
        json={"id": 1, "statu": bad_statu},
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)
    assert resp.get_json()["status"] is False
