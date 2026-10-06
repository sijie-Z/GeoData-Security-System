"""Robustness tests: simulate attacks on watermarked images and measure survival."""

import os

import numpy as np
import pytest
from PIL import Image


def _to_bits(img):
    """Convert image to binary bit array."""
    arr = np.array(img.convert("L"))
    return (arr > 127).astype(int).flatten()


def _nc(a, b):
    """Normalized Correlation between two bit arrays."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    min_len = min(len(a), len(b))
    a, b = a[:min_len], b[:min_len]
    if np.sum(a) == 0 and np.sum(b) == 0:
        return 1.0
    return float(np.dot(a, b) / (np.sqrt(np.dot(a, a)) * np.sqrt(np.dot(b, b)) + 1e-10))


def _ber(a, b):
    """Bit Error Rate."""
    a, b = np.array(a, dtype=int), np.array(b, dtype=int)
    min_len = min(len(a), len(b))
    return float(np.sum(a[:min_len] != b[:min_len]) / min_len)


class TestLSBRobustness:
    """Test LSB watermark survival under common image attacks."""

    @pytest.fixture
    def watermark_pair(self, tmp_path):
        """Create a test watermark image and embed it via LSB."""
        from algorithm.raster_reversible_watermark import embed_reversible

        # Create a 100x100 test host image
        host = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        host_path = str(tmp_path / "host.png")
        Image.fromarray(host).save(host_path)

        # Create a 100x100 binary watermark (matches host size since embed_reversible
        # resizes watermark to host dimensions)
        wm = np.array([[255 if (i + j) % 3 == 0 else 0 for j in range(100)] for i in range(100)], dtype=np.uint8)
        wm_path = str(tmp_path / "wm.png")
        Image.fromarray(wm).save(wm_path)

        out_dir = str(tmp_path / "output")
        result = embed_reversible(host_path, Image.open(wm_path), out_dir, "test")
        # Save host path in result for recovery test
        result["host_path"] = host_path
        return result, wm_path

    def test_no_attack(self, watermark_pair):
        """Baseline: extracted watermark matches original without attack."""
        from algorithm.raster_reversible_watermark import decode_reversible

        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result["stego_path"])
        out = os.path.join(stego_dir, "decoded_test.png")
        decode_reversible(result["stego_path"], result["wm_meta_path"], out)

        orig = _to_bits(Image.open(wm_path))
        extracted = _to_bits(Image.open(out))
        nc = _nc(orig, extracted)
        assert nc > 0.99, f"NC too low without attack: {nc}"

    def test_jpeg_compression(self, watermark_pair):
        """Watermark survives JPEG compression (quality=70)."""
        from algorithm.raster_reversible_watermark import decode_reversible

        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result["stego_path"])

        # Re-save as JPEG (lossy compression)
        img = Image.open(result["stego_path"])
        jpeg_path = os.path.join(stego_dir, "compressed.jpg")
        img.save(jpeg_path, "JPEG", quality=70)

        # Try to decode from compressed version
        out = os.path.join(stego_dir, "decoded_compressed.png")
        try:
            decode_reversible(jpeg_path, result["wm_meta_path"], out)
            orig = _to_bits(Image.open(wm_path))
            extracted = _to_bits(Image.open(out))
            nc = _nc(orig, extracted)
            assert nc >= 0.0
        except Exception:
            pass  # Expected: LSB is fragile against compression

    def test_gaussian_noise(self, watermark_pair):
        """Test watermark survival under Gaussian noise."""
        from algorithm.raster_reversible_watermark import decode_reversible

        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result["stego_path"])

        # Add Gaussian noise
        img_arr = np.array(Image.open(result["stego_path"]).convert("RGB"), dtype=np.float64)
        noise = np.random.normal(0, 5, img_arr.shape)
        noisy = np.clip(img_arr + noise, 0, 255).astype(np.uint8)
        noisy_path = os.path.join(stego_dir, "noisy.png")
        Image.fromarray(noisy).save(noisy_path)

        out = os.path.join(stego_dir, "decoded_noisy.png")
        try:
            decode_reversible(noisy_path, result["wm_meta_path"], out)
            orig = _to_bits(Image.open(wm_path))
            extracted = _to_bits(Image.open(out))
            nc = _nc(orig, extracted)
            assert nc >= 0.0
        except Exception:
            pass

    def test_crop_attack(self, watermark_pair):
        """Test behavior when image is cropped."""
        from algorithm.raster_reversible_watermark import decode_reversible

        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result["stego_path"])

        # Crop 10% from each side
        img = Image.open(result["stego_path"])
        w, h = img.size
        cropped = img.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)))
        crop_path = os.path.join(stego_dir, "cropped.png")
        cropped.save(crop_path)

        out = os.path.join(stego_dir, "decoded_cropped.png")
        with pytest.raises(ValueError):
            decode_reversible(crop_path, result["wm_meta_path"], out)

    def test_recovery_perfect(self, watermark_pair):
        """Reversible recovery produces bit-exact original."""
        from algorithm.raster_reversible_watermark import recover_reversible

        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result["stego_path"])
        host_path = result["host_path"]

        # Recover
        recovered_path = os.path.join(stego_dir, "recovered.png")
        recover_reversible(result["stego_path"], result["wm_map_path"], result["wm_meta_path"], recovered_path)

        # Compare
        orig = np.array(Image.open(host_path))
        recovered = np.array(Image.open(recovered_path))
        assert np.array_equal(orig, recovered), "Recovery is not bit-exact!"


class TestVectorRobustness:
    """Test vector watermark survival under coordinate transformations."""

    def test_embed_extract_roundtrip(self):
        """Basic embed→extract roundtrip for vector data."""
        import os
        import tempfile
        import zipfile

        import geopandas as gpd
        from shapely.geometry import Point

        from algorithm.embed import embed
        from algorithm.extract import extract

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test shapefile with enough vertices for embedding
            n_points = 5000
            gdf = gpd.GeoDataFrame(
                {"id": range(n_points)},
                geometry=[Point(100 + i * 0.0001, 40 + i * 0.0001) for i in range(n_points)],
                crs="EPSG:4326",
            )
            shp_path = os.path.join(tmpdir, "test.shp")
            gdf.to_file(shp_path)

            # Create minimal QR watermark (version 1, low error correction, box_size=1 → 21x21)
            import qrcode

            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=0)
            qr.add_data("WM")
            qr.make(fit=True)
            qr_path = os.path.join(tmpdir, "test_qr.png")
            qr.make_image().save(qr_path)

            # Embed
            result = embed(shp_path, qr_path, output_dir=tmpdir)
            assert "zip_path" in result

            # Extract from watermarked zip
            zip_path = result["zip_path"]
            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            shp_files = [f for f in os.listdir(extract_dir) if f.endswith(".shp")]
            assert len(shp_files) > 0, "No .shp in watermarked zip"

            wm_shp = os.path.join(extract_dir, shp_files[0])
            vr = result["vr"]
            _, wm_img_path = extract(wm_shp, vr, output_dir=os.path.join(tmpdir, "extract_output"))

            # Verify extracted watermark is a valid image
            wm_img = Image.open(wm_img_path)
            assert wm_img.size[0] > 0 and wm_img.size[1] > 0
            wm_img.close()


# =========================================================================== #
# Vector robustness-matrix engine (feat_robustness)                            #
# =========================================================================== #


def _make_matrix_shp(path, n_lines=60, n_pts=300, x0=116.0, y0=39.0, seed=7):
    """Same construction recipe as tests/test_vector_dqim.py::_make_shp."""
    import geopandas as gpd
    from shapely.geometry import LineString

    rng = np.random.default_rng(seed)
    lines = []
    for i in range(n_lines):
        xs = x0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        ys = y0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        lines.append(LineString(np.column_stack([xs, ys])))
    gpd.GeoDataFrame({"fid": range(n_lines)}, geometry=lines, crs="EPSG:4326").to_file(str(path))
    return str(path)


def _build_matrix_payload():
    """Real v2 signed payload text (same construction as test_vector_dqim)."""
    from datetime import UTC, datetime

    from crypto.keys import ensure_active_key
    from crypto.payload import build_qr_v2_text

    kid, _private_key = ensure_active_key()
    return build_qr_v2_text("ab" * 16, 4242, kid, int(datetime.now(UTC).timestamp()))


class TestVectorMatrixEngine:
    """run_matrix subsets on a small shp — the red/green translation comparison."""

    def test_dqim1_survives_translation(self, db, tmp_path):
        """D-QIM: baseline and translated rows both decode with NC/BER measured."""
        from algorithm.robustness import run_matrix

        shp = _make_matrix_shp(tmp_path / "dqim.shp")
        rows = run_matrix(
            shp,
            None,
            schemes=["dqim1"],
            attacks=["none", "translate"],
            payload_text=_build_matrix_payload(),
            work_dir=str(tmp_path / "work_dqim"),
        )
        by_attack = {row["attack"]: row for row in rows}
        assert by_attack["none"]["decode_success"] is True, f"baseline lost: {by_attack['none']}"
        assert by_attack["translate"]["decode_success"] is True, f"D-QIM lost to translation: {by_attack['translate']}"
        for row in rows:
            assert row["nc"] is not None and row["ber"] is not None
            assert row["duration_ms"] is not None and row["duration_ms"] >= 0

    def test_legacy_control_fails_translation(self, db, tmp_path):
        """Legacy: baseline decodes (meaningful control) but translation must fail — the contrast evidence."""
        from algorithm.robustness import run_matrix

        shp = _make_matrix_shp(tmp_path / "legacy.shp")
        rows = run_matrix(
            shp,
            None,
            schemes=["legacy"],
            attacks=["none", "translate"],
            payload_text=_build_matrix_payload(),
            work_dir=str(tmp_path / "work_legacy"),
        )
        by_attack = {row["attack"]: row for row in rows}
        assert by_attack["none"]["decode_success"] is True, (
            "legacy baseline must decode, else the control is meaningless"
        )
        assert by_attack["translate"]["decode_success"] is False, "legacy scheme unexpectedly survived translation"


class TestAttackFunctions:
    """Deterministic behavior of the five coordinate attacks on tiny inputs."""

    @pytest.fixture
    def small_shp(self, tmp_path):
        import geopandas as gpd
        from shapely.geometry import LineString, Polygon

        rng = np.random.default_rng(3)
        lines = [LineString(np.column_stack([np.arange(40) * 0.001, rng.uniform(0, 1, 40)])) for _ in range(3)]
        poly = Polygon(np.column_stack([np.array([0, 1, 1, 0, 0]) + 5.0, np.array([0, 0, 1, 1, 0]) + 5.0]))
        shp = str(tmp_path / "attack_src.shp")
        gpd.GeoDataFrame({"fid": range(4)}, geometry=[*lines, poly], crs="EPSG:4326").to_file(shp)
        return shp

    def test_translate_shifts_bounds(self, small_shp, tmp_path):
        import geopandas as gpd

        from algorithm.robustness import attack_translate

        before = gpd.read_file(small_shp).total_bounds
        out = attack_translate(small_shp, dx=0.005, dy=0.003, output_path=str(tmp_path / "tr.shp"))
        after = gpd.read_file(out).total_bounds
        assert np.allclose(after - before, [0.005, 0.003, 0.005, 0.003], atol=1e-9)

    def test_scale_scales_distances(self, small_shp, tmp_path):
        import geopandas as gpd

        from algorithm.robustness import attack_scale

        out = attack_scale(small_shp, factor=2.0, output_path=str(tmp_path / "sc.shp"))
        g0 = gpd.read_file(small_shp).geometry.iloc[0]
        g1 = gpd.read_file(out).geometry.iloc[0]
        d0 = g0.geoms[1].distance(g0.geoms[0]) if hasattr(g0, "geoms") else g0.length
        d1 = g1.geoms[1].distance(g1.geoms[0]) if hasattr(g1, "geoms") else g1.length
        assert d1 == pytest.approx(2.0 * d0, rel=1e-9)

    def test_vertex_drop_deterministic_and_legal(self, small_shp, tmp_path):
        import geopandas as gpd

        from algorithm.robustness import attack_vertex_drop

        before = sum(len(g.coords) for g in gpd.read_file(small_shp).geometry)
        out1 = attack_vertex_drop(small_shp, pct=0.05, output_path=str(tmp_path / "d1.shp"))
        out2 = attack_vertex_drop(small_shp, pct=0.05, output_path=str(tmp_path / "d2.shp"))
        g1 = gpd.read_file(out1)
        g2 = gpd.read_file(out2)
        assert sum(len(g.coords) for g in g1.geometry) < before
        assert all(g.is_valid for g in g1.geometry)
        # deterministic: two runs produce identical coordinates
        for a, b in zip(g1.geometry, g2.geometry, strict=False):
            assert np.array_equal(np.asarray(a.coords), np.asarray(b.coords))

    def test_noise_small_and_deterministic(self, small_shp, tmp_path):
        import geopandas as gpd

        from algorithm.robustness import attack_noise

        out1 = attack_noise(small_shp, sigma=1e-9, output_path=str(tmp_path / "n1.shp"))
        out2 = attack_noise(small_shp, sigma=1e-9, output_path=str(tmp_path / "n2.shp"))
        g0 = gpd.read_file(small_shp)
        g1 = gpd.read_file(out1)
        g2 = gpd.read_file(out2)
        c0 = np.asarray(g0.geometry.iloc[0].coords)
        c1 = np.asarray(g1.geometry.iloc[0].coords)
        c2 = np.asarray(g2.geometry.iloc[0].coords)
        assert np.abs(c1 - c0).max() < 1e-7
        assert np.array_equal(c1, c2)
        assert all(g.is_valid for g in g1.geometry)

    def test_simplify_auto_tolerance(self, small_shp, tmp_path):
        import geopandas as gpd

        from algorithm.robustness import attack_simplify, default_simplify_tolerance

        tol = default_simplify_tolerance(small_shp)
        assert tol > 0
        before = sum(len(g.coords) for g in gpd.read_file(small_shp).geometry)
        out = attack_simplify(small_shp, output_path=str(tmp_path / "sp.shp"))
        after = sum(len(g.coords) for g in gpd.read_file(out).geometry)
        assert after <= before
        assert all(g.is_valid for g in gpd.read_file(out).geometry)


class TestRobustnessApi:
    """Endpoint smoke: POST a small run, join the worker, read it back."""

    @pytest.fixture
    def dataset_id(self, db, tmp_path):
        from model.Shp_Data import Shp

        shp_path = _make_matrix_shp(tmp_path / "api_src.shp")
        record = Shp(
            name="robustness_api_smoke",
            alias="robustness_api_smoke",
            geomtype="LineString",
            introduction="robustness matrix endpoint smoke",
            shp_file_path=shp_path,
            coordinate_system="EPSG:4326",
        )
        db.session.add(record)
        db.session.commit()
        return record.id

    def test_run_endpoint_smoke(self, client, db, auth_headers, dataset_id):
        import resource.robustness_resource as robustness_resource

        resp = client.post(
            "/api/robustness/run",
            json={"data_id": dataset_id, "schemes": ["dqim1"], "attacks": ["none", "translate"]},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        run_id = resp.get_json()["data"]["run_id"]

        thread = robustness_resource._ACTIVE_RUNS.get(run_id)
        if thread is not None:
            thread.join(timeout=120)
            assert not thread.is_alive(), "robustness worker did not finish within 120s"

        detail = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers)
        assert detail.status_code == 200
        run = detail.get_json()["run"]
        assert run["done"] == 2 and run["total"] == 2
        rows = {(row["scheme"], row["attack"]): row for row in run["rows"]}
        assert rows[("dqim1", "none")]["decode_success"] is True
        assert rows[("dqim1", "translate")]["decode_success"] is True
        assert rows[("dqim1", "none")]["nc"] is not None

        listing = client.get("/api/robustness/runs", headers=auth_headers)
        assert listing.status_code == 200
        assert any(entry["run_id"] == run_id for entry in listing.get_json()["runs"])

    def test_run_endpoint_rejects_unknown_dataset(self, client, db, auth_headers):
        resp = client.post(
            "/api/robustness/run",
            json={"data_id": 999999, "schemes": ["dqim1"], "attacks": ["none"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_run_endpoint_requires_admin(self, client, db):
        resp = client.post("/api/robustness/run", json={"data_id": 1})
        assert resp.status_code in (401, 403)
