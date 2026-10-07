"""IW-DCT watermarking for raster images — a self-contained port of the
invisible-watermark ``dwtDct`` design (ShieldMnt/invisible-watermark, MIT,
https://github.com/ShieldMnt/invisible-watermark), fifth raster algorithm
alongside the reversible-LSB, DWT+QIM, histogram-shifting and blind modules.

Design (spec: taskbook feat_lab_iw, Track B)
---------------------------------------------
* **DWT**: one level of the Haar wavelet (``pywt.dwt2``) over the Y (luma)
  channel; the watermark lives in the LL subband.
* **Blocks**: the LL subband is cut into non-overlapping ``BLOCK x BLOCK``
  blocks. ``BLOCK = 4`` — the published iw implementations (0.1.5 / 0.2.0 /
  main) all construct their embedder with ``block=4``; a 4x4 LL block spans an
  8x8 host-pixel footprint, giving ``(H//8) * (W//8)`` embeddable bits (4,096
  on the lab's 512x512 host — the same budget as the blind scheme).
* **Per block**: opencv DCT (``cv2.dct``) of the block; one bit is carried by
  the order of a *fixed mid-frequency coefficient pair* ``(c1, c2)``
  (row-major indices (1,2) and (2,1) of the 4x4 DCT). bit=1 enforces
  ``c1 - c2 >= +MARGIN``, bit=0 enforces ``c1 - c2 <= -MARGIN``; blocks that
  already satisfy the bound are left untouched, otherwise both coefficients
  are moved symmetrically around their mean. Extraction reads the same pair
  back and compares (``c1 > c2`` -> 1), so the no-attack roundtrip is exact
  by construction (MARGIN is an order of magnitude above the +/-1 noise
  introduced by the uint8 pixel round-trip).
  Deviation note (honest): the *published* iw ``dwtDct`` (``maxDct.py``)
  quantizes the block's single max-energy LL coefficient (QIM, scale=36,
  no DCT transform in the executed path, U channel) rather than comparing a
  fixed DCT-coefficient pair; this module implements the mechanism specified
  by the taskbook (fixed mid-frequency pair comparison on the LL block DCT)
  while keeping iw's block=4 geometry and its cyclic payload structure.
* **Payload**: the QR bitmap is embedded at its natural size (no resize —
  same contract as the blind module) and repeated cyclically across the block
  grid (``block n -> bit n % bit_count``) with per-bit majority voting at
  extraction — exactly the ``num % wmLen`` design of the iw embedder.
  Capacity is one bit per 4x4 LL block; an oversized payload surfaces as
  ``Insufficient IW-DCT capacity`` (mapped to HTTP 400 by the raster
  endpoints, same "Insufficient" prefix convention as the siblings).
  On the lab's 512x512 host (4,096 blocks) the standard 57x57 px payload
  (3,249 bits) fits at ~79% utilization; the first 847 bits carry two votes.
* **Host**: the Y channel is processed as float (RGB -> YUV via cv2), the
  image is cropped to a multiple of 8 pixels (BLOCK x 2) for the grid and
  the trailing edge is left untouched. GeoTIFF hosts keep CRS/transform via
  the same rasterio write-back pattern as the blind/histogram modules.

Parameters (all module constants, recorded in the meta JSON):
* ``BLOCK = 4`` (iw default), DWT level 1 (Haar), channel Y,
* coefficient pair (1,2)/(2,1) — the lowest mid-frequency 4x4 DCT pair
  (lower frequency = more robust than diagonal high-frequency choices),
* ``EMBED_MARGIN = 26`` — calibrated so that the no-attack roundtrip is
  exact on uint8 storage while keeping PSNR in the high-30s dB and giving the
  JPEG q70 / noise sigma=5 cells a real chance (measured in the lab matrix).

Determinism: the embed is a pure function of (host, payload, constants) —
no RNG, no multiprocessing, no shared state between requests.
"""

import json
import logging
import os
from datetime import datetime

import cv2
import numpy as np
import pywt
from PIL import Image

from algorithm.quality_metrics import capacity_report, compute_psnr
from algorithm.raster_geotiff_utils import read_geotiff, save_geotiff

# Same convention as the other raster modules.
WM_THRESHOLD = 127

