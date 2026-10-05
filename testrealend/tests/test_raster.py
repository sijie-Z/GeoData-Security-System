"""Tests for raster endpoints."""

import io
import os
import shutil

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

# Fixture extent (WGS84) — a small box over Hangzhou.
FIXTURE_BOUNDS = (119.9, 29.9, 120.1, 30.1)


def _make_geotiff(path, size=512, fill=None):
    """Write a real, georeferenced 3-band uint8 GeoTIFF.

    ``fill`` writes a constant value into every band — needed by the histogram
    algorithm, which embeds into a dominant histogram peak.
    """
    if fill is None:
        rng = np.random.default_rng(7)
        data = (rng.random((3, size, size)) * 255).astype("uint8")
    else:
        data = np.full((3, size, size), fill, dtype="uint8")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_bounds(*FIXTURE_BOUNDS, size, size),
    ) as dst:
        dst.write(data)
    return path


def _seed_raster_app(db, tif_path, alias="tif-host"):
    """An approved raster application backed by *tif_path* on disk."""
    from flask import current_app

    from model.Application import Application
    from model.Raster_Data import RasterData

    record = RasterData(name=alias, alias=alias, raster_file_path=str(tif_path), url="", layer="")
    db.session.add(record)
    # Commit each bind separately: in the SQLite test env both binds share one
    # file, so holding two write transactions at once deadlocks ("database is
    # locked").
    db.session.commit()
    item = Application(
        data_id=record.id,
        data_name=alias,
        data_alias=alias,
        data_type="raster",
        applicant_name="Tester",
        applicant_user_number="E001",
        reason="test",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    # Clear stale runtime artifacts from earlier sessions so the extract
    # endpoint's meta-file discovery is deterministic.
    shutil.rmtree(os.path.join(current_app.root_path, "runtime", "crmark", f"app_{item.id}"), ignore_errors=True)
    return item, str(tif_path)


@pytest.fixture
def raster_app(db, tmp_path):
    return _seed_raster_app(db, _make_geotiff(tmp_path / "host_geotiff.tif"))


class TestRaster:
    def test_raster_preview_requires_auth(self, client):
        resp = client.get("/api/raster/preview")
        assert resp.status_code in (401, 405, 422)

    def test_raster_generate_requires_auth(self, client):
        resp = client.post("/api/generate_raster_watermark", json={"application_id": 1})
        assert resp.status_code in (401, 422)

    def test_crmark_embed_requires_auth(self, client):
        resp = client.post("/api/crmark/embed", json={})
        assert resp.status_code in (401, 422)

    def test_crmark_recover_requires_auth(self, client):
        resp = client.post("/api/crmark/recover", json={})
        assert resp.status_code in (401, 422)

    def test_crmark_decode_requires_auth(self, client):
        resp = client.post("/api/crmark/decode", json={})
        assert resp.status_code in (401, 422)

    def test_embed_dispatch_requires_auth(self, client):
        resp = client.post("/api/admin/embed_dispatch", json={})
        assert resp.status_code in (401, 422)

    def test_raster_applications_generate(self, client, auth_headers):
        resp = client.get("/api/adm1_get_raster_applications_generate_watermark", headers=auth_headers)
        assert resp.status_code == 200


class TestGeoTIFFEmbed:
    """BUG-1 regression: embedded GeoTIFF stego must be a real on-disk artifact
    and the DB must only ever record a path that exists (no dirty state)."""

    def test_embed_dispatch_records_real_stego_file(self, client, db, adm2_headers, raster_app):
        from model.Application import Application

        item, _ = raster_app
        resp = client.post("/api/admin/embed_dispatch", json={"application_id": item.id}, headers=adm2_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()["data"]
        stego = data["stego_path"]
        assert stego.endswith(".tif")
        assert os.path.isfile(stego)
        with rasterio.open(stego) as src:
            assert src.crs is not None
            assert src.count == 3
        assert os.path.isfile(data["wm_meta_path"])

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.watermark_embedded is True
        assert row.watermark_path == stego
        assert os.path.isfile(row.watermark_path)

    def test_embed_dispatch_histogram_records_real_stego_file(self, client, db, adm2_headers, tmp_path):
        from model.Application import Application

        item, _ = _seed_raster_app(db, _make_geotiff(tmp_path / "host_const.tif", fill=100), alias="const-host")
        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "histogram"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_json()
        stego = resp.get_json()["data"]["stego_path"]
        assert stego.endswith(".tif")
        assert os.path.isfile(stego)
        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.watermark_path == stego
        assert os.path.isfile(row.watermark_path)

    def test_embed_failure_does_not_leave_dirty_state(self, client, db, adm2_headers, raster_app, monkeypatch):
        from model.Application import Application

        item, _ = raster_app

        def _boom(_path):
            raise RuntimeError("boom")

        monkeypatch.setattr("resource.raster_resource._to_preview_base64", _boom)
        resp = client.post("/api/admin/embed_dispatch", json={"application_id": item.id}, headers=adm2_headers)
        assert resp.status_code == 500
        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert not row.watermark_embedded
        assert not row.watermark_path


class TestRasterExtractAfterEmbed:
    """BUG-2 regression: raster applications have no vr_data, but extraction of
    an uploaded raster stego must work once the watermark was embedded."""

    def test_extract_after_embed_not_404_and_detects_watermark(
        self, client, db, adm2_headers, adm3_headers, raster_app
    ):
        item, _ = raster_app
        resp = client.post("/api/admin/embed_dispatch", json={"application_id": item.id}, headers=adm2_headers)
        assert resp.status_code == 200, resp.get_json()
        stego = resp.get_json()["data"]["stego_path"]

        with open(stego, "rb") as fh:
            resp2 = client.post(
                "/api/vector/extract",
                data={"application_id": str(item.id), "file": (fh, os.path.basename(stego))},
                headers=adm3_headers,
            )
        assert resp2.status_code == 200, resp2.get_json()
        verify = resp2.get_json()["data"]["decoded_info"]["verify"]
        assert verify["digest_ok"] is True
        assert verify["signature_ok"] is True

    def test_extract_raster_without_embed_still_404(self, client, adm3_headers, raster_app):
        item, _ = raster_app
        resp = client.post(
            "/api/vector/extract",
            data={"application_id": str(item.id), "file": (io.BytesIO(b"not an image"), "x.tif")},
            headers=adm3_headers,
        )
        assert resp.status_code == 404
