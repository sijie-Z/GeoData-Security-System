"""DWT (Discrete Wavelet Transform) frequency-domain watermarking for raster images.

Uses QIM (Quantization Index Modulation) on the LL subband of the DWT
decomposition to embed watermark bits. This approach is more robust against
image attacks (compression, cropping, noise) compared to spatial-domain LSB.
"""
import json
import logging
import os
from datetime import datetime

import numpy as np
import pywt
from PIL import Image

from algorithm.quality_metrics import compute_psnr, capacity_report


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _to_binary_watermark(watermark_img: Image.Image, width: int, height: int,
                         threshold: int = 127) -> np.ndarray:
    """Convert a watermark image to a binary bit array of given dimensions."""
    wm = watermark_img.convert("L").resize((width, height), Image.Resampling.NEAREST)
    return (np.array(wm, dtype=np.uint8) > threshold).astype(np.uint8)


def _multi_level_dwt2(coeffs, level):
    """Apply multi-level dwt2 starting from the approximation (LL) subband."""
    cA = coeffs
    details_list = []
    for _ in range(level):
        cA, (cH, cV, cD) = pywt.dwt2(cA, 'haar')
        details_list.append((cH, cV, cD))
    return cA, details_list


def _multi_level_idwt2(cA, details_list):
    """Inverse multi-level dwt2, restoring from the deepest LL subband."""
    for details in reversed(details_list):
        cA = pywt.idwt2((cA, details), 'haar')
    return cA


def embed_dwt(host_path: str, watermark_img: Image.Image, output_dir: str,
              prefix: str, level: int = 2) -> dict:
    """Embed a watermark into a raster image using DWT + QIM.

    Args:
        host_path: Path to the host image file.
        watermark_img: PIL Image (grayscale/binary QR code) to embed.
        output_dir: Directory for output files.
        prefix: Filename prefix for output files.
        level: Number of DWT decomposition levels (default 2).

    Returns:
        Dict with keys: stego_path, wm_meta_path, psnr, capacity_report.
    """
    _ensure_dir(output_dir)

    # Load host image and convert to YCbCr
    host_pil = Image.open(host_path)
    if host_pil.mode == 'L':
        host_pil = host_pil.convert('RGB')
    host_ycbcr = np.array(host_pil.convert('YCbCr'), dtype=np.float64)
    h, w, _ = host_ycbcr.shape

    # Extract Y channel and apply multi-level DWT
    y_channel = host_ycbcr[:, :, 0]
    cA, details_list = _multi_level_dwt2(y_channel, level)

    # Prepare watermark bits
    wm_h, wm_w = cA.shape
    wm_bits_2d = _to_binary_watermark(watermark_img, wm_w, wm_h)
    wm_bits = wm_bits_2d.reshape(-1)
    bit_count = int(wm_bits.size)

    # Capacity check
    total_coeffs = int(cA.size)
    if bit_count > total_coeffs:
        cap = capacity_report(total_coeffs, bit_count, n=1)
        raise ValueError(
            f"Insufficient DWT capacity: need {bit_count} bits but LL subband "
            f"has only {total_coeffs} coefficients. Capacity report: {cap}"
        )

    # QIM embedding into LL subband
    step = 30.0  # Quantization step size
    ll_flat = cA.reshape(-1).copy()
    original_ll = ll_flat[:bit_count].copy()

    for i in range(bit_count):
        quantized = round(ll_flat[i] / step)
        ll_flat[i] = quantized * step + wm_bits[i] * step / 4.0

    # Track changed coefficients for reversibility
    embedded_ll = ll_flat[:bit_count].copy()
    changed_mask = np.abs(original_ll - embedded_ll) > 1e-10
    changed_idx = np.nonzero(changed_mask)[0].astype(np.int64)
    changed_vals = original_ll[changed_mask].astype(np.float64)

    cA_embedded = ll_flat.reshape(cA.shape)

    # Inverse DWT to reconstruct watermarked Y channel
    y_watermarked = _multi_level_idwt2(cA_embedded, details_list)
    y_watermarked = np.clip(y_watermarked, 0, 255)

    # Reconstruct RGB image
    stego_ycbcr = host_ycbcr.copy()
    stego_ycbcr[:, :, 0] = y_watermarked
    stego_rgb = Image.fromarray(stego_ycbcr.astype(np.uint8), mode='YCbCr').convert('RGB')
    stego_arr = np.array(stego_rgb, dtype=np.uint8)

    # Save stego image and metadata
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stego_path = os.path.join(output_dir, f"{prefix}_{timestamp}_dwt_stego.png")
    wm_meta_path = os.path.join(output_dir, f"{prefix}_{timestamp}_dwt_wm_meta.json")

    stego_rgb.save(stego_path, format="PNG")

    meta = {
        "algorithm": "dwt",
        "quantization_step": step,
        "dwt_level": level,
        "wavelet": "haar",
        "shape": {"height": int(h), "width": int(w), "channels": 3},
        "watermark": {
            "height": int(wm_h),
            "width": int(wm_w),
            "bit_count": bit_count
        },
        "changed_idx": changed_idx.tolist(),
        "changed_vals": changed_vals.tolist()
    }
    with open(wm_meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)

    # Compute PSNR
    psnr_value = compute_psnr(
        np.array(host_pil.convert('RGB'), dtype=np.uint8),
        stego_arr
    )
    cap_report = capacity_report(total_coeffs, bit_count, n=1)
    logging.info('DWT embed PSNR=%.2f dB, capacity report: %s', psnr_value, cap_report)

    return {
        "stego_path": stego_path,
        "wm_meta_path": wm_meta_path,
        "psnr": psnr_value,
        "capacity_report": cap_report
    }