# ── algorithm constants (recorded in the meta JSON, overridable at extract) ──
BLOCK = 4
DWT_LEVEL = 1
DWT_WAVELET = "haar"
CHANNEL = "Y"
# Fixed mid-frequency coefficient pair of the 4x4 DCT (row, col); row-major
# indices 6 and 9 of the flattened block.
DCT_PAIR = ((1, 2), (2, 1))
EMBED_MARGIN = 26.0


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _read_rgb_array(path: str) -> np.ndarray:
    """Load *path* as an (H, W, 3) uint8 RGB array (sibling convention).

    rasterio for GeoTIFFs, PIL otherwise; multi-band rasters reduce to their
    first three bands; non-8-bit samples are clipped into 0-255.
    """
    arr, _profile = read_geotiff(path)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    elif arr.shape[2] == 1:
        arr = np.concatenate([arr] * 3, axis=-1)
    elif arr.shape[2] > 3:
        arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        arr = np.clip(np.nan_to_num(arr, nan=0.0), 0, 255).astype(np.uint8)
    return arr


def _to_y_channel(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 -> Y (luma) channel as float64 (cv2 BT.601 conventions)."""
    yuv = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2YUV)
    return yuv[:, :, 0].astype(np.float64)


def _grid_shape(height: int, width: int):
    """(crop_h, crop_w, block_rows, block_cols) for an HxW host.

    The image is cropped to a multiple of ``2 * BLOCK`` pixels (each block
    spans BLOCK LL coefficients = 2*BLOCK host pixels), then the LL subband
    (ceil-halved by pywt) is cut into BLOCK x BLOCK blocks.
    """
    crop_h = (height // (2 * BLOCK)) * (2 * BLOCK)
    crop_w = (width // (2 * BLOCK)) * (2 * BLOCK)
    ll_h = crop_h // 2
    ll_w = crop_w // 2
    return crop_h, crop_w, ll_h // BLOCK, ll_w // BLOCK


def _to_wm_bits(watermark_img: Image.Image) -> np.ndarray:
    """QR bitmap -> flat boolean bit array, embedded at its natural size.

    Deliberately NOT resized (blind-module convention): an oversized payload
    is an honest capacity error, not silently shrunk. The payload is repeated
    cyclically across the block grid, so a 1-D array keeps the flat raster
    order unambiguous.
    """
    wm_arr = np.array(watermark_img.convert("L"), dtype=np.uint8)
    return wm_arr.reshape(-1) > WM_THRESHOLD


def embed_iw_dct(
    host_path: str,
    watermark_img: Image.Image,
    output_dir: str,
    prefix: str,
) -> dict:
    """Embed a watermark bitmap into a raster with the IW-DCT scheme.

    Args:
        host_path: Path to the host image file (GeoTIFF metadata is preserved).
        watermark_img: PIL Image (the QR bitmap) embedded at its natural size.
        output_dir: Directory for output files.
        prefix: Filename prefix for output files.

    Returns:
        Dict with keys: stego_path, wm_meta_path, psnr, capacity_report,
        bit_count, blocks.

    Raises:
        ValueError: "Insufficient IW-DCT capacity: ..." when the payload does
            not fit the host's LL block grid (one bit per 4x4 LL block =
            8x8 host pixels).
    """
    _ensure_dir(output_dir)

    host_rgb = _read_rgb_array(host_path)
    h, w = host_rgb.shape[:2]

    wm_gray = watermark_img.convert("L")
    wm_w, wm_h = wm_gray.size
    wm_bits = _to_wm_bits(wm_gray)
    bit_count = int(wm_bits.size)
    if bit_count == 0:
        raise ValueError("Insufficient IW-DCT capacity: the watermark bitmap is empty")

    crop_h, crop_w, block_rows, block_cols = _grid_shape(h, w)
    blocks = block_rows * block_cols
    if bit_count > blocks:
        cap = capacity_report(blocks, bit_count, n=1)
        needed_side = 2 * BLOCK * int(np.ceil(np.sqrt(bit_count)))
        raise ValueError(
            f"Insufficient IW-DCT capacity: need {bit_count} blocks "
            f"(watermark {wm_w}x{wm_h} = {bit_count} bits) but the host image "
            f"({w}x{h}) provides only {blocks} embeddable blocks "
            f"(one per {BLOCK}x{BLOCK} DCT block of the level-{DWT_LEVEL} LL "
            f"subband = {2 * BLOCK}x{2 * BLOCK} host pixels). Capacity report: {cap}"
            f"（IW-DCT 容量 = 宿主宽×高/{2 * BLOCK * 2 * BLOCK}；"
            f"该载荷约需 ≥{needed_side}×{needed_side} 的宿主）"
        )

    # ── forward DWT on the cropped Y channel ────────────────────────────
    y = _to_y_channel(host_rgb)
    y_crop = y[:crop_h, :crop_w]
    ll, highs = pywt.dwt2(y_crop, DWT_WAVELET)  # single level (DWT_LEVEL = 1)
    ll = np.asarray(ll, dtype=np.float64).copy()

    # ── embed: bit n % bit_count into block n, margin-enforced pair order ──
    (r1, c1), (r2, c2) = DCT_PAIR
    changed_blocks = 0
    for row in range(block_rows):
        for col in range(block_cols):
            n = row * block_cols + col
            bit = bool(wm_bits[n % bit_count])
            block = ll[row * BLOCK : (row + 1) * BLOCK, col * BLOCK : (col + 1) * BLOCK]
            dct = cv2.dct(block)
            v1 = float(dct[r1, c1])
            v2 = float(dct[r2, c2])
            delta = v1 - v2
            if bit:
                if delta >= EMBED_MARGIN:
                    continue
                shift = (EMBED_MARGIN - delta) / 2.0
            else:
                if delta <= -EMBED_MARGIN:
                    continue
                shift = (-EMBED_MARGIN - delta) / 2.0
            dct[r1, c1] = np.float64(v1 + shift)
            dct[r2, c2] = np.float64(v2 - shift)
            ll[row * BLOCK : (row + 1) * BLOCK, col * BLOCK : (col + 1) * BLOCK] = cv2.idct(dct)
            changed_blocks += 1

    # ── inverse DWT, write the Y channel back ───────────────────────────
    y_out = pywt.idwt2((ll, highs), DWT_WAVELET)[:crop_h, :crop_w]
    y_new = y.copy()
    y_new[:crop_h, :crop_w] = y_out
    yuv = cv2.cvtColor(host_rgb.astype(np.float32), cv2.COLOR_RGB2YUV)
    yuv[:, :, 0] = y_new
    stego_rgb = np.clip(np.round(cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)), 0, 255).astype(np.uint8)

    # ── GeoTIFF-aware output (same write-back pattern as the blind module) ──
    _host_arr, raster_profile = read_geotiff(host_path)
    is_gt = raster_profile.get("geotiff", False)
    if is_gt:
        logging.info("IW-DCT embed: input is a GeoTIFF — CRS/transform will be preserved: %s", host_path)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stego_filename = f"{prefix}_{timestamp}_iwdct_stego{'_geotiff' if is_gt else ''}.{'tif' if is_gt else 'png'}"
    stego_path = os.path.join(output_dir, stego_filename)
    wm_meta_path = os.path.join(output_dir, f"{prefix}_{timestamp}_iwdct_wm_meta.json")

    if is_gt:
        stego_profile = dict(raster_profile)
        stego_profile.update({"driver": "GTiff", "height": h, "width": w, "count": 3, "dtype": "uint8"})
        # Trust the returned path: save_geotiff falls back to PNG and reports
        # that path on failure, so callers never record a missing file.
        stego_path = save_geotiff(stego_rgb, stego_profile, stego_path)
    else:
        Image.fromarray(stego_rgb, mode="RGB").save(stego_path, format="PNG")
    if not os.path.isfile(stego_path):
        raise RuntimeError(f"stego image was not written to disk: {stego_path}")

    # ── serialize the GeoTIFF profile for the meta JSON ─────────────────
    geo_profile_for_meta = None
    if is_gt:
        geo_profile_for_meta = {}
        for k, v in raster_profile.items():
            if k == "geotiff":
                continue
            if k == "crs":
                try:
                    geo_profile_for_meta["crs"] = v.to_wkt() if hasattr(v, "to_wkt") else str(v)
                except Exception:
                    geo_profile_for_meta["crs"] = str(v)
            elif k == "transform":
                geo_profile_for_meta["transform"] = list(v)[:6] if hasattr(v, "__iter__") else str(v)
            elif isinstance(v, (str, int, float, bool, type(None))):
                geo_profile_for_meta[k] = v
            else:
                geo_profile_for_meta[k] = str(v)

    utility = round(bit_count / max(blocks, 1) * 100, 2)
    meta = {
        "algorithm": "iw_dct",
        "block_size": BLOCK,
        "dwt": {"wavelet": DWT_WAVELET, "level": DWT_LEVEL},
        "channel": CHANNEL,
        "dct_pair": [list(DCT_PAIR[0]), list(DCT_PAIR[1])],
        "embed_margin": EMBED_MARGIN,
        "shape": {"height": int(h), "width": int(w), "channels": 3},
        "watermark": {"height": int(wm_h), "width": int(wm_w), "bit_count": bit_count},
        "capacity": {
            "block_num": int(blocks),
            "utilization_percent": utility,
            "voting": "cyclic repetition (block n -> bit n % bit_count), per-bit majority",
        },
        "geotiff": is_gt,
        "geotiff_profile": geo_profile_for_meta,
    }
    with open(wm_meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)

    psnr_value = compute_psnr(host_rgb, stego_rgb)
    cap_report = capacity_report(blocks, bit_count, n=1)
    logging.info(
        "IW-DCT embed PSNR=%.2f dB, %d bits / %d blocks (utilization %.2f%%, %d blocks adjusted), capacity report: %s",
        psnr_value,
        bit_count,
        blocks,
        utility,
        changed_blocks,
        cap_report,
    )

    return {
        "stego_path": stego_path,
        "wm_meta_path": wm_meta_path,
        "psnr": psnr_value,
        "capacity_report": cap_report,
        "bit_count": bit_count,
        "blocks": int(blocks),
    }


def extract_iw_dct(stego_path: str, wm_meta_path: str, output_path: str) -> str:
    """Blind-extract the watermark bitmap from an IW-DCT stego image.

    Needs only the meta JSON (payload dimensions) — no host, no change map.
    Cyclic repetition means every payload bit is read from one or more blocks;
    a stego whose geometry shrank below one block per bit (e.g. a 0.5x resize
    or an aggressive crop) is rejected honestly instead of returning garbage.
    """
    with open(wm_meta_path, encoding="utf-8") as fp:
        meta = json.load(fp)

    wm_h = int(meta["watermark"]["height"])
    wm_w = int(meta["watermark"]["width"])
    bit_count = int(meta["watermark"]["bit_count"])
    block = int(meta.get("block_size", BLOCK))
    if block != BLOCK:  # pragma: no cover - forward-compat guard
        raise ValueError(f"IW-DCT meta carries unsupported block_size={block}")
    pair = meta.get("dct_pair") or [list(DCT_PAIR[0]), list(DCT_PAIR[1])]
    (r1, c1), (r2, c2) = (int(pair[0][0]), int(pair[0][1])), (int(pair[1][0]), int(pair[1][1]))

    stego_rgb = _read_rgb_array(stego_path)
    h, w = stego_rgb.shape[:2]
    crop_h, crop_w, block_rows, block_cols = _grid_shape(h, w)
    blocks = block_rows * block_cols
    if blocks < bit_count:
        raise ValueError(
            f"stego raster too small for IW-DCT extraction: needs >= {bit_count} blocks "
            f"(watermark {wm_w}x{wm_h}) but the attacked image ({w}x{h}) provides only {blocks} "
            f"({BLOCK}x{BLOCK} LL blocks) — geometry changed beyond this scheme's blind reach"
        )

    y = _to_y_channel(stego_rgb)
    ll = np.asarray(pywt.dwt2(y[:crop_h, :crop_w], DWT_WAVELET)[0], dtype=np.float64)

    votes = np.zeros(bit_count, dtype=np.float64)
    counts = np.zeros(bit_count, dtype=np.int64)
    for row in range(block_rows):
        for col in range(block_cols):
            n = row * block_cols + col
            idx = n % bit_count
            dct = cv2.dct(ll[row * BLOCK : (row + 1) * BLOCK, col * BLOCK : (col + 1) * BLOCK])
            if float(dct[r1, c1]) > float(dct[r2, c2]):
                votes[idx] += 1.0
            counts[idx] += 1

    bits = (votes / counts > 0.5).astype(np.uint8)
    wm_img = (bits.reshape(wm_h, wm_w) * 255).astype(np.uint8)
    Image.fromarray(wm_img, mode="L").save(output_path, format="PNG")

    logging.info(
        "IW-DCT extract: recovered %dx%d watermark (%d bits) from %d blocks (%d..%d votes/bit) to %s",
        wm_w,
        wm_h,
        bit_count,
        blocks,
        int(counts.min()),
        int(counts.max()),
        output_path,
    )
    return output_path
