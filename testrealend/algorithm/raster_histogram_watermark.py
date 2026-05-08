"""Histogram Shifting reversible watermarking (Ni et al. 2006).

An alternative to LSB-based reversible watermarking that offers higher
capacity for images with concentrated pixel-value distributions (many
pixels sharing a single intensity value).

Algorithm overview
------------------
* **Embed**: find the peak (most frequent pixel value) and a zero point
  (a value with zero or minimal frequency).  Shift all pixels between
  peak and zero point away from peak by one, creating a gap.  Embed
  watermark bits by moving selected peak-pixels into the gap.
* **Extract**: identify peak-pixels in the stego image (they now occupy
  two adjacent values) and read the bits back.
* **Recover**: reverse the shift to losslessly restore the original image.
"""
import json
import logging
import os
from datetime import datetime

import numpy as np
from PIL import Image

from algorithm.quality_metrics import compute_psnr, capacity_report
from algorithm.raster_geotiff_utils import read_geotiff, save_geotiff


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _find_peak_and_zero(hist: np.ndarray):
    """Find the peak point and zero point for histogram shifting.

    Returns
    -------
    peak : int
        Pixel value with maximum frequency.
    peak_count : int
        Frequency of the peak value.
    zero_point : int
        Target value for the shift boundary.
    direction : str
        ``"up"`` when shifting values above peak upward, ``"down"`` when
        shifting values below peak downward.
    """
    peak = int(np.argmax(hist))
    peak_count = int(hist[peak])

    # 1. Search above peak for a true zero-frequency bin
    for v in range(peak + 1, 256):
        if hist[v] == 0:
            return peak, peak_count, v, "up"

    # 2. Search below peak for a true zero-frequency bin
    for v in range(peak - 1, -1, -1):
        if hist[v] == 0:
            return peak, peak_count, v, "down"

    # 3. No true zero point -- use the least frequent value (boundary).
    #    This creates a "soft" zero point whose original pixels must be
    #    tracked in metadata to guarantee perfect reversibility.
    if peak < 255:
        above = np.arange(peak + 1, 256)
        return peak, peak_count, int(above[np.argmin(hist[above])]), "up"

    # peak == 255 -- search below
    below = np.arange(0, peak)
    return peak, peak_count, int(below[np.argmin(hist[below])]), "down"


# ── public API ────────────────────────────────────────────────────────────