def extract_dwt(stego_path: str, wm_meta_path: str, output_path: str) -> str:
    """Extract a watermark from a DWT-watermarked image.

    Args:
        stego_path: Path to the stego image.
        wm_meta_path: Path to the DWT watermark metadata JSON.
        output_path: Path to save the extracted watermark image.

    Returns:
        output_path.
    """
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    # Load stego image and convert to YCbCr
    stego_pil = Image.open(stego_path)
    if stego_pil.mode == 'L':
        stego_pil = stego_pil.convert('RGB')
    stego_ycbcr = np.array(stego_pil.convert('YCbCr'), dtype=np.float64)

    # Apply DWT to Y channel
    level = int(meta.get("dwt_level", 2))
    y_channel = stego_ycbcr[:, :, 0]
    cA, _ = _multi_level_dwt2(y_channel, level)

    # Extract bits using QIM threshold
    step = float(meta["quantization_step"])
    wm_h = int(meta["watermark"]["height"])
    wm_w = int(meta["watermark"]["width"])
    bit_count = int(meta["watermark"]["bit_count"])

    ll_flat = cA.reshape(-1)
    bits = np.zeros(bit_count, dtype=np.uint8)
    for i in range(bit_count):
        q = round(ll_flat[i] / step)
        bits[i] = q % 2

    # Reconstruct watermark image
    wm = (bits.reshape(wm_h, wm_w) * 255).astype(np.uint8)
    Image.fromarray(wm, mode="L").save(output_path, format="PNG")

    logging.info('DWT extract: recovered %d-bit watermark (%dx%d)', bit_count, wm_w, wm_h)
    return output_path


def recover_dwt(stego_path: str, wm_meta_path: str, output_path: str) -> str:
    """Recover the original host image from a DWT-watermarked stego image.

    Uses saved original LL coefficients to perfectly restore the host image
    (true reversibility).

    Args:
        stego_path: Path to the stego image.
        wm_meta_path: Path to the DWT watermark metadata JSON.
        output_path: Path to save the recovered original image.

    Returns:
        output_path.
    """
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)

    # Load stego image and convert to YCbCr
    stego_pil = Image.open(stego_path)
    if stego_pil.mode == 'L':
        stego_pil = stego_pil.convert('RGB')
    stego_ycbcr = np.array(stego_pil.convert('YCbCr'), dtype=np.float64)

    # Apply DWT to Y channel
    level = int(meta.get("dwt_level", 2))
    y_channel = stego_ycbcr[:, :, 0]
    cA, details_list = _multi_level_dwt2(y_channel, level)

    # Restore original LL coefficients at changed positions
    changed_idx = np.array(meta["changed_idx"], dtype=np.int64)
    changed_vals = np.array(meta["changed_vals"], dtype=np.float64)
    ll_flat = cA.reshape(-1).copy()
    ll_flat[changed_idx] = changed_vals
    cA_restored = ll_flat.reshape(cA.shape)

    # Inverse DWT
    y_recovered = _multi_level_idwt2(cA_restored, details_list)
    y_recovered = np.clip(np.round(y_recovered), 0, 255)

    # Reconstruct RGB image
    recovered_ycbcr = stego_ycbcr.copy()
    recovered_ycbcr[:, :, 0] = y_recovered
    recovered_rgb = Image.fromarray(recovered_ycbcr.astype(np.uint8), mode='YCbCr').convert('RGB')
    recovered_rgb.save(output_path, format="PNG")

    logging.info('DWT recover: restored original image to %s', output_path)
    return output_path
