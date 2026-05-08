import json
import logging
import os
from datetime import datetime

import numpy as np
from PIL import Image

from algorithm.quality_metrics import compute_psnr, capacity_report
from algorithm.raster_geotiff_utils import is_geotiff, read_geotiff, save_geotiff


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _to_binary_watermark(watermark_img: Image.Image, width: int, height: int, threshold: int = 127) -> np.ndarray:
    wm = watermark_img.convert("L").resize((width, height), Image.Resampling.NEAREST)
    return (np.array(wm, dtype=np.uint8) > threshold).astype(np.uint8)


def embed_reversible(host_path: str, watermark_img: Image.Image, output_dir: str, prefix: str,
                     min_wm_size: int = 64, max_wm_size: int = 512, threshold: int = 127) -> dict:
    _ensure_dir(output_dir)

    # --- Read host image (GeoTIFF-aware) ---
    host_arr, raster_profile = read_geotiff(host_path)
    # Ensure RGB layout for the embedding logic
    if host_arr.ndim == 2:
        host_arr = np.stack([host_arr] * 3, axis=-1)
    elif host_arr.shape[2] == 1:
        host_arr = np.concatenate([host_arr] * 3, axis=-1)
    elif host_arr.shape[2] > 3:
        host_arr = host_arr[:, :, :3]
    host_arr = host_arr.astype(np.uint8)

    h, w, _ = host_arr.shape
    is_gt = raster_profile.get("geotiff", False)
    if is_gt:
        logging.info("Input is a GeoTIFF — CRS and transform will be preserved: %s", host_path)

    # Clamp watermark dimensions between min_wm_size and max_wm_size, also bounded by host image size
    wm_w = max(min_wm_size, min(max_wm_size, w))
    wm_h = max(min_wm_size, min(max_wm_size, h))
    wm_bits_2d = _to_binary_watermark(watermark_img, wm_w, wm_h, threshold)
    wm_bits = wm_bits_2d.reshape(-1)
    channel = host_arr[:, :, 0].reshape(-1).copy()
    bit_count = int(wm_bits.size)
    if bit_count > channel.size:
        cap = capacity_report(channel.size, bit_count, n=1)
        raise ValueError(
            f"Insufficient raster capacity: need {bit_count} bits but carrier has only {channel.size} pixels. "
            f"Capacity report: {cap}"
        )
    original_values = channel[:bit_count].copy()
    embedded_values = (original_values & 0xFE) | wm_bits
    changed_mask = original_values != embedded_values
    changed_idx = np.nonzero(changed_mask)[0].astype(np.int64)
    changed_vals = original_values[changed_mask].astype(np.uint8)
    channel[:bit_count] = embedded_values
    stego_arr = host_arr.copy()
    stego_arr[:, :, 0] = channel.reshape(h, w)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stego_filename = f"{prefix}_{timestamp}_stego{'_geotiff' if is_gt else ''}.{'tif' if is_gt else 'png'}"
    stego_path = os.path.join(output_dir, stego_filename)
    wm_map_path = os.path.join(output_dir, f"{prefix}_{timestamp}_wm_map.npz")
    wm_meta_path = os.path.join(output_dir, f"{prefix}_{timestamp}_wm_meta.json")

    # --- Save stego image (GeoTIFF if input was GeoTIFF) ---
    if is_gt:
        # Build a write profile from the original rasterio profile
        stego_profile = {k: v for k, v in raster_profile.items() if k != "geotiff"}
        stego_profile.update({"driver": "GTiff", "height": h, "width": w, "count": 3, "dtype": "uint8"})
        save_geotiff(stego_arr, stego_profile, stego_path)
    else:
        Image.fromarray(stego_arr, mode="RGB").save(stego_path, format="PNG")

    # --- Save change map & metadata ---
    # Include the original geotiff profile so recovery can restore it
    geo_profile_for_meta = None
    if is_gt:
        # Serialize only JSON-safe keys from the rasterio profile
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

    np.savez_compressed(wm_map_path, changed_idx=changed_idx, changed_vals=changed_vals)
    meta = {
        "shape": {"height": int(h), "width": int(w), "channels": 3},
        "watermark": {
            "height": int(wm_h),
            "width": int(wm_w),
            "bit_count": bit_count
        },
        "geotiff": is_gt,
        "geotiff_profile": geo_profile_for_meta
    }
    with open(wm_meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)

    # Compute PSNR between original and stego image
    psnr_value = compute_psnr(host_arr, stego_arr)
    cap_report = capacity_report(channel.size, bit_count, n=1)
    logging.info('Raster embed PSNR=%.2f dB, capacity report: %s', psnr_value, cap_report)

    return {
        "stego_path": stego_path,
        "wm_map_path": wm_map_path,
        "wm_meta_path": wm_meta_path,
        "bit_count": bit_count,
        "changed_count": int(changed_idx.size),
        "psnr": psnr_value,
        "capacity_report": cap_report,
        "geotiff": is_gt
    }


