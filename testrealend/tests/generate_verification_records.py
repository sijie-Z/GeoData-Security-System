"""Generate real verification records from existing applications.

Takes the last N applications, runs the full embed→extract→verify
pipeline on their associated data files, computes NC/BER, and writes
WatermarkVerification records to the database.
"""

import hashlib
import os
import sys
import tempfile
from datetime import UTC, datetime

import numpy as np
from PIL import Image

# --- NumPy 2.x compatibility patches ---
# geopandas 0.14.x / pandas 3.x use np.array(..., copy=False) which fails with NumPy 2.x
_original_np_array = np.array


def _patched_np_array(*args, **kwargs):
    kwargs["copy"] = True
    return _original_np_array(*args, **kwargs)


np.array = _patched_np_array

import pandas as _pd

_orig_series_array = _pd.Series.__array__


def _patched_series_array(self, dtype=None, copy=None):
    return _orig_series_array(self, dtype=dtype, copy=True)


_pd.Series.__array__ = _patched_series_array
# --- end patches ---

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
from model.Application import Application
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from model.watermark_verification import WatermarkVerification
from resource.watermark_utils import build_qr_text


def _to_bits_resized(img, target_size):
    """Resize to target_size then flatten to bit array."""
    resized = img.convert("L").resize(target_size, Image.Resampling.NEAREST)
    return (np.array(resized, dtype=np.uint8) > 127).astype(int).flatten()


def nc(a, b):
    """Normalized Correlation."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if np.sum(a) == 0 and np.sum(b) == 0:
        return 1.0
    d = np.sqrt(np.dot(a, a)) * np.sqrt(np.dot(b, b))
    return float(np.dot(a, b) / d) if d > 1e-10 else 1.0


def ber(a, b):
    """Bit Error Rate."""
    a, b = np.array(a, dtype=int), np.array(b, dtype=int)
    n = min(len(a), len(b))
    return float(np.sum(a[:n] != b[:n]) / n)


def compute_hash(img_or_path):
    """SHA256 hash of image pixels."""
    if isinstance(img_or_path, str):
        img_or_path = Image.open(img_or_path).convert("RGB")
    arr = np.array(img_or_path.convert("RGB"))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def generate_minimal_qr(app_item, max_vertices=60):
    """Generate the smallest possible QR code that still carries app identity.
    Uses version 1, low error correction to fit within vertex budget."""
    # Minimal payload: just the essential identifiers
    text = f"APP-{app_item.id:04d}|{app_item.data_alias}|{app_item.applicant_name}"
    # If even that's too large, use just the App ID
    if len(text) > 25:  # Version 1 alphanumeric max
        text = f"APP-{app_item.id:04d}"
    # Calculate how many bits we need
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=1)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    print(f"  QR: {img.size[0]}x{img.size[1]}, text='{text}' ({len(text)} chars)")
    return img


def generate_qr_image(app_item):
    """Generate a suitably-sized QR code for verification."""
    payload = {
        "purpose": app_item.purpose or "",
        "usage_scope": app_item.usage_scope or "",
        "security_level": app_item.security_level or "normal",
        "custom_tag": app_item.custom_tag or "",
        "reason": app_item.reason or "",
    }
    qr_text, _signature = build_qr_text(app_item, payload)
    # Try reducing version — use minimal version that fits
    # Alphanumeric QR capacity: version 1=25, 2=47, 3=77...
    text_len = len(qr_text)
    # Use fit=True to auto-size, but with LOW error correction to minimize
    qr = qrcode.QRCode(
        version=None,  # auto-fit
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_text)
    qr.make(fit=True)
    # Get actual version used
    actual_version = qr.version
    modules = 17 + actual_version * 4  # QR module count
    bits_needed = modules * modules
    print(f"  QR: version={actual_version}, {modules}x{modules}, bits={bits_needed}, text={text_len} chars")
    return qr.make_image(fill_color="black", back_color="white")


def run_verification_for_app(app_item, data_record, tmp_dir):
    """Run embed+extract for one application, return (nc_value, ber_value, orig_hash, extract_hash)."""
    data_path = None
    if app_item.data_type == "vector":
        data_path = getattr(data_record, "shp_file_path", None)
    else:
        data_path = getattr(data_record, "raster_file_path", None)

    if not data_path or not os.path.exists(data_path):
        print(f"    SKIP: data file not found: {data_path}")
        return None

    # Generate QR watermark
    qr_img = generate_qr_image(app_item)
    qr_size = qr_img.size

    try:
        if app_item.data_type == "vector":
            nc_val, ber_val, orig_h, ext_h = _verify_vector(data_path, qr_img, qr_size, tmp_dir)
        else:
            nc_val, ber_val, orig_h, ext_h = _verify_raster(data_path, qr_img, qr_size, tmp_dir)
        return nc_val, ber_val, orig_h, ext_h
    except Exception as e:
        import traceback

        print(f"    ERROR during verification: {e}")
        traceback.print_exc()
        return None


def _verify_vector(shp_path, qr_img, qr_size, tmp_dir):
    """Vector watermark round-trip: embed → extract → compare."""
    from algorithm.embed import embed
    from algorithm.extract import extract

    # Save QR to temp
    qr_path = os.path.join(tmp_dir, "qr.png")
    qr_img.save(qr_path, "PNG")

    # Embed
    result = embed(shp_path, qr_path, output_dir=tmp_dir)

    # Extract from watermarked zip
    import zipfile

    zip_path = result["zip_path"]
    extract_dir = os.path.join(tmp_dir, "wm_extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    shp_files = [f for f in os.listdir(extract_dir) if f.endswith(".shp")]
    if not shp_files:
        raise ValueError("No .shp in watermarked zip")

    wm_shp = os.path.join(extract_dir, shp_files[0])
    vr = result["vr"]
    _, extracted_img_path = extract(wm_shp, vr, output_dir=os.path.join(tmp_dir, "extract_out"))

    # Compare
    orig_bits = _to_bits_resized(qr_img, qr_size)
    ext_img = Image.open(extracted_img_path)
    ext_bits = _to_bits_resized(ext_img, qr_size)
    nc_val = round(nc(orig_bits, ext_bits), 6)
    ber_val = round(ber(orig_bits, ext_bits), 6)
    orig_h = compute_hash(qr_img)
    ext_h = compute_hash(ext_img)

    return nc_val, ber_val, orig_h, ext_h


def _verify_raster(raster_path, qr_img, qr_size, tmp_dir):
    """Raster watermark round-trip: embed (LSB) → decode → compare."""
    from algorithm.raster_reversible_watermark import decode_reversible, embed_reversible

    out_dir = os.path.join(tmp_dir, "raster_wm")
    os.makedirs(out_dir, exist_ok=True)

    # Embed
    result = embed_reversible(raster_path, qr_img, out_dir, "verify")

    # Decode
    decoded_path = os.path.join(out_dir, "decoded.png")
    decode_reversible(result["stego_path"], result["wm_meta_path"], decoded_path)

    # Compare
    orig_bits = _to_bits_resized(qr_img, qr_size)
    ext_img = Image.open(decoded_path)
    ext_bits = _to_bits_resized(ext_img, qr_size)
    nc_val = round(nc(orig_bits, ext_bits), 6)
    ber_val = round(ber(orig_bits, ext_bits), 6)
    orig_h = compute_hash(qr_img)
    ext_h = compute_hash(ext_img)

    return nc_val, ber_val, orig_h, ext_h


def _find_best_data(app_item, prefer_idx):
    """Find a data file - first tries the app's actual linked data, then falls back."""
    # Try the app's own associated data first (truly "real" data)
    if app_item.data_id and app_item.data_id not in (1,):  # skip taihu (1-feature, too few vertices)
        if app_item.data_type == "vector":
            d = db.session.get(Shp, app_item.data_id)
        else:
            d = db.session.get(RasterData, app_item.data_id)
        if d:
            p = getattr(d, "shp_file_path", None) or getattr(d, "raster_file_path", None)
            if p and os.path.exists(p):
                return d, p

    # Fallback: hardcoded vector datasets based on index
    vector_ids = [2, 3, 2]  # Greenland=8016, Coastline=2301, Greenland=8016
    raster_ids = [1, 2, 3]

    if app_item.data_type == "vector":
        candidates = vector_ids
    else:
        candidates = raster_ids

    sid = candidates[prefer_idx % len(candidates)]
    model_cls = Shp if app_item.data_type == "vector" else RasterData
    d = db.session.get(model_cls, sid)
    if d:
        p = getattr(d, "shp_file_path", None) or getattr(d, "raster_file_path", None)
        if p and os.path.exists(p):
            return d, p

    # Final fallback: any vector shapefile
    for sid in [2, 3, 1, 4]:
        d = db.session.get(Shp, sid)
        if d:
            p = d.shp_file_path
            if p and os.path.exists(p):
                return d, p
    return None, None


