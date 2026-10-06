"""Robustness experiment matrix engine for the raster watermarking schemes.

Sibling of ``algorithm/robustness.py`` (the vector engine). For every raster
scheme the same QR payload is embedded once into a synthetic host GeoTIFF, the
no-attack baseline is measured first, then every image attack is applied to a
copy of the stego raster and read back with that scheme's extractor. One row
per (scheme, attack) carries the same keys as the vector engine:

  * ``decode_success`` — ``decode_qr_from_image`` returned exactly the payload
    text the QR carries (the payload-level gate);
  * ``nc`` / ``ber`` — bit-level fidelity between the extracted watermark
    bitmap and the ground-truth bitmap the scheme actually embedded: the
    payload QR converted to ``L`` and NEAREST-resized to the embedded
    watermark dimensions (no resize for blind, which embeds the QR at its
    natural size). This mirrors the vector convention, where the extracted
    bitmap is compared against the payload bitmap at the embedded size. A QR
    that cannot be decoded at all yields ``decode_success=False`` with NC/BER
    ``None`` (nothing to compare), exactly like the vector matrix;
  * ``duration_ms`` — wall time of the attack + extract + decode + metrics cell.

Schemes (label -> implementation):
  * ``lsb``       -> ``raster_reversible_watermark.embed_reversible`` / ``decode_reversible``
  * ``dwt``       -> ``raster_dwt_watermark.embed_dwt`` / ``extract_dwt``
  * ``histogram`` -> ``raster_histogram_watermark.embed_histogram`` / ``extract_histogram``
  * ``blind``     -> ``raster_blind_watermark.embed_blind`` / ``extract_blind``

Host: ``make_host_tif`` writes a deterministic 512x512 3-band uint8 GeoTIFF
with CRS EPSG:4326 (same construction as ``tests/test_raster.py::_make_geotiff``,
seed 7; ``fill`` writes a constant value, which the histogram scheme needs to
find a dominant peak).

Attacks (each reads the stego raster, edits pixels, and writes a new GeoTIFF
keeping CRS/transform from the stego profile, or from the host profile when
the stego itself carries no georeference — the DWT scheme writes a PNG stego):
``jpeg`` / ``resize`` / ``crop`` / ``rotate`` / ``noise`` / ``blur`` plus the
``none`` baseline. Defaults live in ``RASTER_ATTACK_DEFAULTS``; ``resize``
deliberately does NOT scale back up (the extractor sees the real attacked
size), per the taskbook decision.

Payload sizing (smoke-measured): the real ~191-char v2 payload renders as a
57x57 px QR at ``box_size=1`` / ECC L (``render_raster_payload_qr``). A
512x512 host provides the blind scheme floor(((H+1)/2)/4) * floor(((W+1)/2)/4)
= 4096 embeddable bits and the library requires ``wm_bits < block_num``, so
57x57 = 3249 bits fits, while the delivery-default ``box_size=2`` QR (~130 px,
~16900 bits) and even ``box_size=1`` at ECC M (65x65 = 4225 bits) exceed it.
The other three schemes resize the payload bitmap to their own working size
anyway, so one small QR serves all four schemes identically.

Discipline: everything here is a pure function of its arguments — no Flask
context, no DB, no globals; outputs go under the caller-provided ``work_dir``.
Failures are first-class data: an embed that cannot fit the host yields one
error row per requested attack; an extractor that cannot run on the attacked
geometry (e.g. the reversible decoder rejects a resized input) is recorded as
a cell error; nothing is prettified.
"""

import io
import json
import logging
import os
import time

import numpy as np

# Same fixture extent as tests/test_raster.py (a small box over Hangzhou, WGS84).
HOST_BOUNDS = (119.9, 29.9, 120.1, 30.1)

# The four raster schemes the raster matrix compares.
RASTER_SCHEMES = ("lsb", "dwt", "histogram", "blind")