def recover_reversible(stego_path: str, wm_map_path: str, wm_meta_path: str, output_path: str) -> str:
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    # --- Read stego image (GeoTIFF-aware) ---
    stego_arr, raster_profile = read_geotiff(stego_path)
    if stego_arr.ndim == 2:
        stego_arr = np.stack([stego_arr] * 3, axis=-1)
    elif stego_arr.shape[2] == 1:
        stego_arr = np.concatenate([stego_arr] * 3, axis=-1)
    elif stego_arr.shape[2] > 3:
        stego_arr = stego_arr[:, :, :3]
    stego_arr = stego_arr.astype(np.uint8)

    h = int(meta["shape"]["height"])
    w = int(meta["shape"]["width"])
    if stego_arr.shape[0] != h or stego_arr.shape[1] != w:
        raise ValueError("输入图像尺寸与元数据不一致。")
    ch0 = stego_arr[:, :, 0].reshape(-1).copy()
    wm_map = np.load(wm_map_path)
    changed_idx = wm_map["changed_idx"].astype(np.int64)
    changed_vals = wm_map["changed_vals"].astype(np.uint8)
    ch0[changed_idx] = changed_vals
    recovered = stego_arr.copy()
    recovered[:, :, 0] = ch0.reshape(h, w)

    # --- Save recovered image (GeoTIFF if original was GeoTIFF) ---
    is_gt = meta.get("geotiff", False)
    if is_gt:
        # Rebuild a rasterio profile from the stored metadata
        geo_profile = meta.get("geotiff_profile", {})
        # Restore CRS from WKT string if present
        if "crs" in geo_profile:
            try:
                import rasterio.crs
                geo_profile["crs"] = rasterio.crs.CRS.from_wkt(geo_profile["crs"])
            except Exception:
                pass
        # Restore Affine transform from list
        if "transform" in geo_profile and isinstance(geo_profile["transform"], list):
            try:
                import affine
                geo_profile["transform"] = affine.Affine(*geo_profile["transform"])
            except Exception:
                pass
        geo_profile.update({"driver": "GTiff", "height": h, "width": w, "count": 3, "dtype": "uint8"})
        save_geotiff(recovered, geo_profile, output_path)
    else:
        Image.fromarray(recovered, mode="RGB").save(output_path, format="PNG")
    return output_path


def decode_reversible(stego_path: str, wm_meta_path: str, output_path: str) -> str:
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    # --- Read stego image (GeoTIFF-aware) ---
    stego_arr, _ = read_geotiff(stego_path)
    if stego_arr.ndim == 2:
        stego_arr = np.stack([stego_arr] * 3, axis=-1)
    elif stego_arr.shape[2] == 1:
        stego_arr = np.concatenate([stego_arr] * 3, axis=-1)
    elif stego_arr.shape[2] > 3:
        stego_arr = stego_arr[:, :, :3]
    stego_arr = stego_arr.astype(np.uint8)

    h = int(meta["shape"]["height"])
    w = int(meta["shape"]["width"])
    wm_h = int(meta["watermark"]["height"])
    wm_w = int(meta["watermark"]["width"])
    bit_count = int(meta["watermark"]["bit_count"])
    if stego_arr.shape[0] != h or stego_arr.shape[1] != w:
        raise ValueError("输入图像尺寸与元数据不一致。")
    bits = (stego_arr[:, :, 0].reshape(-1)[:bit_count] & 0x01).astype(np.uint8)
    wm = (bits.reshape(wm_h, wm_w) * 255).astype(np.uint8)
    Image.fromarray(wm, mode="L").save(output_path, format="PNG")
    return output_path
