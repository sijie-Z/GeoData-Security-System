"""Tests for watermark endpoints."""

import base64
import io
import json
import uuid
from datetime import UTC, datetime

import numpy as np
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


def _build_roundtrip_shp(tmp_path, n_lines=15, n_pts=200):
    """Small vector dataset: polylines + a polygon with a hole (nested geometry)."""
    import geopandas as gpd
    from shapely.geometry import LineString, Polygon

    rng = np.random.default_rng(3)
    geoms = []
    for li in range(n_lines):
        xs = (21600.0 + li * 5.0 + np.cumsum(rng.normal(0, 1.0, n_pts))).round(3)
        ys = (23300.0 + np.cumsum(rng.normal(0, 1.0, n_pts))).round(3)
        geoms.append(LineString(zip(xs, ys)))
    ang = np.linspace(0, 2 * np.pi, 140)
    ext = np.column_stack([21700 + 4 * np.cos(ang), 23300 + 4 * np.sin(ang)]).round(3)
    hole = np.column_stack([21700 + 1.5 * np.cos(ang), 23300 + 1.5 * np.sin(ang)]).round(3)
    geoms.append(Polygon(ext, [hole]))
    gdf = gpd.GeoDataFrame({"fid": range(len(geoms))}, geometry=geoms, crs="EPSG:2334")
    shp_path = tmp_path / "roundtrip.shp"
    gdf.to_file(shp_path)
    return str(shp_path)


