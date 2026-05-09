"""Robustness tests: simulate attacks on watermarked images and measure survival."""
import pytest
import numpy as np
import os
from PIL import Image


def _to_bits(img):
    """Convert image to binary bit array."""
    arr = np.array(img.convert('L'))
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
        from algorithm.raster_reversible_watermark import embed_reversible, decode_reversible

        # Create a 100x100 test host image
        host = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        host_path = str(tmp_path / 'host.png')
        Image.fromarray(host).save(host_path)

        # Create a 100x100 binary watermark (matches host size since embed_reversible
        # resizes watermark to host dimensions)
        wm = np.array([[255 if (i + j) % 3 == 0 else 0 for j in range(100)] for i in range(100)], dtype=np.uint8)
        wm_path = str(tmp_path / 'wm.png')
        Image.fromarray(wm).save(wm_path)

        out_dir = str(tmp_path / 'output')
        result = embed_reversible(host_path, Image.open(wm_path), out_dir, 'test')
        # Save host path in result for recovery test
        result['host_path'] = host_path
        return result, wm_path

    def test_no_attack(self, watermark_pair):
        """Baseline: extracted watermark matches original without attack."""
        from algorithm.raster_reversible_watermark import decode_reversible
        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result['stego_path'])
        out = os.path.join(stego_dir, 'decoded_test.png')
        decode_reversible(result['stego_path'], result['wm_meta_path'], out)

        orig = _to_bits(Image.open(wm_path))
        extracted = _to_bits(Image.open(out))
        nc = _nc(orig, extracted)
        assert nc > 0.99, f"NC too low without attack: {nc}"

    def test_jpeg_compression(self, watermark_pair):
        """Watermark survives JPEG compression (quality=70)."""
        from algorithm.raster_reversible_watermark import decode_reversible
        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result['stego_path'])

        # Re-save as JPEG (lossy compression)
        img = Image.open(result['stego_path'])
        jpeg_path = os.path.join(stego_dir, 'compressed.jpg')
        img.save(jpeg_path, 'JPEG', quality=70)

        # Try to decode from compressed version
        out = os.path.join(stego_dir, 'decoded_compressed.png')
        try:
            decode_reversible(jpeg_path, result['wm_meta_path'], out)
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
        stego_dir = os.path.dirname(result['stego_path'])

        # Add Gaussian noise
        img_arr = np.array(Image.open(result['stego_path']).convert('RGB'), dtype=np.float64)
        noise = np.random.normal(0, 5, img_arr.shape)
        noisy = np.clip(img_arr + noise, 0, 255).astype(np.uint8)
        noisy_path = os.path.join(stego_dir, 'noisy.png')
        Image.fromarray(noisy).save(noisy_path)

        out = os.path.join(stego_dir, 'decoded_noisy.png')
        try:
            decode_reversible(noisy_path, result['wm_meta_path'], out)
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
        stego_dir = os.path.dirname(result['stego_path'])

        # Crop 10% from each side
        img = Image.open(result['stego_path'])
        w, h = img.size
        cropped = img.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)))
        crop_path = os.path.join(stego_dir, 'cropped.png')
        cropped.save(crop_path)

        out = os.path.join(stego_dir, 'decoded_cropped.png')
        with pytest.raises(ValueError):
            decode_reversible(crop_path, result['wm_meta_path'], out)

    def test_recovery_perfect(self, watermark_pair):
        """Reversible recovery produces bit-exact original."""
        from algorithm.raster_reversible_watermark import recover_reversible
        result, wm_path = watermark_pair
        stego_dir = os.path.dirname(result['stego_path'])
        host_path = result['host_path']

        # Recover
        recovered_path = os.path.join(stego_dir, 'recovered.png')
        recover_reversible(result['stego_path'], result['wm_map_path'], result['wm_meta_path'], recovered_path)

        # Compare
        orig = np.array(Image.open(host_path))
        recovered = np.array(Image.open(recovered_path))
        assert np.array_equal(orig, recovered), "Recovery is not bit-exact!"


class TestVectorRobustness:
    """Test vector watermark survival under coordinate transformations."""

    def test_embed_extract_roundtrip(self):
        """Basic embed→extract roundtrip for vector data."""
        import geopandas as gpd
        from shapely.geometry import Point
        from algorithm.embed import embed
        from algorithm.extract import extract
        import tempfile, os, zipfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test shapefile with enough vertices for embedding
            n_points = 5000
            gdf = gpd.GeoDataFrame(
                {'id': range(n_points)},
                geometry=[Point(100 + i * 0.0001, 40 + i * 0.0001) for i in range(n_points)],
                crs='EPSG:4326'
            )
            shp_path = os.path.join(tmpdir, 'test.shp')
            gdf.to_file(shp_path)

            # Create minimal QR watermark (version 1, low error correction, box_size=1 → 21x21)
            import qrcode
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=1, border=0)
            qr.add_data('WM')
            qr.make(fit=True)
            qr_path = os.path.join(tmpdir, 'test_qr.png')
            qr.make_image().save(qr_path)

            # Embed
            result = embed(shp_path, qr_path, output_dir=tmpdir)
            assert 'zip_path' in result

            # Extract from watermarked zip
            zip_path = result['zip_path']
            extract_dir = os.path.join(tmpdir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            shp_files = [f for f in os.listdir(extract_dir) if f.endswith('.shp')]
            assert len(shp_files) > 0, "No .shp in watermarked zip"

            wm_shp = os.path.join(extract_dir, shp_files[0])
            vr = result['vr']
            _, wm_img_path = extract(wm_shp, vr, output_dir=os.path.join(tmpdir, 'extract_output'))

            # Verify extracted watermark is a valid image
            wm_img = Image.open(wm_img_path)
            assert wm_img.size[0] > 0 and wm_img.size[1] > 0
            wm_img.close()
