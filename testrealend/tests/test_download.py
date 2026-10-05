"""Tests for download endpoints."""

from datetime import UTC, datetime, timedelta

import pytest


class TestDownload:
    def test_download_requires_auth(self, client):
        resp = client.get("/api/emp_download_zip")
        assert resp.status_code in (401, 405, 422)

    def test_request_download_token_requires_auth(self, client):
        resp = client.post("/api/request_download_token", json={"application_id": 1})
        assert resp.status_code in (401, 422)

    def test_token_download_invalid_token(self, client):
        resp = client.get("/api/download/invalid-token-123")
        assert resp.status_code in (400, 401, 403, 404)

    def test_record_download_requires_auth(self, client):
        resp = client.post("/api/record_download_file", json={})
        assert resp.status_code in (401, 422)

    def test_record_download(self, client, employee_headers):
        resp = client.post(
            "/api/record_download_file",
            headers=employee_headers,
            json={"application_id": 1, "applicant_user_number": "E001", "download_user_number": "E001"},
        )
        assert resp.status_code in (200, 201, 400, 404, 500)


class TestTokenDownloadFlow:
    """BUG-3 regression: GET /api/download/<token> compared an aware
    datetime.now(UTC) against the naive DB column and always raised
    TypeError (500). A valid token must download, used/expired ones stay 403."""

    @pytest.fixture
    def downloadable_app(self, db, tmp_path):
        from model.Application import Application

        payload = tmp_path / "download_me.bin"
        payload.write_bytes(b"TOKEN-DOWNLOAD-PAYLOAD")
        item = Application(
            data_id=1,
            data_name="dl",
            data_alias="dl",
            data_type="vector",
            applicant_name="Tester",
            applicant_user_number="E001",
            reason="test",
            adm1_statu=True,
            adm2_statu=True,
            watermark_path=str(payload),
        )
        db.session.add(item)
        db.session.commit()
        return item, payload

    def test_token_flow_download_200_then_used_403(self, client, downloadable_app, employee_headers):
        item, payload = downloadable_app
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code in (200, 201), resp.get_json()
        token = resp.get_json()["token"]

        dl = client.get(f"/api/download/{token}")
        assert dl.status_code == 200
        assert dl.data == b"TOKEN-DOWNLOAD-PAYLOAD"

        used = client.get(f"/api/download/{token}")
        assert used.status_code == 403
        assert "已使用" in used.get_json()["msg"]

    def test_expired_token_returns_403(self, client, db, downloadable_app):
        from model.download_token import DownloadToken

        item, _ = downloadable_app
        expired = DownloadToken(
            application_id=item.id,
            user_number="E001",
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
        )
        db.session.add(expired)
        db.session.commit()

        resp = client.get(f"/api/download/{expired.token}")
        assert resp.status_code == 403
        assert "过期" in resp.get_json()["msg"]