def _build_qr_png_b64(text, box_size=2):
    import qrcode

    qr = qrcode.QRCode(version=2, box_size=box_size, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode(), qr_img.size[0]


def _signed_qr_text(app_id, alias):
    """Compact payload following the build_qr_text convention (Signature line last)."""
    import hashlib
    import hmac

    from resource.watermark_utils import QR_SECRET_KEY

    content = "\n".join(
        [
            "=== SPATIAL DATA TRACKING SYSTEM ===",
            f"AppID: {app_id}",
            "DataType: vector",
            f"Data: {alias}",
        ]
    )
    sig = hmac.new(QR_SECRET_KEY.encode(), content.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{content}\nSignature: {sig}\n=== END ==="


def _create_vector_application(db, shp_path, alias):
    """Persist a Shp record + approved Application awaiting its QR watermark."""
    from model.Application import Application
    from model.Shp_Data import Shp

    shp = Shp(
        name=f"v_{alias}",
        alias=alias,
        geomtype="Polygon",
        introduction="vector watermark test",
        datetime=datetime.now(UTC),
        url="",
        layer=f"v_{alias}",
        shp_file_path=shp_path,
        coordinate_system="EPSG:2334",
        data_source="test",
    )
    db.session.add(shp)
    db.session.commit()

    item = Application(
        data_id=shp.id,
        data_name=f"v_{alias}",
        data_alias=alias,
        data_type="vector",
        applicant_name="Tester",
        applicant_user_number="E001",
        reason="watermark test",
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
    return item


def _attach_qr(db, item, qr_text):
    """Render qr_text into item.qrcode; returns the PNG pixel size (watermark side)."""
    item.qrcode, qr_side = _build_qr_png_b64(qr_text)
    item.watermark_generated = True
    db.session.commit()
    return qr_side


class TestVectorWatermarkRoundtrip:
    """Regression (N2): embed -> extract must recover the QR watermark.

    The chunk index for each vertex pair is derived from embedding-invariant
    anchors (x grid cell + y) so extraction can recompute it, the watermark grid
    size travels through vr_data, and nested geometries (polygons with holes)
    contribute votes exactly like they do during embedding.
    """

    def test_embed_extract_roundtrip_decodes(self, client, db, adm2_headers, adm3_headers, tmp_path):
        from model.Application import Application

        # A compact signed payload (same convention as build_qr_text) keeps the
        # QR small so the test data comfortably passes the capacity check.
        # Enough vertices so nearly every embedding chunk receives votes.
        shp_path = _build_roundtrip_shp(tmp_path, n_lines=50, n_pts=400)
        alias = f"rt-{uuid.uuid4().hex[:8]}"
        item = _create_vector_application(db, shp_path, alias)
        expected_side = _attach_qr(db, item, _signed_qr_text(item.id, alias))

        embed_resp = client.post("/api/embedding_watermark", json={"application_id": item.id}, headers=adm2_headers)
        assert embed_resp.status_code == 200, embed_resp.get_data(as_text=True)
        assert embed_resp.data[:2] == b"PK", "embed response must be the watermarked zip"

        # vr_data contract: {"vr": [...], "side_length": N}
        db.session.commit()
        payload = json.loads(db.session.get(Application, item.id).vr_data)
        assert isinstance(payload, dict), f"vr_data must carry the side_length contract, got {payload!r}"
        assert payload["side_length"] == expected_side  # pixel size of the generated QR PNG
        assert len(payload["vr"]) == 2

        extract_resp = client.post(
            "/api/vector/extract",
            headers=adm3_headers,
            data={"application_id": str(item.id), "file": (io.BytesIO(embed_resp.data), "watermarked.zip")},
            content_type="multipart/form-data",
        )
        assert extract_resp.status_code == 200, extract_resp.get_data(as_text=True)
        verify = extract_resp.get_json()["data"]["decoded_info"]["verify"]
        assert verify["digest_ok"] is True, verify
        assert verify["signature_ok"] is True, verify
        assert verify["message"] == "二维码校验成功"

    def test_algorithm_roundtrip_pixels_and_nested(self, tmp_path):
        """Algorithm-level: recovered watermark must be near pixel-identical to
        the original QR, including votes from nested (polygon-with-hole) parts."""
        from PIL import Image

        from algorithm.embed import embed as vector_embed
        from algorithm.extract import extract as vector_extract
        from resource.watermark_utils import decode_qr_from_image

        shp_path = _build_roundtrip_shp(tmp_path)
        qr_text = "ROUNDTRIP-REGRESSION-PAYLOAD"
        qr_b64, expected_side = _build_qr_png_b64(qr_text)
        qr_path = tmp_path / "qr.png"
        with open(qr_path, "wb") as fh:
            fh.write(base64.b64decode(qr_b64))

        res = vector_embed(shp_path, str(qr_path), output_dir=str(tmp_path / "embed"))
        assert res["side_length"] == expected_side

        import zipfile

        unz = tmp_path / "unz"
        unz.mkdir()
        with zipfile.ZipFile(res["zip_path"]) as zf:
            zf.extractall(unz)
        wshp = next(str(p) for p in unz.rglob("*.shp"))

        _, wm_path = vector_extract(wshp, res["vr"], side_length=res["side_length"], output_dir=str(tmp_path / "x"))
        assert decode_qr_from_image(wm_path) == qr_text

        orig = np.array(Image.open(qr_path).convert("L")) > 127
        rec = np.array(Image.open(wm_path).convert("L")) > 127
        assert orig.shape == rec.shape
        mask = np.ones_like(orig, dtype=bool)
        mask[:8, :8] = mask[:8, -8:] = mask[-8:, :8] = False
        inner_agreement = float((orig[mask] == rec[mask]).mean())
        assert inner_agreement >= 0.9, f"watermark pixels barely recovered: {inner_agreement:.4f}"


class TestVectorEmbedCapacity:
    """Regression (N3): a watermark too large for the data must surface as a
    readable 4xx carrying the required vs available chunk counts, not a generic
    500 (the pre-fix behavior for e.g. 11WuJiang: 49,958 vertices < 180,577)."""

    def test_resource_returns_readable_400(self, client, db, adm2_headers, tmp_path):
        import re

        # ~290 vertices vs a compact QR needing ~2,300 chunks -> far insufficient
        shp_path = _build_roundtrip_shp(tmp_path, n_lines=3, n_pts=50)
        alias = f"cap-{uuid.uuid4().hex[:8]}"
        item = _create_vector_application(db, shp_path, alias)
        qr_side = _attach_qr(db, item, _signed_qr_text(item.id, alias))

        resp = client.post("/api/embedding_watermark", json={"application_id": item.id}, headers=adm2_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        msg = resp.get_json()["msg"]
        m = re.search(r"需要 (\d+) 个嵌入区块，当前数据最多可提供 (\d+) 个（共 (\d+) 个顶点）", msg)
        assert m, msg
        needed, available, vertices = (int(g) for g in m.groups())
        assert needed == (qr_side * qr_side - 192 + 3) // 4
        assert 0 < available == vertices

    def test_algorithm_raises_capacity_error(self, tmp_path):
        from algorithm.embed import CapacityError
        from algorithm.embed import embed as vector_embed

        shp_path = _build_roundtrip_shp(tmp_path, n_lines=3, n_pts=50)
        qr_b64, qr_side = _build_qr_png_b64(_signed_qr_text(999, "cap"))
        qr_path = tmp_path / "cap_qr.png"
        with open(qr_path, "wb") as fh:
            fh.write(base64.b64decode(qr_b64))
        needed = (qr_side * qr_side - 192 + 3) // 4
        with pytest.raises(CapacityError, match=rf"需要 {needed} 个嵌入区块"):
            vector_embed(shp_path, str(qr_path), output_dir=str(tmp_path / "embed"))