# Standard attack set: the no-attack baseline first, then the image attacks.
# "blur" is supported by the engine but not part of the default whitelist runs
# (the reference matrix is 4 schemes x [none, jpeg, resize, crop, rotate, noise]).
RASTER_ATTACKS = ("none", "jpeg", "resize", "crop", "rotate", "noise", "blur")

# Default parameters per attack (attack_params recorded per row).
RASTER_ATTACK_DEFAULTS = {
    "none": {},
    "jpeg": {"quality": 70},
    "resize": {"factor": 0.5},
    "crop": {"keep": 0.7},
    "rotate": {"deg": 5.0},
    "noise": {"sigma": 5.0},
    "blur": {"radius": 3.0},
}

# Fixed seed for the deterministic Gaussian-noise attack (same as the vector
# engine's noise attack).
RASTER_NOISE_SEED = 11

# Payload QR rendering for the raster matrix: box_size=1 and ECC L keep the
# real v2 payload at 57x57 px (3249 bits), under the 512-host blind budget of
# 4095 embeddable bits. See the module docstring.
PAYLOAD_QR_BOX_SIZE = 1


# --------------------------------------------------------------------------- #
# host + payload                                                               #
# --------------------------------------------------------------------------- #


def make_host_tif(path, size=512, seed=7, fill=None):
    """Write the deterministic synthetic host: a 3-band uint8 GeoTIFF, EPSG:4326.

    Same construction as ``tests/test_raster.py::_make_geotiff`` (uniform random
    noise, seed 7) with an optional constant ``fill`` — the histogram scheme
    needs a dominant histogram peak and can only embed into a (near-)constant
    host at full payload size, so callers wanting histogram cells pass ``fill``.
    """
    import rasterio
    from rasterio.transform import from_bounds

    rng = np.random.default_rng(seed)
    if fill is None:
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
        transform=from_bounds(*HOST_BOUNDS, size, size),
    ) as dst:
        dst.write(data)
    return path


def render_raster_payload_qr(text, out_path):
    """Render the raster-matrix payload QR at the size blind can carry.

    ``box_size=1`` with ECC L puts the real v2 payload at 57x57 px (3249 bits
    < the 512-host blind budget); the delivery default (box_size=2, ECC M,
    ~130 px) is ~16900 bits and cannot be embedded. Returns
    ``(png_path, side_length_px)`` like the underlying renderer.
    """
    import qrcode

    from delivery.qr2 import render_v2_qr_png

    return render_v2_qr_png(
        text,
        out_path,
        box_size=PAYLOAD_QR_BOX_SIZE,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
    )


# --------------------------------------------------------------------------- #
# raster helpers                                                               #
# --------------------------------------------------------------------------- #


def _read_rgb_uint8(path):
    """Load *path* as an (H, W, 3) uint8 RGB array plus its rasterio profile.

    Same band conventions as the raster algorithm modules (first three bands of
    a multi-band raster, grayscale replicated), so attacks and extractors see
    identical pixels.
    """
    from algorithm.raster_geotiff_utils import read_geotiff

    arr, profile = read_geotiff(path)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    elif arr.shape[2] == 1:
        arr = np.concatenate([arr] * 3, axis=-1)
    elif arr.shape[2] > 3:
        arr = arr[:, :, :3]
    return arr.astype(np.uint8), profile


def _write_attacked(arr, output_path, src_profile, base_profile):
    """Write an attacked raster, keeping georeference where available.

    Uses the stego's own profile when it is a GeoTIFF; otherwise falls back to
    the host's profile (the DWT scheme writes a PNG stego). Returns the path
    actually written.
    """
    from algorithm.raster_geotiff_utils import save_geotiff

    profile = src_profile if src_profile.get("geotiff") else (base_profile or src_profile)
    return save_geotiff(arr, profile, output_path)


def _default_output(stego_path, tag):
    root, ext = os.path.splitext(str(stego_path))
    return f"{root}_{tag}{ext or '.tif'}"