def embed_histogram(host_path: str, watermark_img: Image.Image,
                    output_dir: str, prefix: str) -> dict:
    """Embed a binary watermark into *host_path* using Histogram Shifting.

    Parameters
    ----------
    host_path : str
        Path to the host raster image.
    watermark_img : PIL.Image.Image
        Binary watermark image (e.g. a QR code).
    output_dir : str
        Directory for output files.
    prefix : str
        Filename prefix for generated files.

    Returns
    -------
    dict
        Keys: ``stego_path``, ``wm_meta_path``, ``psnr``, ``capacity``
        (number of pixels at the peak value, i.e. the embedding budget).
    """
    _ensure_dir(output_dir)

    # Load host as RGB and work on channel 0 (consistent with the existing
    # LSB reversible-watermark module).
    host_arr_raw, raster_profile = read_geotiff(host_path)
    # Ensure RGB layout
    if host_arr_raw.ndim == 2:
        host_arr_raw = np.stack([host_arr_raw] * 3, axis=-1)
    elif host_arr_raw.shape[2] == 1:
        host_arr_raw = np.concatenate([host_arr_raw] * 3, axis=-1)
    elif host_arr_raw.shape[2] > 3:
        host_arr_raw = host_arr_raw[:, :, :3]
    host_arr = host_arr_raw.astype(np.int32)
    h, w, _ = host_arr.shape
    is_gt = raster_profile.get("geotiff", False)
    if is_gt:
        logging.info("Histogram embed: input is a GeoTIFF — CRS/transform will be preserved: %s", host_path)

    channel = host_arr[:, :, 0].ravel().copy()
    original_channel = channel.copy()

    # ── histogram analysis ──────────────────────────────────────────────
    hist, _ = np.histogram(channel, bins=256, range=(0, 255))
    peak, peak_count, zero_point, direction = _find_peak_and_zero(hist)

    logging.info("Histogram shifting: peak=%d (count=%d), zero_point=%d, "
                 "direction=%s", peak, peak_count, zero_point, direction)

    # Track whether the zero point is "soft" (has non-zero frequency).
    # When soft, its original pixel positions must be saved to guarantee
    # perfect reversibility during recovery.
    soft_zero = bool(hist[zero_point] > 0)
    zero_point_positions = np.array([], dtype=np.int64)
    if soft_zero:
        zero_point_positions = np.where(channel == zero_point)[0].astype(
            np.int64
        )

    # ── convert watermark to bit array ──────────────────────────────────
    wm_arr = np.array(
        watermark_img.convert("L").resize((w, h), Image.Resampling.NEAREST),
        dtype=np.uint8,
    )
    wm_bits = (wm_arr.ravel() > 127).astype(np.int32)
    bit_count = int(wm_bits.size)

    # ── capacity check ──────────────────────────────────────────────────
    if bit_count > peak_count:
        cap = capacity_report(peak_count, bit_count, n=1)
        raise ValueError(
            f"Insufficient histogram capacity: need {bit_count} bits but "
            f"peak bin has only {peak_count} pixels. Capacity report: {cap}"
        )

    # ── shift + embed ───────────────────────────────────────────────────
    peak_positions = np.where(original_channel == peak)[0]

    if direction == "up":
        # Shift pixels in (peak, zero_point) upward by 1
        mask = (channel > peak) & (channel < zero_point)
        channel[mask] += 1
        # Embed: peak stays peak (bit 0), peak -> peak+1 (bit 1)
        embed_idx = peak_positions[:bit_count][wm_bits == 1]
        channel[embed_idx] += 1
    else:  # down
        # Shift pixels in (zero_point, peak) downward by 1
        mask = (channel > zero_point) & (channel < peak)
        channel[mask] -= 1
        # Embed: peak stays peak (bit 0), peak -> peak-1 (bit 1)
        embed_idx = peak_positions[:bit_count][wm_bits == 1]
        channel[embed_idx] -= 1

    # ── reconstruct and save stego image ────────────────────────────────
    stego_arr = host_arr.copy()
    stego_arr[:, :, 0] = channel.reshape(h, w)
    stego_arr = np.clip(stego_arr, 0, 255).astype(np.uint8)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stego_filename = f"{prefix}_{timestamp}_stego{'_geotiff' if is_gt else ''}.{'tif' if is_gt else 'png'}"
    stego_path = os.path.join(output_dir, stego_filename)
    wm_meta_path = os.path.join(
        output_dir, f"{prefix}_{timestamp}_wm_meta.json"
    )

    # --- Save stego image (GeoTIFF if input was GeoTIFF) ---
    if is_gt:
        stego_profile = {k: v for k, v in raster_profile.items() if k != "geotiff"}
        stego_profile.update({"driver": "GTiff", "height": h, "width": w, "count": 3, "dtype": "uint8"})
        save_geotiff(stego_arr, stego_profile, stego_path)
    else:
        Image.fromarray(stego_arr, mode="RGB").save(stego_path, format="PNG")

    # ── save metadata ───────────────────────────────────────────────────
    # Serialize GeoTIFF profile for recovery
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

    meta = {
        "algorithm": "histogram_shifting",
        "peak": peak,
        "peak_count": peak_count,
        "zero_point": zero_point,
        "direction": direction,
        "soft_zero": soft_zero,
        "zero_point_positions": (
            zero_point_positions.tolist() if soft_zero else []
        ),
        "shape": {"height": int(h), "width": int(w), "channels": 3},
        "watermark": {
            "height": int(wm_arr.shape[0]),
            "width": int(wm_arr.shape[1]),
            "bit_count": bit_count,
        },
        "geotiff": is_gt,
        "geotiff_profile": geo_profile_for_meta,
    }
    with open(wm_meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)

    # ── quality metrics ─────────────────────────────────────────────────
    psnr_value = compute_psnr(host_arr.astype(np.uint8), stego_arr)
    cap_report = capacity_report(peak_count, bit_count, n=1)
    logging.info("Histogram embed PSNR=%.2f dB, capacity report: %s",
                 psnr_value, cap_report)

    return {
        "stego_path": stego_path,
        "wm_meta_path": wm_meta_path,
        "psnr": psnr_value,
        "capacity": peak_count,
    }


