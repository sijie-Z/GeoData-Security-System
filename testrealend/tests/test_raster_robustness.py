"""Tests for the raster robustness matrix (feat_raster_robustness).

Engine: ``algorithm/robustness_raster.py`` — four raster schemes (lsb / dwt /
histogram / blind) x image attacks on a synthetic 512x512 GeoTIFF host, plus
the ``kind="raster"`` extension of ``POST /api/robustness/run``.
"""

import numpy as np
import pytest

from algorithm.robustness_raster import (
    RASTER_ATTACKS,
    RASTER_SCHEMES,
    make_host_tif,
    r_blur,
    r_crop,
    r_jpeg,
    r_noise,
    r_resize,
    r_rotate,
    render_raster_payload_qr,
    run_raster_matrix,
)


def _build_matrix_payload():
    """Real v2 signed payload text (same construction as test_robustness)."""
    from datetime import UTC, datetime

    from crypto.keys import ensure_active_key
    from crypto.payload import build_qr_v2_text

    kid, _private_key = ensure_active_key()
    return build_qr_v2_text("ef" * 16, 4242, kid, int(datetime.now(UTC).timestamp()))


def _read_tif(path):
    import rasterio

    with rasterio.open(path) as src:
        return src.read(), src.crs, src.width, src.height


class TestRasterHostAndPayload:
    def test_make_host_tif_deterministic_and_georeferenced(self, tmp_path):
        a = make_host_tif(str(tmp_path / "host_a.tif"))
        b = make_host_tif(str(tmp_path / "host_b.tif"))
        arr_a, crs_a, w_a, h_a = _read_tif(a)
        arr_b, _crs_b, _w_b, _h_b = _read_tif(b)
        assert (w_a, h_a) == (512, 512)
        assert arr_a.shape == (3, 512, 512)
        assert crs_a is not None and crs_a.to_epsg() == 4326
        assert np.array_equal(arr_a, arr_b), "host must be deterministic (seed 7)"

    def test_make_host_tif_fill_is_constant(self, tmp_path):
        arr, _crs, _w, _h = _read_tif(make_host_tif(str(tmp_path / "host_fill.tif"), fill=100))
        assert np.all(arr == 100)

    def test_payload_qr_fits_blind_budget(self, db, tmp_path):
        """The rendered payload must fit the blind scheme on a 512x512 host.

        One bit per 8x8 block -> 4096 blocks; the library needs strictly fewer
        bits than blocks, so the QR side must stay <= 63 px (3969 bits).
        """
        text = _build_matrix_payload()
        qr_path, side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        assert 0 < side <= 63, f"payload QR {side}px exceeds the 512-host blind budget"
        from resource.watermark_utils import decode_qr_from_image

        assert decode_qr_from_image(qr_path) == text


class TestRasterAttackFunctions:
    @pytest.fixture
    def source_tif(self, tmp_path):
        return make_host_tif(str(tmp_path / "attack_src.tif"))

    def test_jpeg_recompresses_and_keeps_geometry(self, source_tif, tmp_path):
        src, _crs, _w, _h = _read_tif(source_tif)
        out = r_jpeg(source_tif, quality=70, output_path=str(tmp_path / "out_jpeg.tif"))
        arr, crs, w, h = _read_tif(out)
        assert (w, h) == (512, 512)
        assert crs is not None and crs.to_epsg() == 4326
        assert not np.array_equal(arr, src), "JPEG recompression must alter pixels"

    def test_resize_halves_dimensions_and_keeps_crs(self, source_tif, tmp_path):
        out = r_resize(source_tif, factor=0.5, output_path=str(tmp_path / "out_resize.tif"))
        _arr, crs, w, h = _read_tif(out)
        assert (w, h) == (256, 256)
        assert crs is not None and crs.to_epsg() == 4326

    def test_crop_keeps_center_70_percent(self, source_tif, tmp_path):
        src, _crs, _w, _h = _read_tif(source_tif)
        out = r_crop(source_tif, keep=0.7, output_path=str(tmp_path / "out_crop.tif"))
        arr, crs, w, h = _read_tif(out)
        assert (w, h) == (358, 358)
        assert crs is not None and crs.to_epsg() == 4326
        assert np.array_equal(arr, src[:, 77 : 77 + 358, 77 : 77 + 358]), "crop must be centered"

    def test_rotate_keeps_dimensions(self, source_tif, tmp_path):
        out = r_rotate(source_tif, deg=5, output_path=str(tmp_path / "out_rotate.tif"))
        _arr, _crs, w, h = _read_tif(out)
        assert (w, h) == (512, 512)

    def test_noise_is_deterministic(self, source_tif, tmp_path):
        src, _crs, _w, _h = _read_tif(source_tif)
        out1 = r_noise(source_tif, sigma=5, output_path=str(tmp_path / "out_noise1.tif"))
        out2 = r_noise(source_tif, sigma=5, output_path=str(tmp_path / "out_noise2.tif"))
        arr1, _c1, _w1, _h1 = _read_tif(out1)
        arr2, _c2, _w2, _h2 = _read_tif(out2)
        assert np.array_equal(arr1, arr2), "fixed-seed noise must be deterministic"
        assert not np.array_equal(arr1, src)

    def test_blur_keeps_dimensions(self, source_tif, tmp_path):
        src, _crs, _w, _h = _read_tif(source_tif)
        out = r_blur(source_tif, radius=3, output_path=str(tmp_path / "out_blur.tif"))
        arr, _crs2, w, h = _read_tif(out)
        assert (w, h) == (512, 512)
        assert not np.array_equal(arr, src)


