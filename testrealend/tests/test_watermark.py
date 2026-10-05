"""Tests for watermark endpoints."""

from datetime import UTC, datetime

import pytest


class TestWatermarkGeneration:
    def test_requires_auth(self, client):
        resp = client.post("/api/generate_watermark", json={"application_id": 1})
        assert resp.status_code in (401, 422)

    def test_missing_application(self, client, auth_headers):
        resp = client.post("/api/generate_watermark", headers=auth_headers, json={"application_id": 99999})
        assert resp.status_code in (404, 400)

    def test_get_generate_applications(self, client, auth_headers):
        resp = client.get("/api/adm1_get_applications_generate_watermark", headers=auth_headers)
        assert resp.status_code == 200


class TestWatermarkEmbedding:
    def test_requires_auth(self, client):
        resp = client.post("/api/embedding_watermark", json={"application_id": 1})
        assert resp.status_code in (401, 422)

    def test_get_embedding_applications(self, client, adm2_headers):
        resp = client.get("/api/adm2_embedding_watermark_applications", headers=adm2_headers)
        assert resp.status_code == 200


class TestVectorExtract:
    def test_requires_auth(self, client):
        resp = client.post("/api/vector/extract")
        assert resp.status_code in (401, 422)

    def test_missing_fields(self, client, adm3_headers):
        resp = client.post("/api/vector/extract", headers=adm3_headers)
        assert resp.status_code in (400, 422)


class TestQRCodeDecode:
    """BUG-4 regression: the decode endpoint filtered every ``===`` line out of
    the signed content, but the generator signs all header/body lines including
    the banner — so untampered QR codes always failed signature verification."""

    @pytest.fixture
    def qr_text(self, db):
        from model.Application import Application
        from resource.watermark_utils import build_qr_text

        item = Application(
            data_id=1,
            data_name="qr-demo",
            data_alias="qr-demo",
            data_type="vector",
            applicant_name="Tester",
            applicant_user_number="E001",
            reason="test",
            adm1_statu=True,
            adm2_statu=True,
            adm1_name="A1",
            adm1_user_number="admin1",
            adm2_name="A2",
            adm2_user_number="admin2",
            application_submission_time=datetime.now(UTC),
        )
        db.session.add(item)
        db.session.commit()
        text, _signature = build_qr_text(item, {"reason": "test"})
        return text

    def test_untampered_qr_signature_ok(self, client, qr_text, employee_headers):
        resp = client.post("/api/qrcode/decode", json={"qr_text": qr_text}, headers=employee_headers)
        assert resp.status_code == 200
        verify = resp.get_json()["data"]["decoded_info"]["verify"]
        assert verify["signature_ok"] is True

    def test_tampered_qr_signature_false(self, client, qr_text, employee_headers):
        tampered = qr_text.replace("Data: qr-demo", "Data: HACKED")
        assert tampered != qr_text
        resp = client.post("/api/qrcode/decode", json={"qr_text": tampered}, headers=employee_headers)
        assert resp.status_code == 200
        verify = resp.get_json()["data"]["decoded_info"]["verify"]
        assert verify["signature_ok"] is False