# --------------------------------------------------------------------------- #
# attacks (each reads a stego raster and writes a new attacked raster)         #
# --------------------------------------------------------------------------- #


def r_jpeg(stego_path, quality=70, output_path=None, base_profile=None):
    """Lossy recompression: encode the stego as JPEG at ``quality``, decode back.

    The classic fragile-watermark killer (LSB) and a realistic distribution
    attack; the attacked raster is re-written as a GeoTIFF (CRS kept) so the
    extractors' GeoTIFF-aware loaders stay on one path.
    """
    from PIL import Image

    arr, profile = _read_rgb_uint8(stego_path)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="JPEG", quality=int(quality))
    buf.seek(0)
    with Image.open(buf) as img:
        attacked = np.asarray(img.convert("RGB"), dtype=np.uint8)
    return _write_attacked(attacked, output_path or _default_output(stego_path, "jpeg"), profile, base_profile)


def r_resize(stego_path, factor=0.5, output_path=None, base_profile=None):
    """Bilinear downsample by ``factor`` (no scaling back up).

    The extractor sees the real attacked size — schemes whose metadata is
    hard-bound to the original dimensions fail honestly (e.g. the reversible
    decoder rejects a size-mismatched input).
    """
    from PIL import Image

    arr, profile = _read_rgb_uint8(stego_path)
    h, w = arr.shape[:2]
    new_size = (max(1, round(w * float(factor))), max(1, round(h * float(factor))))
    attacked = np.asarray(Image.fromarray(arr, mode="RGB").resize(new_size, Image.Resampling.BILINEAR), dtype=np.uint8)
    return _write_attacked(attacked, output_path or _default_output(stego_path, "resize"), profile, base_profile)


def r_crop(stego_path, keep=0.7, output_path=None, base_profile=None):
    """Center crop keeping ``keep`` of each side (default 70%).

    Pixel coordinates shift relative to the original frame, so block grids and
    metadata-bound readers see a geometry mismatch unless the scheme realigns
    (the blind extractor attempts template realignment against the host).
    """
    arr, profile = _read_rgb_uint8(stego_path)
    h, w = arr.shape[:2]
    nh = max(1, round(h * float(keep)))
    nw = max(1, round(w * float(keep)))
    top, left = (h - nh) // 2, (w - nw) // 2
    attacked = arr[top : top + nh, left : left + nw]
    return _write_attacked(attacked, output_path or _default_output(stego_path, "crop"), profile, base_profile)


def r_rotate(stego_path, deg=5.0, output_path=None, base_profile=None):
    """Rotate by ``deg`` degrees (bilinear, expand=False, constant border fill).

    The frame size is unchanged, so dimension-checking extractors still run —
    the payload survives only if the algorithm itself is rotation-robust.
    """
    from PIL import Image

    arr, profile = _read_rgb_uint8(stego_path)
    img = Image.fromarray(arr, mode="RGB").rotate(
        float(deg), resample=Image.Resampling.BILINEAR, expand=False, fillcolor=(0, 0, 0)
    )
    return _write_attacked(
        np.asarray(img, dtype=np.uint8), output_path or _default_output(stego_path, "rotate"), profile, base_profile
    )


def r_noise(stego_path, sigma=5.0, seed=RASTER_NOISE_SEED, output_path=None, base_profile=None):
    """Additive Gaussian noise, sigma in the 0-255 domain; fixed seed (deterministic)."""
    arr, profile = _read_rgb_uint8(stego_path)
    rng = np.random.default_rng(seed)
    attacked = np.clip(arr.astype(np.float64) + rng.normal(0.0, float(sigma), arr.shape), 0, 255).astype(np.uint8)
    return _write_attacked(attacked, output_path or _default_output(stego_path, "noise"), profile, base_profile)