class TestRasterMatrixEngine:
    def _payload_qr(self, db, tmp_path):
        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        return qr_path, text

    def test_lsb_baseline_and_jpeg_control(self, db, tmp_path):
        """LSB: baseline decodes; JPEG q70 (the fragile-watermark killer) must not."""
        qr_path, _text = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host.tif"))
        rows = run_raster_matrix(host, ["lsb"], ["none", "jpeg"], qr_path, str(tmp_path / "work_lsb"))
        by_attack = {row["attack"]: row for row in rows}
        assert by_attack["none"]["decode_success"] is True, f"lsb baseline lost: {by_attack['none']}"
        assert by_attack["none"]["nc"] is not None and by_attack["none"]["nc"] > 0.99
        assert by_attack["jpeg"]["decode_success"] is False, "lsb unexpectedly survived JPEG recompression"

    def test_blind_baseline_decodes(self, db, tmp_path):
        """Blind (DWT-DCT-SVD): the 57px payload fits the 512-host block budget."""
        qr_path, _text = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host.tif"))
        rows = run_raster_matrix(host, ["blind"], ["none"], qr_path, str(tmp_path / "work_blind"))
        assert len(rows) == 1
        row = rows[0]
        assert row["decode_success"] is True, f"blind baseline lost: {row}"
        assert row["nc"] is not None and row["nc"] > 0.99, f"blind baseline NC too low: {row}"
        assert row["duration_ms"] is not None and row["duration_ms"] >= 0

    def test_matrix_row_schema_matches_vector(self, db, tmp_path):
        qr_path, _text = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host.tif"))
        rows = run_raster_matrix(host, ["dwt"], ["none"], qr_path, str(tmp_path / "work_dwt"))
        assert set(rows[0].keys()) == {
            "scheme",
            "attack",
            "trial",
            "attack_params",
            "decode_success",
            "nc",
            "ber",
            "duration_ms",
            "error",
        }

    def test_histogram_embed_failure_is_an_honest_error_row(self, db, tmp_path):
        """A random-noise host has no dominant histogram peak: full-size payload
        cannot fit, and every requested attack row records the embed failure
        (no silent skip, no prettified numbers)."""
        qr_path, _text = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host.tif"))
        rows = run_raster_matrix(host, ["histogram"], ["none", "jpeg"], qr_path, str(tmp_path / "work_hist"))
        assert len(rows) == 2
        for row in rows:
            assert row["decode_success"] is False
            assert row["error"] and "Insufficient histogram capacity" in row["error"]


class TestRobustnessRasterApi:
    def test_raster_run_endpoint_smoke(self, client, db, auth_headers):
        import resource.robustness_resource as robustness_resource

        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "schemes": ["lsb"], "attacks": ["none"]},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        data = resp.get_json()["data"]
        assert data["kind"] == "raster"
        run_id = data["run_id"]

        thread = robustness_resource._ACTIVE_RUNS.get(run_id)
        if thread is not None:
            thread.join(timeout=120)
            assert not thread.is_alive(), "raster robustness worker did not finish within 120s"

        detail = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers)
        assert detail.status_code == 200
        run = detail.get_json()["run"]
        assert run["kind"] == "raster"
        assert run["data_ref"] == "synthetic_512x512"
        assert run["done"] == 1 and run["total"] == 1
        row = run["rows"][0]
        assert (row["scheme"], row["attack"]) == ("lsb", "none")
        assert row["decode_success"] is True
        assert row["nc"] is not None

        listing = client.get("/api/robustness/runs", headers=auth_headers)
        assert listing.status_code == 200
        entry = next(e for e in listing.get_json()["runs"] if e["run_id"] == run_id)
        assert entry["kind"] == "raster"

    def test_raster_endpoint_rejects_vector_scheme(self, client, db, auth_headers):
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "schemes": ["legacy"], "attacks": ["none"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        msg = resp.get_json()["msg"]
        assert "schemes" in msg and "lsb" in msg

    def test_endpoint_rejects_unknown_kind(self, client, db, auth_headers):
        resp = client.post("/api/robustness/run", json={"kind": "banana"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_raster_scheme_and_attack_whitelists(self):
        assert RASTER_SCHEMES == ("lsb", "dwt", "histogram", "blind")
        assert set(RASTER_ATTACKS) == {"none", "jpeg", "resize", "crop", "rotate", "noise", "blur"}
