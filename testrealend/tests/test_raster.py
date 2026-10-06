"""Tests for raster endpoints."""

import base64
import io
import os
import re
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


def _make_multiband_geotiff(path, width=192, height=192, bands=7, low=0.0, high=254.0):
    """A 7-band float64 GeoTIFF, by default in the 0-255 range.

    PIL cannot open it at all ("More samples per pixel than can be decoded: 7")
    — exactly the host class (7-band MODIS GeoTIFF) that made embed_dwt fail
    with a generic 500 before band selection was added. Odd sizes exercise the
    even-dimension crop; ``low``/``high`` outside 0-255 exercise the clipping
    path of saturated physical-unit rasters.
    """
    rng = np.random.default_rng(11)
    data = rng.random((bands, height, width)) * (high - low) + low
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=bands,
        dtype="float64",
        crs="EPSG:4326",
        transform=from_bounds(*FIXTURE_BOUNDS, width, height),
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


class TestRasterPreview:
    """Regression (API campaign domain02): /api/raster/preview opened
    caller-supplied server paths directly — a non-image file produced
    PIL.UnidentifiedImageError mapped to a generic 500, and any image anywhere
    on the server could be rendered (information exposure). Unparseable files
    now yield a readable 400 and previews are confined to the application's
    own data roots (out-of-root paths -> 404)."""

    @staticmethod
    def _runtime_probe_dir():
        from flask import current_app

        path = os.path.join(current_app.root_path, "runtime", "preview_tests")
        os.makedirs(path, exist_ok=True)
        return path

    def test_preview_non_image_returns_400(self, client, employee_headers):
        txt = os.path.join(self._runtime_probe_dir(), "not_an_image.txt")
        with open(txt, "w", encoding="utf-8") as fh:
            fh.write("definitely not an image")
        resp = client.post("/api/raster/preview", json={"file_path": txt}, headers=employee_headers)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert resp.get_json()["message"] == "文件不是可解析的图片"

    def test_preview_image_inside_root_returns_200(self, client, employee_headers):
        from PIL import Image as PILImage

        png = os.path.join(self._runtime_probe_dir(), "tiny.png")
        PILImage.new("RGB", (8, 8), (200, 30, 30)).save(png)
        resp = client.post("/api/raster/preview", json={"file_path": png}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        decoded = base64.b64decode(resp.get_json()["base64"])
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_preview_outside_roots_returns_404(self, client, employee_headers, tmp_path):
        from PIL import Image as PILImage

        png = tmp_path / "outside.png"
        PILImage.new("RGB", (8, 8), (10, 10, 10)).save(png)
        resp = client.post("/api/raster/preview", json={"file_path": str(png)}, headers=employee_headers)
        assert resp.status_code == 404, resp.get_data(as_text=True)


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


class TestDWTMultibandRoundtrip:
    """Regression (API campaign domain05): embed_dwt unconditionally converted
    the host to YCbCr, so a 7-band MODIS GeoTIFF raised PIL "More samples per
    pixel" -> generic 500. Multi-band hosts now use their first three bands as
    RGB (same convention as the reversible/histogram algorithms), odd sizes are
    cropped to what the multi-level haar transform round-trips exactly, and
    extract decodes the QIM quarter-step offset the embed writes (plus exact
    float BT.601 conversions) — the embed -> extract roundtrip is now exact."""

    def test_embed_extract_roundtrip_on_7band_geotiff(self, tmp_path):
        from PIL import Image as PILImage

        from algorithm.raster_dwt_watermark import embed_dwt, extract_dwt

        # Odd sizes exercise the even-dimension crop; in-range float samples
        # keep every pixel embeddable (no gamut saturation).
        host = _make_multiband_geotiff(tmp_path / "host_7band.tif", width=171, height=131, bands=7)
        rng = np.random.default_rng(3)
        wm = PILImage.fromarray((rng.random((32, 32)) > 0.5).astype(np.uint8) * 255, mode="L")

        result = embed_dwt(str(host), wm, str(tmp_path / "out"), "t7")
        assert os.path.isfile(result["stego_path"])
        assert os.path.isfile(result["wm_meta_path"])

        decoded_path = str(tmp_path / "decoded.png")
        extract_dwt(result["stego_path"], result["wm_meta_path"], decoded_path)
        with PILImage.open(decoded_path) as dec:
            decoded = np.array(dec.convert("L"))

        # Deterministic decoder: recovered bits must match the embedded ones.
        resized = wm.convert("L").resize((decoded.shape[1], decoded.shape[0]), PILImage.Resampling.NEAREST)
        expected = (np.array(resized) > 127).astype(np.uint8) * 255
        assert decoded.shape == expected.shape
        assert np.array_equal(decoded, expected)

    def test_embed_dispatch_dwt_on_multiband_geotiff(self, client, db, adm2_headers, tmp_path):
        from model.Application import Application

        # Saturated physical-unit values + odd size: the full hostile path the
        # real MODIS raster takes. Must embed and decode without a 500.
        host = _make_multiband_geotiff(
            tmp_path / "host7_api.tif", width=187, height=149, bands=7, low=-100.0, high=1900.0
        )
        item, _ = _seed_raster_app(db, host, alias="mb7-host")
        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "dwt"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()["data"]
        stego, meta = data["stego_path"], data["wm_meta_path"]
        assert os.path.isfile(stego)
        assert os.path.isfile(meta)

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.watermark_embedded is True
        assert row.watermark_path == stego

        dec = client.post(
            "/api/crmark/decode",
            json={"stego_path": stego, "wm_meta_path": meta},
            headers=adm2_headers,
        )
        assert dec.status_code == 200, dec.get_data(as_text=True)
        assert dec.data[:8] == b"\x89PNG\r\n\x1a\n"


class TestRasterCapacityMapping:
    """Regression (API campaign domain05): the histogram algorithm raises
    ValueError("Insufficient histogram capacity: need N bits but peak bin has
    only M pixels...") when the host cannot carry the watermark (7-band MODIS
    TIFF: 4,141,368 bits vs 5,749; grayscale PNG: 262,144 vs 1,108 cold-run
    numbers). Both raster embed entry points mapped it to a generic 500; they
    must return a readable 400 carrying the need-vs-available numbers, the
    same pattern as the vector CapacityError path."""

    _CAPACITY_RE = re.compile(r"need (\d+) bits but peak bin has only (\d+) pixels")

    def _assert_capacity_400(self, resp, expected_bits):
        assert resp.status_code == 400, resp.get_data(as_text=True)
        msg = resp.get_json()["message"]
        m = self._CAPACITY_RE.search(msg)
        assert m, msg
        needed, available = int(m.group(1)), int(m.group(2))
        assert needed == expected_bits
        assert 0 < available < needed

    def test_histogram_capacity_400_multiband_geotiff(self, client, db, adm2_headers, tmp_path):
        host = _make_multiband_geotiff(tmp_path / "hist7.tif", width=192, height=192, bands=7)
        item, _ = _seed_raster_app(db, host, alias="hist7-host")
        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "histogram"},
            headers=adm2_headers,
        )
        self._assert_capacity_400(resp, 192 * 192)

    def test_histogram_capacity_400_gray_png(self, client, db, adm2_headers, tmp_path):
        from PIL import Image as PILImage

        rng = np.random.default_rng(21)
        path = tmp_path / "gray_host.png"
        PILImage.fromarray((rng.random((128, 128)) * 255).astype(np.uint8), mode="L").save(path)
        item, _ = _seed_raster_app(db, path, alias="hist-gray-host")
        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "histogram"},
            headers=adm2_headers,
        )
        self._assert_capacity_400(resp, 128 * 128)

    def test_embedding_watermark_raster_capacity_400(self, client, db, adm2_headers, tmp_path):
        from io import BytesIO

        from PIL import Image as PILImage

        from model.Application import Application
        from model.Raster_Data import RasterData

        host = _make_multiband_geotiff(tmp_path / "hist7_legacy.tif", width=192, height=192, bands=7)
        record = RasterData(name="hist7_legacy", alias="hist7_legacy", raster_file_path=str(host), url="", layer="")
        db.session.add(record)
        db.session.commit()

        buf = BytesIO()
        PILImage.new("L", (16, 16), 255).save(buf, format="PNG")
        item = Application(
            data_id=record.id,
            data_name="hist7_legacy",
            data_alias="hist7_legacy",
            data_type="raster",
            applicant_name="Tester",
            applicant_user_number="E001",
            reason="capacity mapping",
            adm1_statu=True,
            adm2_statu=True,
            qrcode=base64.b64encode(buf.getvalue()).decode(),
        )
        db.session.add(item)
        db.session.commit()

        resp = client.post(
            "/api/embedding_watermark",
            json={"application_id": item.id, "algorithm": "histogram"},
            headers=adm2_headers,
        )
        assert resp.status_code == 400, resp.get_data(as_text=True)
        msg = resp.get_json()["msg"]
        m = self._CAPACITY_RE.search(msg)
        assert m, msg
        assert int(m.group(1)) == 192 * 192
        assert 0 < int(m.group(2)) < int(m.group(1))


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