def r_blur(stego_path, radius=3.0, output_path=None, base_profile=None):
    """Gaussian blur with the given PIL radius (optional attack, engine-supported)."""
    from PIL import Image, ImageFilter

    arr, profile = _read_rgb_uint8(stego_path)
    img = Image.fromarray(arr, mode="RGB").filter(ImageFilter.GaussianBlur(radius=float(radius)))
    return _write_attacked(
        np.asarray(img, dtype=np.uint8), output_path or _default_output(stego_path, "blur"), profile, base_profile
    )


_ATTACK_FUNCTIONS = {
    "jpeg": r_jpeg,
    "resize": r_resize,
    "crop": r_crop,
    "rotate": r_rotate,
    "noise": r_noise,
    "blur": r_blur,
}


# --------------------------------------------------------------------------- #
# matrix orchestration                                                         #
# --------------------------------------------------------------------------- #


def _ordered_attacks(attacks):
    """The no-attack baseline first, then the rest in caller order."""
    rest = [a for a in attacks if a != "none"]
    return (["none"] if "none" in attacks else []) + rest


def _row(scheme, attack, attack_params, decode_success, nc=None, ber=None, duration_ms=None, error=None):
    return {
        "scheme": scheme,
        "attack": attack,
        "attack_params": attack_params,
        "decode_success": decode_success,
        "nc": nc,
        "ber": ber,
        "duration_ms": duration_ms,
        "error": error,
    }


def _image_bits(image_path, size=None):
    """Flatten an image into a 0/1 bit sequence (threshold at 128).

    ``size`` (PIL ``(width, height)``) reproduces the NEAREST resize the embed
    side applies to the payload, so the ground-truth bits match what was
    actually embedded; no resize happens when the size already matches.
    """
    from PIL import Image

    img = Image.open(image_path).convert("L")
    if size is not None and img.size != tuple(size):
        img = img.resize(tuple(size), Image.Resampling.NEAREST)
    return (np.asarray(img) > 127).astype(int).flatten()


def _watermark_dims(wm_meta_path):
    """Embedded watermark bitmap dimensions recorded by every raster scheme."""
    with open(wm_meta_path, encoding="utf-8") as fp:
        meta = json.load(fp)
    return int(meta["watermark"]["width"]), int(meta["watermark"]["height"])


def _embed_stego(scheme, host_tif, qr_png, work_dir):
    """Embed ``scheme``'s watermark; returns ``(stego_path, wm_meta_path)``."""
    from PIL import Image

    if scheme == "lsb":
        from algorithm.raster_reversible_watermark import embed_reversible as embed
    elif scheme == "dwt":
        from algorithm.raster_dwt_watermark import embed_dwt as embed
    elif scheme == "histogram":
        from algorithm.raster_histogram_watermark import embed_histogram as embed
    elif scheme == "blind":
        from algorithm.raster_blind_watermark import embed_blind as embed
    else:
        raise ValueError(f"unknown raster scheme: {scheme!r}")
    with Image.open(qr_png) as wm_img:
        result = embed(host_tif, wm_img, output_dir=os.path.join(work_dir, f"embed_{scheme}"), prefix=f"r_{scheme}")
    return result["stego_path"], result["wm_meta_path"]


def _extract_watermark(scheme, attacked_path, wm_meta_path, out_png):
    """Run the scheme's extractor; returns the rebuilt watermark PNG path."""
    if scheme == "lsb":
        from algorithm.raster_reversible_watermark import decode_reversible as extract
    elif scheme == "dwt":
        from algorithm.raster_dwt_watermark import extract_dwt as extract
    elif scheme == "histogram":
        from algorithm.raster_histogram_watermark import extract_histogram as extract
    elif scheme == "blind":
        from algorithm.raster_blind_watermark import extract_blind as extract
    else:
        raise ValueError(f"unknown raster scheme: {scheme!r}")
    return extract(attacked_path, wm_meta_path, out_png)


