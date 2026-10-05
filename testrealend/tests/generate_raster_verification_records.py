"""Generate raster watermark verification records using synthetic test images.

Creates test raster data, runs embed→extract→verify pipeline for LSB and DWT
algorithms, and writes WatermarkVerification records to the database.
This populates the WatermarkQualityDashboard with raster verification data.
"""

import os
import sys
import tempfile
from datetime import UTC, datetime

import numpy as np
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Use importlib to avoid collision with global 'app' package
import importlib.util

_spec = importlib.util.spec_from_file_location("myapp", os.path.join(PROJECT_ROOT, "app.py"))
_app_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_app_module)
create_app = _app_module.create_app

import qrcode

from extension.extension import db
from model.watermark_verification import WatermarkVerification


def create_test_raster(size=256):
    """Create a synthetic terrain-like raster image for testing."""
    Y, X = np.ogrid[:size, :size]
    cx, cy = size // 2, size // 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    base = np.clip((1 - dist / (size * 0.7)) * 200 + 30, 0, 255)

    x = np.linspace(0, 4 * np.pi, size)
    y = np.linspace(0, 4 * np.pi, size)
    Xm, Ym = np.meshgrid(x, y)
    waves = np.sin(Xm) * np.cos(Ym) * 30 + np.sin(Xm * 2.5) * np.cos(Ym * 1.8) * 20 + np.sin(Xm * 0.7 + Ym * 1.3) * 25

    spots = (
        np.exp(-((X - size * 0.3) ** 2 + (Y - size * 0.4) ** 2) / 2000) * 80
        + np.exp(-((X - size * 0.7) ** 2 + (Y - size * 0.6) ** 2) / 3000) * 60
        + np.exp(-((X - size * 0.5) ** 2 + (Y - size * 0.25) ** 2) / 1500) * 90
    )

    r = np.clip(base + waves + spots, 0, 255).astype(np.uint8)
    g = np.clip(base + waves * 0.9 + spots * 1.1 + 5, 0, 255).astype(np.uint8)
    b = np.clip(base + waves * 1.1 + spots * 0.9 - 3, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([r, g, b], axis=-1), mode="RGB")


def create_watermark(size=64):
    """Create a QR-code-like binary watermark pattern."""
    wm = np.zeros((size, size), dtype=np.uint8)
    # Finder patterns (3 corners)
    for ox, oy in [(0, 0), (0, size - 8), (size - 8, 0)]:
        wm[ox : ox + 8, oy : oy + 8] = 255
        wm[ox + 1 : ox + 7, oy + 1 : oy + 7] = 0
        wm[ox + 2 : ox + 6, oy + 2 : oy + 6] = 255
    # Data modules
    for i in range(8, size, 3):
        for j in range(8, size, 3):
            if (i + j) % 5 == 0:
                wm[i : min(i + 2, size), j : min(j + 2, size)] = 255
    # Timing patterns
    for j in range(8, size, 2):
        wm[6, j] = 255
        wm[j, 6] = 255
    return Image.fromarray(wm, mode="L")


def _to_bits_resized(img, target_size):
    """Resize to target_size then flatten to bit array."""
    resized = img.convert("L").resize(target_size, Image.Resampling.NEAREST)
    return (np.array(resized, dtype=np.uint8) > 127).astype(int).flatten()


