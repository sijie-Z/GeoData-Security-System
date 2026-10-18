"""Authorization round 2 — owner/admin gates, sub-role isolation, revocation.

Covers the 2026-10 audit findings:

* high risk: ``emp_download_zip`` / ``request_download_token`` (application
  ownership), ``GET /api/applications/<id>`` + QR endpoints (PII), destructive
  data deletion;
* medium risk: data-management admin gate, watermark forensics surface, forged
  download-audit rows, CRMark arbitrary-path reads, review sub-role isolation,
  cross-role admin nav menus;
* session/key hardening: refresh-token revocation on logout, strict JWT role
  claims (no DB fallback for explicit non-admin roles), random per-process
  secrets when none are configured.

Every fixed endpoint has at least one "must be denied" and one "legitimate
call still works" case, so the fixes cannot silently break the normal flows of
employees, adm1/adm2/adm3 or the super admin.
"""

import base64
import io
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEGACY_SECRET_DEFAULTS = {
    "dev-only-key-replace-in-production",
    "dev-only-jwt-key-replace-in-production",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _seed_application(
    db,
    applicant="E001",
    alias=None,
    adm1_statu=True,
    adm2_statu=True,
    qrcode=None,
    data_type="vector",
    applicant_name=None,
    watermark_path=None,
):
    """Insert an Application row.

    ``application_submission_time`` is backdated so these rows never leak into
    the dashboard date aggregations asserted by test_dashboard.py.
    """
    from model.Application import Application

    alias = alias or f"authz2-{uuid.uuid4().hex[:10]}"
    item = Application(
        data_id=1,
        data_name=alias,
        data_alias=alias,
        data_type=data_type,
        applicant_name=applicant_name or ("员工1" if applicant == "E001" else "员工2"),
        applicant_user_number=applicant,
        reason="authz round2",
        adm1_statu=adm1_statu,
        adm2_statu=adm2_statu,
        qrcode=qrcode,
        watermark_path=watermark_path,
        application_submission_time=datetime.now(UTC) - timedelta(days=30),
    )
    db.session.add(item)
    db.session.commit()
    return item


def _png_b64(size=8, color=(30, 60, 90)):
    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def employee2_headers(client, db):
    """A second regular employee (the conftest only seeds employee1/E001)."""
    from werkzeug.security import generate_password_hash

    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo

    number = "E002AUTHZ"
    username = "employee2_authz2"
    if not EmployeeInfo.query.filter_by(employee_number=number).first():
        db.session.add(
            EmployeeInfo(
                employee_number=number,
                name="员工2",
                job_number="EMP002AUTHZ",
                id_number="IDAUTHZR2E2",
                phone_number="19900000002",
                address="Test Address",
            )
        )
        db.session.commit()
    if not EmployeeAccount.query.filter_by(employee_user_name=username).first():
        db.session.add(
            EmployeeAccount(
                employee_user_name=username,
                employee_user_password=generate_password_hash("emp123"),
                role="employee",
                employee_number=number,
            )
        )
        db.session.commit()
    resp = client.post("/api/login", json={"username": username, "password": "emp123", "role": "employee"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def superadmin_headers(client, db):
    """A ``role='admin'`` super-admin token that must pass every admin gate.

    Minted directly instead of inserting an ``AdmAccount`` row: the shared test
    DB is reused across the whole suite and recall-vote thresholds count
    ``AdmAccount`` rows, so extra admin accounts would contaminate test_recall.
    """
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity={
                "username": "superadmin_authz2",
                "name": "超级管理员2",
                "role": "admin",
                "number": "S2AUTHZ",
            }
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def downloadable_app(db, tmp_path):
    """An approved application owned by E001 backed by a real file."""
    payload = tmp_path / "authz2_download.bin"
    payload.write_bytes(b"AUTHZ2-DOWNLOAD-PAYLOAD")
    item = _seed_application(db, applicant="E001", watermark_path=str(payload))
    return item, payload


@pytest.fixture
def make_vector(db):
    """Factory for throwaway Shp rows (data-management write endpoints)."""
    from model.Shp_Data import Shp

    def _make():
        alias = f"authz2-vec-{uuid.uuid4().hex[:10]}"
        record = Shp(
            name=alias,
            alias=alias,
            geomtype="Point",
            introduction="authz round2",
            shp_file_path="runtime/authz2/test.shp",
        )
        db.session.add(record)
        db.session.commit()
        return record

    return _make


def _make_raster_application(db, directory):
    """An approved raster application backed by a real 256x256 PNG host."""
    from model.Raster_Data import RasterData

    host = os.path.join(str(directory), "authz2_host.png")
    Image.new("RGB", (256, 256), (100, 120, 140)).save(host, "PNG")
    alias = f"authz2-raster-{uuid.uuid4().hex[:8]}"
    record = RasterData(name=alias, alias=alias, raster_file_path=host, url="", layer="")
    db.session.add(record)
    db.session.commit()
    item = _seed_application(db, data_type="raster", qrcode=_png_b64(32))
    item.data_id = record.id
    db.session.commit()
    return item, host


# ─────────────────────────────────────────────────────────────────────────────
# §0.1/2 — download & token owner-or-admin
# ─────────────────────────────────────────────────────────────────────────────


class TestDownloadOwnership:
    def test_owner_can_download_own_application(self, client, db, employee_headers, downloadable_app):
        item, payload = downloadable_app
        resp = client.post("/api/emp_download_zip", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.data == payload.read_bytes()

    def test_other_employee_cannot_download(self, client, db, employee2_headers, downloadable_app):
        item, _ = downloadable_app
        resp = client.post("/api/emp_download_zip", json={"application_id": item.id}, headers=employee2_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_download_for_inspection(self, client, db, auth_headers, downloadable_app):
        item, payload = downloadable_app
        resp = client.post("/api/emp_download_zip", json={"application_id": item.id}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.data == payload.read_bytes()

    def test_owner_can_request_token(self, client, db, employee_headers, downloadable_app):
        item, _ = downloadable_app
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["token"]

    def test_other_employee_cannot_request_token(self, client, db, employee2_headers, downloadable_app):
        item, _ = downloadable_app
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee2_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_request_token(self, client, db, auth_headers, downloadable_app):
        item, _ = downloadable_app
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# §0.3 — application detail / QR PII is owner-or-admin
# ─────────────────────────────────────────────────────────────────────────────


class TestApplicationPII:
    @pytest.fixture
    def owned(self, db):
        return _seed_application(db, applicant="E001", qrcode=_png_b64())

    def test_owner_reads_detail(self, client, db, employee_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}", headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["data"]["applicant_user_number"] == "E001"

    def test_other_employee_cannot_read_detail(self, client, db, employee2_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}", headers=employee2_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_reads_detail(self, client, db, auth_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_owner_reads_qrcode(self, client, db, employee_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}/qrcode", headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["data"]["qrcode"]

    def test_other_employee_cannot_read_qrcode(self, client, db, employee2_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}/qrcode", headers=employee2_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_reads_qrcode(self, client, db, auth_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}/qrcode", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_owner_reads_qrcode_image(self, client, db, employee_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}/qrcode/image", headers=employee_headers)
        assert resp.status_code == 200
        assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_other_employee_cannot_read_qrcode_image(self, client, db, employee2_headers, owned):
        resp = client.get(f"/api/applications/{owned.id}/qrcode/image", headers=employee2_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# §0.1 — forged download-audit rows
# ─────────────────────────────────────────────────────────────────────────────


class TestDownloadAudit:
    def test_owner_can_record_own_download(self, client, db, employee_headers):
        from model.Download_Record import DownloadRecord

        item = _seed_application(db, applicant="E001")
        resp = client.post(
            "/api/record_download_file",
            json={"application_id": item.id, "data_id": 1, "fileName": "x.zip"},
            headers=employee_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        record = DownloadRecord.query.filter_by(application_id=item.id).order_by(DownloadRecord.id.desc()).first()
        assert record is not None
        assert record.applicant_user_number == "E001"

    def test_other_employee_cannot_forge_audit_row(self, client, db, employee2_headers):
        from model.Download_Record import DownloadRecord

        item = _seed_application(db, applicant="E001")
        resp = client.post(
            "/api/record_download_file",
            json={"application_id": item.id, "data_id": 1, "fileName": "forged.zip"},
            headers=employee2_headers,
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)
        assert DownloadRecord.query.filter_by(application_id=item.id).first() is None

    def test_admin_can_record_on_behalf(self, client, db, auth_headers):
        item = _seed_application(db, applicant="E001")
        resp = client.post(
            "/api/record_download_file",
            json={"application_id": item.id, "data_id": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# §0.4 — destructive data management endpoints are admin-only
# ─────────────────────────────────────────────────────────────────────────────


class TestDataManagementAdminGate:
    def test_employee_cannot_update_data(self, client, db, employee_headers, make_vector):
        record = make_vector()
        resp = client.put(f"/api/data/vector/{record.id}", json={"alias": "hijacked"}, headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_update_data(self, client, db, auth_headers, make_vector):
        record = make_vector()
        new_alias = f"authz2-updated-{uuid.uuid4().hex[:8]}"
        resp = client.put(f"/api/data/vector/{record.id}", json={"alias": new_alias}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["data"]["data_alias"] == new_alias

    def test_employee_cannot_delete_data(self, client, db, employee_headers, make_vector):
        from model.Shp_Data import Shp

        record = make_vector()
        resp = client.delete(f"/api/data/vector/{record.id}/delete", headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)
        assert db.session.get(Shp, record.id) is not None

    def test_admin_can_delete_data(self, client, db, auth_headers, make_vector, monkeypatch):
        from model.Shp_Data import Shp

        record = make_vector()
        monkeypatch.setattr("utils.geoserver_utils.delete_layer", lambda layer: None)
        resp = client.delete(f"/api/data/vector/{record.id}/delete", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert db.session.get(Shp, record.id) is None

    def test_employee_cannot_upload_shp(self, client, db, employee_headers):
        resp = client.post("/api/upload_shp_data", data={}, headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_shp_upload_reaches_validation(self, client, db, auth_headers):
        resp = client.post("/api/upload_shp_data", data={}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_employee_cannot_upload_raster(self, client, db, employee_headers):
        resp = client.post("/api/upload_raster_data", data={}, headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_raster_upload_reaches_validation(self, client, db, auth_headers):
        resp = client.post("/api/upload_raster_data", data={}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_employee_cannot_publish_to_geoserver(self, client, db, employee_headers):
        resp = client.post(
            "/api/geoserver/publish", json={"data_type": "vector", "data_id": 1}, headers=employee_headers
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_publish_reaches_validation(self, client, db, auth_headers):
        resp = client.post("/api/geoserver/publish", json={}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# §0.2 — watermark forensics surface
# ─────────────────────────────────────────────────────────────────────────────


class TestWatermarkForensicsGate:
    def test_employee_cannot_list_verification_records(self, client, db, employee_headers):
        resp = client.get("/api/watermark/verification_records", headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_list_verification_records(self, client, db, auth_headers):
        resp = client.get("/api/watermark/verification_records", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_employee_cannot_upload_original_watermark(self, client, db, employee_headers):
        resp = client.post("/api/upload_original_watermark", data={}, headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_upload_original_reaches_validation(self, client, db, auth_headers):
        resp = client.post("/api/upload_original_watermark", data={}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_admin_can_upload_original_watermark(self, client, db, auth_headers):
        item = _seed_application(db)
        png = io.BytesIO()
        Image.new("L", (16, 16), 0).save(png, "PNG")
        png.seek(0)
        resp = client.post(
            "/api/upload_original_watermark",
            data={"application_id": str(item.id), "file": (png, "original.png")},
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["path"]

    def test_employee_cannot_upload_extracted_watermark(self, client, db, employee_headers):
        resp = client.post("/api/upload_extracted_watermark", data={}, headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_upload_extracted_reaches_validation(self, client, db, auth_headers):
        resp = client.post("/api/upload_extracted_watermark", data={}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_admin_can_upload_extracted_watermark(self, client, db, auth_headers):
        item = _seed_application(db, qrcode=_png_b64(16))
        png = io.BytesIO()
        Image.new("L", (16, 16), 0).save(png, "PNG")
        png.seek(0)
        resp = client.post(
            "/api/upload_extracted_watermark",
            data={"application_id": str(item.id), "file": (png, "extracted.png")},
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert "nc_value" in resp.get_json()

    def test_employee_cannot_compare_watermarks(self, client, db, employee_headers):
        resp = client.post("/api/upload/ori&ext_watermark", data={}, headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_compare_reaches_validation(self, client, db, auth_headers):
        resp = client.post("/api/upload/ori&ext_watermark", data={}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_owner_can_read_original_watermark(self, client, db, employee_headers):
        item = _seed_application(db, applicant="E001", qrcode=_png_b64())
        resp = client.post("/api/get_original_watermark", json={"number": item.id}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["original_watermark"]

    def test_other_employee_cannot_read_original_watermark(self, client, db, employee2_headers):
        item = _seed_application(db, applicant="E001", qrcode=_png_b64())
        resp = client.post("/api/get_original_watermark", json={"number": item.id}, headers=employee2_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_read_original_watermark(self, client, db, auth_headers):
        item = _seed_application(db, applicant="E001", qrcode=_png_b64())
        resp = client.post("/api/get_original_watermark", json={"number": item.id}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# §0.2 — CRMark arbitrary-path confinement
# ─────────────────────────────────────────────────────────────────────────────


def _make_dwt_artifacts(directory):
    """Create a real DWT stego + metadata pair inside *directory*."""
    from algorithm.raster_dwt_watermark import embed_dwt

    os.makedirs(directory, exist_ok=True)
    host_path = os.path.join(directory, "host.png")
    Image.new("RGB", (256, 256), (120, 130, 140)).save(host_path, "PNG")
    watermark = Image.new("L", (32, 32), 0)
    for y in range(0, 32, 2):
        for x in range(0, 32, 2):
            watermark.putpixel((x, y), 255)
    return embed_dwt(host_path, watermark, directory, "authz2")


class TestCRMarkPathConfinement:
    def test_recover_rejects_path_outside_roots(self, client, db, adm2_headers, tmp_path):
        from flask import current_app

        outside_dir = str(tmp_path / "outside")
        # Make the files real and readable — only the root check can reject them.
        result = _make_dwt_artifacts(outside_dir)
        assert not str(result["stego_path"]).startswith(current_app.root_path)
        resp = client.post(
            "/api/crmark/recover",
            json={"stego_path": result["stego_path"], "wm_meta_path": result["wm_meta_path"]},
            headers=adm2_headers,
        )
        assert resp.status_code == 404, resp.get_data(as_text=True)

    def test_decode_rejects_path_outside_roots(self, client, db, adm2_headers, tmp_path):
        outside_dir = str(tmp_path / "outside_decode")
        result = _make_dwt_artifacts(outside_dir)
        resp = client.post(
            "/api/crmark/decode",
            json={"stego_path": result["stego_path"], "wm_meta_path": result["wm_meta_path"]},
            headers=adm2_headers,
        )
        assert resp.status_code == 404, resp.get_data(as_text=True)

    def test_decode_allows_runtime_artifacts(self, client, db, adm2_headers):
        from flask import current_app

        runtime_dir = os.path.join(current_app.root_path, "runtime", "crmark", f"authz2-{uuid.uuid4().hex[:8]}")
        result = _make_dwt_artifacts(runtime_dir)
        resp = client.post(
            "/api/crmark/decode",
            json={"stego_path": result["stego_path"], "wm_meta_path": result["wm_meta_path"]},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_recover_allows_runtime_artifacts(self, client, db, adm2_headers):
        from flask import current_app

        runtime_dir = os.path.join(current_app.root_path, "runtime", "crmark", f"authz2r-{uuid.uuid4().hex[:8]}")
        result = _make_dwt_artifacts(runtime_dir)
        resp = client.post(
            "/api/crmark/recover",
            json={"stego_path": result["stego_path"], "wm_meta_path": result["wm_meta_path"]},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)


class TestCRMarkRoleGate:
    """CRMark recover/decode expose tenant stego/meta/original artifacts, so they
    carry the same adm2 gate as the embedding page that calls them
    (RasterWatermarkEmbedding, router adminRole 'adm2')."""

    DENIED_ROLE_FIXTURES = ("employee_headers", "auth_headers", "adm3_headers")

    @pytest.mark.parametrize("fixture_name", DENIED_ROLE_FIXTURES)
    def test_recover_requires_adm2(self, client, db, request, fixture_name):
        headers = request.getfixturevalue(fixture_name)
        resp = client.post("/api/crmark/recover", json={}, headers=headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    @pytest.mark.parametrize("fixture_name", DENIED_ROLE_FIXTURES)
    def test_decode_requires_adm2(self, client, db, request, fixture_name):
        headers = request.getfixturevalue(fixture_name)
        resp = client.post("/api/crmark/decode", json={}, headers=headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# §0.2 — review sub-role isolation
# ─────────────────────────────────────────────────────────────────────────────


class TestReviewSubRoleIsolation:
    def test_employee_cannot_batch_review(self, client, db, employee_headers):
        item = _seed_application(db, adm1_statu=None, adm2_statu=None)
        resp = client.post(
            "/api/admin/batch_review",
            json={"ids": [item.id], "stage": "adm1", "action": "pass"},
            headers=employee_headers,
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_adm1_can_batch_review_first_stage(self, client, db, auth_headers):
        from model.Application import Application

        item = _seed_application(db, adm1_statu=None, adm2_statu=None)
        resp = client.post(
            "/api/admin/batch_review",
            json={"ids": [item.id], "stage": "adm1", "action": "pass"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        db.session.expire_all()
        assert db.session.get(Application, item.id).adm1_statu is True

    def test_adm2_cannot_batch_review_first_stage(self, client, db, adm2_headers):
        item = _seed_application(db, adm1_statu=None, adm2_statu=None)
        resp = client.post(
            "/api/admin/batch_review",
            json={"ids": [item.id], "stage": "adm1", "action": "pass"},
            headers=adm2_headers,
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_adm1_cannot_batch_review_second_stage(self, client, db, auth_headers):
        item = _seed_application(db, adm1_statu=True, adm2_statu=None)
        resp = client.post(
            "/api/admin/batch_review",
            json={"ids": [item.id], "stage": "adm2", "action": "pass"},
            headers=auth_headers,
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_adm2_can_batch_review_second_stage(self, client, db, adm2_headers):
        from model.Application import Application

        item = _seed_application(db, adm1_statu=True, adm2_statu=None)
        resp = client.post(
            "/api/admin/batch_review",
            json={"ids": [item.id], "stage": "adm2", "action": "pass"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        db.session.expire_all()
        assert db.session.get(Application, item.id).adm2_statu is True

    def test_adm3_cannot_batch_review_either_stage(self, client, db, adm3_headers):
        item = _seed_application(db, adm1_statu=None, adm2_statu=None)
        for stage in ("adm1", "adm2"):
            resp = client.post(
                "/api/admin/batch_review",
                json={"ids": [item.id], "stage": stage, "action": "fail"},
                headers=adm3_headers,
            )
            assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_superadmin_passes_stage_gate(self, client, db, superadmin_headers):
        item = _seed_application(db, adm1_statu=None, adm2_statu=None)
        resp = client.post(
            "/api/admin/batch_review",
            json={"ids": [item.id], "stage": "adm1", "action": "pass"},
            headers=superadmin_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_adm1_cannot_re_review(self, client, db, auth_headers):
        item = _seed_application(db, adm1_statu=True, adm2_statu=None)
        resp = client.post(
            "/api/admin/re_review",
            json={"id": item.id, "stage": "adm2", "statu": True},
            headers=auth_headers,
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_adm2_can_re_review(self, client, db, adm2_headers):
        from model.Application import Application

        item = _seed_application(db, adm1_statu=True, adm2_statu=None)
        resp = client.post(
            "/api/admin/re_review",
            json={"id": item.id, "stage": "adm2", "statu": True},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        db.session.expire_all()
        assert db.session.get(Application, item.id).adm2_statu is True

    def test_employee_cannot_re_review(self, client, db, employee_headers):
        item = _seed_application(db, adm1_statu=True, adm2_statu=None)
        resp = client.post(
            "/api/admin/re_review",
            json={"id": item.id, "stage": "adm2", "statu": True},
            headers=employee_headers,
        )
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_crmark_embed_requires_adm2(self, client, db, employee_headers, auth_headers, adm2_headers, adm3_headers):
        for headers in (employee_headers, auth_headers, adm3_headers):
            resp = client.post("/api/crmark/embed", json={"application_id": 999999}, headers=headers)
            assert resp.status_code == 403, resp.get_data(as_text=True)
        # adm2 passes the gate and reaches the application lookup.
        resp = client.post("/api/crmark/embed", json={"application_id": 999999}, headers=adm2_headers)
        assert resp.status_code == 404, resp.get_data(as_text=True)

    def test_batch_embed_requires_adm2(self, client, db, employee_headers, auth_headers, adm2_headers, adm3_headers):
        for headers in (employee_headers, auth_headers, adm3_headers):
            resp = client.post("/api/watermark/batch_embed", json={"application_ids": []}, headers=headers)
            assert resp.status_code == 403, resp.get_data(as_text=True)
        resp = client.post("/api/watermark/batch_embed", json={"application_ids": []}, headers=adm2_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_batch_generate_requires_adm1(self, client, db, employee_headers, auth_headers, adm2_headers):
        for headers in (employee_headers, adm2_headers):
            resp = client.post("/api/watermark/batch_generate", json={"application_ids": []}, headers=headers)
            assert resp.status_code == 403, resp.get_data(as_text=True)
        resp = client.post("/api/watermark/batch_generate", json={"application_ids": []}, headers=auth_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)

    def test_adm1_batch_generate_succeeds(self, client, db, auth_headers):
        item = _seed_application(db)
        resp = client.post(
            "/api/watermark/batch_generate",
            json={"application_ids": [item.id], "reason": "authz2 smoke"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["summary"]["success"] == 1

    def test_adm2_crmark_embed_succeeds(self, client, db, adm2_headers, tmp_path):
        item, _ = _make_raster_application(db, tmp_path)
        resp = client.post("/api/crmark/embed", json={"application_id": item.id}, headers=adm2_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["stego_path"]

    def test_adm2_batch_embed_succeeds(self, client, db, adm2_headers, tmp_path):
        item, _ = _make_raster_application(db, tmp_path)
        resp = client.post("/api/watermark/batch_embed", json={"application_ids": [item.id]}, headers=adm2_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["summary"]["success"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# §0.2 — admin nav menus are not readable by employees
# ─────────────────────────────────────────────────────────────────────────────


class TestAdminNavGate:
    def test_employee_cannot_read_admin_nav_tree(self, client, db, employee_headers):
        resp = client.get("/api/admin/nav/tree", headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_read_admin_nav_tree(self, client, db, auth_headers):
        resp = client.get("/api/admin/nav/tree", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_employee_cannot_read_admin_nav_list(self, client, db, employee_headers):
        resp = client.get("/api/admin/nav/list", headers=employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_admin_can_read_admin_nav_list(self, client, db, auth_headers):
        resp = client.get("/api/admin/nav/list", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_employee_nav_still_works(self, client, db, employee_headers):
        tree = client.get("/api/employee/nav/tree", headers=employee_headers)
        assert tree.status_code == 200, tree.get_data(as_text=True)
        listing = client.get("/api/employee/nav/list", headers=employee_headers)
        assert listing.status_code == 200, listing.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session hardening — refresh tokens are revoked on logout
# ─────────────────────────────────────────────────────────────────────────────


def _login(client, username="employee1", password="emp123", role="employee"):
    resp = client.post("/api/login", json={"username": username, "password": password, "role": role})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


class TestRefreshRevocation:
    def test_refresh_works_before_logout_then_fails_after(self, client, db):
        tokens = _login(client)
        before = client.post("/api/refresh-token", json={"refresh_token": tokens["refresh_token"]})
        assert before.status_code == 200, before.get_data(as_text=True)

        # Same request shape as the frontend: access header, no body.
        logout = client.post("/api/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert logout.status_code == 200, logout.get_data(as_text=True)

        after = client.post("/api/refresh-token", json={"refresh_token": tokens["refresh_token"]})
        assert after.status_code == 401, after.get_data(as_text=True)

    def test_logout_with_explicit_refresh_token_revokes_header_path(self, client, db):
        tokens = _login(client, "admin1", "admin123", "admin")
        logout = client.post(
            "/api/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert logout.status_code == 200, logout.get_data(as_text=True)

        after = client.post(
            "/api/refresh-token",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        )
        assert after.status_code == 401, after.get_data(as_text=True)

    def test_new_login_after_logout_can_refresh(self, client, db):
        first = _login(client)
        client.post("/api/logout", headers={"Authorization": f"Bearer {first['access_token']}"})

        second = _login(client)
        resp = client.post("/api/refresh-token", json={"refresh_token": second["refresh_token"]})
        assert resp.status_code == 200, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# JWT role claims: explicit employee role never inherits an admin account
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def colliding_employee_headers(client, db):
    """An employee whose number equals an existing admin's ``adm_number``."""
    from werkzeug.security import generate_password_hash

    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo
    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo

    number = "E-COLLIDE-R2"
    username = "collide_emp_r2"
    if not EmployeeInfo.query.filter_by(employee_number=number).first():
        db.session.add(
            EmployeeInfo(
                employee_number=number,
                name="撞号员工",
                job_number="JCOL",
                id_number="IDCOLLIDEEMP",
                phone_number="19900000003",
                address="Test Address",
            )
        )
        db.session.commit()
    if not EmployeeAccount.query.filter_by(employee_user_name=username).first():
        db.session.add(
            EmployeeAccount(
                employee_user_name=username,
                employee_user_password=generate_password_hash("emp123"),
                role="employee",
                employee_number=number,
            )
        )
        db.session.commit()
    if not AdmInfo.query.filter_by(adm_number=number).first():
        db.session.add(
            AdmInfo(
                adm_number=number,
                name="撞号管理员",
                job_number="JCOLADM",
                id_number="IDCOLLIDEADM",
                phone_number="19900000004",
                address="Test Address",
            )
        )
        db.session.commit()
    if not AdmAccount.query.filter_by(adm_number=number).first():
        db.session.add(
            AdmAccount(
                adm_user_name="collide_adm_r2",
                adm_user_password=generate_password_hash("adm123"),
                role="admin1",
                adm_number=number,
            )
        )
        db.session.commit()

    resp = client.post("/api/login", json={"username": username, "password": "emp123", "role": "employee"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    headers = {"Authorization": f"Bearer {resp.get_json()['access_token']}"}
    try:
        yield headers
    finally:
        # Extra AdmAccount rows change recall-vote thresholds in the shared
        # test DB (test_recall counts them); remove everything this fixture made.
        db.session.rollback()
        for row in AdmAccount.query.filter_by(adm_number=number).all():
            db.session.delete(row)
        for row in AdmInfo.query.filter_by(adm_number=number).all():
            db.session.delete(row)
        for row in EmployeeAccount.query.filter_by(employee_number=number).all():
            db.session.delete(row)
        for row in EmployeeInfo.query.filter_by(employee_number=number).all():
            db.session.delete(row)
        db.session.commit()


class TestRoleClaimStrictness:
    def test_explicit_employee_role_does_not_inherit_admin(self, client, db, colliding_employee_headers):
        resp = client.get("/api/admin/nav/tree", headers=colliding_employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)
        resp = client.put("/api/data/vector/1", json={"alias": "x"}, headers=colliding_employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    def test_legacy_token_without_role_claim_still_uses_db_fallback(self, client, db, colliding_employee_headers):
        """Backwards compatibility: pre-role-claim tokens keep working."""
        from flask_jwt_extended import create_access_token

        with client.application.app_context():
            legacy = create_access_token(identity={"number": "E-COLLIDE-R2", "username": "collide_emp_r2"})
        resp = client.get("/api/admin/nav/tree", headers={"Authorization": f"Bearer {legacy}"})
        assert resp.status_code == 200, resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────────────────────
# Secrets: no public default keys
# ─────────────────────────────────────────────────────────────────────────────


def _run_python(code, extra_env):
    env = {k: v for k, v in os.environ.items() if k not in ("SECRET_KEY", "JWT_SECRET_KEY", "QR_SECRET_KEY")}
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestSecretFallback:
    def test_unset_secrets_get_random_per_process_values(self):
        code = "import config; print(config.Config.SECRET_KEY); print(config.Config.JWT_SECRET_KEY)"
        first = _run_python(code, {"FLASK_ENV": "development"})
        second = _run_python(code, {"FLASK_ENV": "development"})
        assert first.returncode == 0, first.stderr
        assert second.returncode == 0, second.stderr
        first_keys = first.stdout.strip().splitlines()
        second_keys = second.stdout.strip().splitlines()
        assert len(first_keys) == 2 and len(second_keys) == 2
        assert set(first_keys).isdisjoint(LEGACY_SECRET_DEFAULTS)
        assert first_keys[0] != first_keys[1]
        assert first_keys != second_keys
        assert "临时随机密钥" in first.stderr

    def test_production_still_fails_closed_without_env_keys(self):
        code = "import config\ntry:\n    config.get_config()\nexcept RuntimeError:\n    print('RAISED')\nelse:\n    print('NO')"
        result = _run_python(code, {"FLASK_ENV": "production"})
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "RAISED"


class TestQRSecretFallback:
    """QR signatures use their own HMAC key; it must fail closed in production
    just like SECRET_KEY/JWT_SECRET_KEY, while dev/testing keeps working."""

    def test_production_requires_qr_secret(self):
        result = _run_python("import resource.watermark_utils", {"FLASK_ENV": "production"})
        assert result.returncode != 0
        assert "QR_SECRET_KEY" in result.stderr

    def test_production_rejects_public_default_qr_secret(self):
        result = _run_python(
            "import resource.watermark_utils",
            {"FLASK_ENV": "production", "QR_SECRET_KEY": "dev-only-qr-key-replace-in-production"},
        )
        assert result.returncode != 0
        assert "QR_SECRET_KEY" in result.stderr

    def test_testing_qr_secret_is_not_public_and_roundtrips(self):
        import hashlib
        import hmac
        from types import SimpleNamespace

        from resource.watermark_utils import LEGACY_QR_SECRET_KEYS, QR_SECRET_KEY, build_qr_text

        assert QR_SECRET_KEY not in LEGACY_QR_SECRET_KEYS
        item = SimpleNamespace(
            id=1,
            data_alias="qr-roundtrip",
            data_id=1,
            data_type="vector",
            applicant_name="员工1",
            applicant_user_number="E001",
            application_submission_time=None,
            adm1_statu=True,
            adm2_statu=True,
            adm1_name=None,
            adm1_user_number=None,
            adm1_approval_time=None,
            adm2_name=None,
            adm2_user_number=None,
            adm2_approval_time=None,
        )
        text, signature = build_qr_text(item, {})
        content_to_sign = text.split("\nSignature: ")[0]
        expected = hmac.new(QR_SECRET_KEY.encode(), content_to_sign.encode(), hashlib.sha256).hexdigest()[:16]
        assert signature == expected
        assert f"Signature: {signature}" in text