def _run_scheme(scheme, host_tif, host_profile, qr_png, attacks, payload_text, work_dir):
    from algorithm.quality_metrics import compute_ber, compute_nc
    from resource.watermark_utils import decode_qr_from_image

    scheme_dir = os.path.join(work_dir, f"scheme_{scheme}")
    os.makedirs(scheme_dir, exist_ok=True)

    try:
        stego_path, wm_meta_path = _embed_stego(scheme, host_tif, qr_png, scheme_dir)
        wm_w, wm_h = _watermark_dims(wm_meta_path)
        gt_bits = _image_bits(qr_png, size=(wm_w, wm_h))
    except Exception as e:
        logging.exception("raster robustness matrix: embed failed for scheme %s", scheme)
        error = f"embed failed: {e}"[:255]
        return [_row(scheme, attack, dict(RASTER_ATTACK_DEFAULTS[attack]), False, error=error) for attack in attacks]

    rows = []
    for attack in attacks:
        params = dict(RASTER_ATTACK_DEFAULTS[attack])
        started = time.perf_counter()
        try:
            if attack == "none":
                attacked_path = stego_path
            else:
                attacked_path = _ATTACK_FUNCTIONS[attack](
                    stego_path,
                    output_path=os.path.join(scheme_dir, f"attacked_{scheme}_{attack}.tif"),
                    base_profile=host_profile,
                    **params,
                )
            wm_png = _extract_watermark(
                scheme, attacked_path, wm_meta_path, os.path.join(scheme_dir, f"extract_{scheme}_{attack}.png")
            )
            text = decode_qr_from_image(wm_png)
            duration_ms = int((time.perf_counter() - started) * 1000)
            if text is None:
                rows.append(_row(scheme, attack, params, False, duration_ms=duration_ms))
                continue
            ext_bits = _image_bits(wm_png)
            nc = compute_nc(gt_bits, ext_bits)
            ber = compute_ber(gt_bits, ext_bits)
            rows.append(_row(scheme, attack, params, text == payload_text, nc=nc, ber=ber, duration_ms=duration_ms))
        except Exception as e:
            logging.exception("raster robustness matrix: cell failed scheme=%s attack=%s", scheme, attack)
            duration_ms = int((time.perf_counter() - started) * 1000)
            rows.append(_row(scheme, attack, params, False, duration_ms=duration_ms, error=str(e)[:255]))
    return rows


def run_raster_matrix(host_tif, schemes=None, attacks=None, payload_qr_png=None, work_dir=None):
    """Run the full (scheme x attack) raster robustness matrix; returns row dicts.

    The payload QR is rendered by the caller (``render_raster_payload_qr`` —
    the delivery renderer at a size the blind scheme can carry); the text it
    carries is read back from the PNG itself and serves as the ground truth
    every cell's decoded text is compared against. For each scheme the
    watermark is embedded once into ``host_tif``; the no-attack baseline is
    measured first, then each requested attack runs on its own copy of the
    stego raster.

    Returns one row dict per (scheme, attack) with exactly the vector engine's
    keys: ``{scheme, attack, attack_params, nc, ber, decode_success,
    duration_ms, error}``. Nothing is written to any database here.
    """
    if not payload_qr_png:
        raise ValueError("payload_qr_png is required")
    if work_dir is None:
        raise ValueError("work_dir is required")
    schemes = list(schemes or RASTER_SCHEMES)
    attacks = _ordered_attacks(list(attacks or RASTER_ATTACKS))

    from resource.watermark_utils import decode_qr_from_image

    payload_text = decode_qr_from_image(payload_qr_png)
    if payload_text is None:
        raise ValueError(f"payload QR is not decodable: {payload_qr_png}")

    os.makedirs(work_dir, exist_ok=True)
    _host_arr, host_profile = _read_rgb_uint8(host_tif)

    rows = []
    for scheme in schemes:
        rows.extend(_run_scheme(scheme, host_tif, host_profile, payload_qr_png, attacks, payload_text, work_dir))
    return rows