def compute_nc(a, b):
    """Normalized Correlation."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if np.sum(a) == 0 and np.sum(b) == 0:
        return 1.0
    d = np.sqrt(np.dot(a, a)) * np.sqrt(np.dot(b, b))
    return float(np.dot(a, b) / d) if d > 1e-10 else 1.0


def compute_ber(a, b):
    """Bit Error Rate."""
    a, b = np.array(a, dtype=int), np.array(b, dtype=int)
    n = min(len(a), len(b))
    return float(np.sum(a[:n] != b[:n]) / n)


def verify_raster_lsb(host_path, qr_img, qr_size, tmp_dir):
    """Raster LSB watermark round-trip: embed → decode → compare."""
    from algorithm.raster_reversible_watermark import decode_reversible, embed_reversible

    out_dir = os.path.join(tmp_dir, "lsb")
    os.makedirs(out_dir, exist_ok=True)

    result = embed_reversible(host_path, qr_img, out_dir, "verify")
    decoded_path = os.path.join(out_dir, "decoded.png")
    decode_reversible(result["stego_path"], result["wm_meta_path"], decoded_path)

    orig_bits = _to_bits_resized(qr_img, qr_size)
    ext_img = Image.open(decoded_path)
    ext_bits = _to_bits_resized(ext_img, qr_size)
    nc_val = round(compute_nc(orig_bits, ext_bits), 6)
    ber_val = round(compute_ber(orig_bits, ext_bits), 6)

    return nc_val, ber_val


def verify_raster_dwt(host_path, qr_img, qr_size, tmp_dir):
    """Raster DWT watermark round-trip: embed → extract → compare."""
    from algorithm.raster_dwt_watermark import embed_dwt, extract_dwt

    out_dir = os.path.join(tmp_dir, "dwt")
    os.makedirs(out_dir, exist_ok=True)

    result = embed_dwt(host_path, qr_img, out_dir, "verify")
    decoded_path = os.path.join(out_dir, "decoded.png")
    extract_dwt(result["stego_path"], result["wm_meta_path"], decoded_path)

    orig_bits = _to_bits_resized(qr_img, qr_size)
    ext_img = Image.open(decoded_path)
    ext_bits = _to_bits_resized(ext_img, qr_size)
    nc_val = round(compute_nc(orig_bits, ext_bits), 6)
    ber_val = round(compute_ber(orig_bits, ext_bits), 6)

    return nc_val, ber_val


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("  Raster Watermark Verification Record Generator")
        print("=" * 60)

        created = 0
        qr_size = (64, 64)
        qr_img = create_watermark(64)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Save host image
            host_img = create_test_raster(256)
            host_path = os.path.join(tmp_dir, "host.png")
            host_img.save(host_path, "PNG")

            # Generate multiple verification records for each algorithm
            algorithms = [
                ("LSB", verify_raster_lsb),
                ("DWT", verify_raster_dwt),
            ]

            for algo_name, verify_fn in algorithms:
                print(f"\n--- Testing {algo_name} algorithm ---")
                for i in range(5):  # 5 records per algorithm
                    try:
                        nc_val, ber_val = verify_fn(host_path, qr_img, qr_size, tmp_dir)
                        print(f"  Record {i + 1}: NC={nc_val:.4f}, BER={ber_val:.4f}")

                        record = WatermarkVerification(
                            application_id=100 + i,  # Fake app ID
                            data_id=1,
                            data_type="raster",
                            nc_value=nc_val,
                            original_hash="test_raster_hash",
                            extracted_hash=f"extracted_{algo_name.lower()}_{i}",
                            verified_by=f"benchmark_{algo_name.lower()}",
                            verified_at=datetime.now(UTC),
                            ip_address="127.0.0.1",
                        )
                        db.session.add(record)
                        created += 1
                    except Exception as e:
                        print(f"  Record {i + 1}: FAILED - {e}")

        if created > 0:
            db.session.commit()
            print(f"\n✓ Created {created} raster verification records.")
        else:
            print("\n✗ No records created.")

        # Show summary
        records = (
            WatermarkVerification.query.filter_by(data_type="raster")
            .order_by(WatermarkVerification.verified_at.desc())
            .limit(10)
            .all()
        )

        print(f"\n=== Raster Verification Records ({len(records)}) ===")
        for r in records:
            print(f"  #{r.id}: app_id={r.application_id} NC={r.nc_value:.4f} by={r.verified_by}")

        # Show totals
        total = WatermarkVerification.query.count()
        raster_count = WatermarkVerification.query.filter_by(data_type="raster").count()
        vector_count = WatermarkVerification.query.filter_by(data_type="vector").count()
        print(f"\nTotal: {total} (Vector: {vector_count}, Raster: {raster_count})")


if __name__ == "__main__":
    main()