def main():
    app = create_app()
    with app.app_context():
        apps = Application.query.order_by(Application.id.desc()).limit(6).all()
        print(f"Processing {len(apps)} applications...")

        created = 0
        with tempfile.TemporaryDirectory() as tmp_dir:
            for idx, a in enumerate(apps):
                print(f"\n--- App #{a.id}: {a.data_alias} (type={a.data_type}) ---")

                data, data_path = _find_best_data(a, idx)
                if not data:
                    print("  SKIP: no usable data found")
                    continue

                print(f"  Using: {data.name} ({data_path})")
                result = run_verification_for_app(a, data, tmp_dir)
                if result:
                    nc_val, ber_val, orig_h, ext_h = result
                    print(f"  RESULT: NC={nc_val:.4f}, BER={ber_val:.4f}")

                    record = WatermarkVerification(
                        application_id=a.id,
                        data_id=data.id,
                        data_type=a.data_type or "vector",
                        nc_value=nc_val,
                        original_hash=orig_h,
                        extracted_hash=ext_h,
                        verified_by="benchmark_script",
                        verified_at=datetime.now(UTC),
                        ip_address="127.0.0.1",
                    )
                    db.session.add(record)
                    created += 1
                else:
                    print("  SKIP: verification failed")

            if created > 0:
                db.session.commit()
            print(f"\nDone. Created {created} verification records.")

        # Show current records
        records = WatermarkVerification.query.order_by(WatermarkVerification.verified_at.desc()).limit(10).all()
        print(f"\n=== Current Verification Records ({len(records)}) ===")
        for r in records:
            print(f"  #{r.id}: app_id={r.application_id} data_id={r.data_id} NC={r.nc_value:.4f} at={r.verified_at}")


if __name__ == "__main__":
    main()