def extract_histogram(stego_path: str, wm_meta_path: str,
                      output_path: str) -> str:
    """Extract the watermark from a histogram-shifted stego image.

    Parameters
    ----------
    stego_path : str
        Path to the stego image.
    wm_meta_path : str
        Path to the JSON metadata produced during embedding.
    output_path : str
        Where to save the recovered watermark image.

    Returns
    -------
    str
        The *output_path*.
    """
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    peak = int(meta["peak"])
    zero_point = int(meta["zero_point"])
    direction = meta["direction"]
    soft_zero = bool(meta.get("soft_zero", False))
    wm_h = int(meta["watermark"]["height"])
    wm_w = int(meta["watermark"]["width"])
    bit_count = int(meta["watermark"]["bit_count"])

    stego_arr_raw, _ = read_geotiff(stego_path)
    if stego_arr_raw.ndim == 2:
        stego_arr_raw = np.stack([stego_arr_raw] * 3, axis=-1)
    elif stego_arr_raw.shape[2] == 1:
        stego_arr_raw = np.concatenate([stego_arr_raw] * 3, axis=-1)
    elif stego_arr_raw.shape[2] > 3:
        stego_arr_raw = stego_arr_raw[:, :, :3]
    stego_arr = stego_arr_raw.astype(np.int32)

    flat = stego_arr[:, :, 0].ravel()

    # In the stego image, pixels that were originally at *peak* now sit at
    # two adjacent values (peak for bit 0, peak+/-1 for bit 1).  All other
    # modified pixels have been shifted further away, so there is no
    # collision -- except when the zero point is adjacent to the peak and
    # is a "soft" zero point (its original pixels share the same value as
    # the embedded bit-1 pixels).
    if direction == "up":
        candidates_mask = (flat == peak) | (flat == peak + 1)
    else:
        candidates_mask = (flat == peak) | (flat == peak - 1)

    # Exclude soft-zero-point positions that would collide with bit-1 pixels
    if soft_zero:
        zp_pos = np.array(meta.get("zero_point_positions", []), dtype=np.int64)
        if zp_pos.size > 0:
            candidates_mask[zp_pos] = False

    candidates = np.where(candidates_mask)[0]
    target_val = peak + 1 if direction == "up" else peak - 1
    bits = (flat[candidates[:bit_count]] == target_val).astype(np.uint8)

    # Reconstruct watermark image
    wm = (bits.reshape(wm_h, wm_w) * 255).astype(np.uint8)
    Image.fromarray(wm, mode="L").save(output_path, format="PNG")
    return output_path


def recover_histogram(stego_path: str, wm_meta_path: str,
                      output_path: str) -> str:
    """Losslessly recover the original host image from the stego image.

    Parameters
    ----------
    stego_path : str
        Path to the stego image.
    wm_meta_path : str
        Path to the JSON metadata produced during embedding.
    output_path : str
        Where to save the recovered host image.

    Returns
    -------
    str
        The *output_path*.
    """
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    peak = int(meta["peak"])
    zero_point = int(meta["zero_point"])
    direction = meta["direction"]
    soft_zero = bool(meta.get("soft_zero", False))
    h = int(meta["shape"]["height"])
    w = int(meta["shape"]["width"])

    stego_arr_raw, _ = read_geotiff(stego_path)
    if stego_arr_raw.ndim == 2:
        stego_arr_raw = np.stack([stego_arr_raw] * 3, axis=-1)
    elif stego_arr_raw.shape[2] == 1:
        stego_arr_raw = np.concatenate([stego_arr_raw] * 3, axis=-1)
    elif stego_arr_raw.shape[2] > 3:
        stego_arr_raw = stego_arr_raw[:, :, :3]
    stego_arr = stego_arr_raw.astype(np.int32)
    flat = stego_arr[:, :, 0].ravel().copy()

    # Reverse the histogram shift.  All modified pixels (embedded peak
    # pixels and shifted non-peak pixels) now occupy the range between
    # peak and zero_point inclusive.  Move them back by one step.
    if direction == "up":
        mask = (flat > peak) & (flat <= zero_point)
        flat[mask] -= 1
    else:  # down
        mask = (flat >= zero_point) & (flat < peak)
        flat[mask] += 1

    # If the zero point was "soft" (non-zero frequency), its original
    # pixels were inadvertently included in the reverse shift.  Restore
    # them from the saved positions.
    if soft_zero:
        zp_pos = np.array(meta.get("zero_point_positions", []), dtype=np.int64)
        if zp_pos.size > 0:
            flat[zp_pos] = zero_point

    # Reconstruct and save
    recovered = stego_arr.copy()
    recovered[:, :, 0] = flat.reshape(h, w)
    recovered = np.clip(recovered, 0, 255).astype(np.uint8)

    # --- Save recovered image (GeoTIFF if original was GeoTIFF) ---
    is_gt = meta.get("geotiff", False)
    if is_gt:
        geo_profile = meta.get("geotiff_profile", {})
        if "crs" in geo_profile:
            try:
                import rasterio.crs
                geo_profile["crs"] = rasterio.crs.CRS.from_wkt(geo_profile["crs"])
            except Exception:
                pass
        if "transform" in geo_profile and isinstance(geo_profile["transform"], list):
            try:
                import affine
                geo_profile["transform"] = affine.Affine(*geo_profile["transform"])
            except Exception:
                pass
        geo_profile.update({"driver": "GTiff", "height": h, "width": w, "count": 3, "dtype": "uint8"})
        save_geotiff(recovered.astype(np.uint8), geo_profile, output_path)
    else:
        Image.fromarray(recovered, mode="RGB").save(output_path, format="PNG")
    return output_path
