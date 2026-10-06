"""Blind (DWT-DCT-SVD) watermarking for raster images, via the blind_watermark
library (guofei9987, MIT, https://github.com/guofei9987/blind_watermark).

Fourth raster algorithm alongside the reversible-LSB, DWT+QIM and histogram
shifting modules. The payload is the QR-code bitmap handed over as a PIL
image; its bits are shuffled with ``password_wm`` and embedded block-wise
(each 8x8 pixel block carries one bit, repeated across the whole block grid)
with SVD modulation of DCT coefficients (d1=36, d2=20), so extraction needs
neither the original host nor a change map — only the password and the
watermark dimensions recorded in the meta JSON ("blind" extraction).

Capacity (hard limit, enforced by the library): one bit per 8x8 pixel block,
i.e. ``block_num = floor(((H+1)//2)/4) * floor(((W+1)//2)/4)``; the library
asserts ``wm_bits < block_num`` (strictly fewer). The watermark bitmap is
used at its natural size — nothing is resized — so an oversized QR surfaces
as ``Insufficient blind watermark capacity`` (mapped to HTTP 400 by the
raster endpoints, same prefix convention as the other algorithms).

Robustness, measured on blind_watermark 0.4.4 (honest numbers, see the
project report):
- Uncropped roundtrip is exact (NC 1.0, PSNR ~37.7 dB at defaults).
- Crops that keep the image WIDTH and the top-left origin (e.g. trimming
  bottom rows) decode directly with NC 1.0: the block grid and the
  bit-to-block assignment are preserved.
- Arbitrary crops (e.g. keeping the center) shift the block grid; direct
  extraction then returns noise (measured NC ~0.52-0.60). The library's
  official fix is geometric realignment: locate the attacked image inside
  the original host via template matching and paste it back at its original
  coordinates (``recover.estimate_crop_parameters`` + ``recover_crop``),
  then extract. ``extract_blind`` does this automatically when the original
  host is still available (its path is recorded in the meta JSON). The
  pasted-back void is not free either: empty (zero) blocks vote 0 for every
  bit, diluting each bit's majority.
- The realignment only recovers crops when the watermark uses a small
  fraction of the block grid. Measured: 1024x1024 host + 41x41 watermark
  (utilization 10.3%) -> NC 1.00 after a 30% center crop, 0.999 after 40%;
  512x512 host + 41x41 watermark (utilization 41%) -> NC 0.92 after a 10%
  crop but only 0.56 after 30%. Keep ``wm_bits`` well below ``block_num/10``
  when crop recovery matters.

Implementation notes:
- The library works on cv2-order (BGR) arrays and would otherwise call
  ``cv2.imread``/``cv2.imwrite`` with our paths (unusable for non-ASCII
  Windows paths). We therefore feed and receive plain numpy arrays via the
  ``img=`` / ``embed_img=`` parameters and keep all file I/O in rasterio/PIL.
- GeoTIFF hosts keep CRS/transform: the stego image is written back through
  ``save_geotiff`` with the host's rasterio profile (same pattern as the
  reversible/histogram modules). Multi-band rasters use their first three
  bands as RGB and are clipped to 8-bit, like the other raster algorithms.
- Embedding is deterministic and serial (library default "common" pool):
  no multiprocessing on Windows, no shared mutable state between requests.
"""

import json
import logging
import os
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

from algorithm.quality_metrics import capacity_report, compute_psnr
from algorithm.raster_geotiff_utils import read_geotiff, save_geotiff

# blind_watermark imports its whole toolbox (cv2, pywt) at import time; if the
# dependency is missing we still want a clear message at first use rather than
# a broken import of every resource module.
try:
    from blind_watermark import WaterMark
    from blind_watermark import recover as _blind_recover
except ImportError as _exc:  # pragma: no cover - exercised only without the dep
    WaterMark = None
    _blind_recover = None
    _BLIND_IMPORT_ERROR = _exc
else:
    _BLIND_IMPORT_ERROR = None

# Same convention as the other raster modules.
WM_THRESHOLD = 127


def _ensure_dependency():
    if WaterMark is None:  # pragma: no cover - exercised only without the dep
        raise ImportError(
            "blind_watermark is not installed; install it with `pip install blind_watermark` "
            f"(original error: {_BLIND_IMPORT_ERROR})"
        )


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _read_rgb_array(path: str) -> np.ndarray:
    """Load *path* as an (H, W, 3) uint8 RGB array.

    Same convention as ``raster_dwt_watermark._read_rgb_array``: rasterio for
    GeoTIFFs, PIL otherwise; multi-band rasters reduce to their first three
    bands; non-8-bit samples are clipped into 0-255 because the payload the
    library operates on is an 8-bit image.
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


def _blind_block_capacity(height: int, width: int) -> int:
    """Number of embeddable bits for an HxW host: one per 8x8 pixel block.

    Mirrors ``WaterMarkCore.read_img_arr``: the Y/UV channels are Haar-DWT
    transformed (halved), then split into non-overlapping 4x4 coefficient
    blocks, so an HxW image provides floor(((H+1)/2)/4) * floor(((W+1)/2)/4)
    blocks and the library requires ``bit_count < block_num`` (strictly less).
    """
    return ((height + 1) // 2 // 4) * ((width + 1) // 2 // 4)


def _to_wm_bits(watermark_img: Image.Image) -> np.ndarray:
    """QR bitmap -> flat boolean bit array (library ``mode='bit'`` payload).

    Deliberately NOT resized: the library capacity error is the honest
    contract (unlike dwt/histogram, which resize the payload themselves).
    The array must be one-dimensional: the library shuffles it with
    ``RandomState(password_wm).shuffle``, which only permutes the first axis.
    """
    wm_arr = np.array(watermark_img.convert("L"), dtype=np.uint8)
    return wm_arr.reshape(-1) > WM_THRESHOLD


def embed_blind(
    host_path: str,
    watermark_img: Image.Image,
    output_dir: str,
    prefix: str,
    password_img: int = 1,
    password_wm: int = 1,
) -> dict:
    """Embed a watermark bitmap into a raster using blind_watermark (DWT-DCT-SVD).

    Args:
        host_path: Path to the host image file (GeoTIFF metadata is preserved).
        watermark_img: PIL Image (the QR bitmap) embedded at its natural size.
        output_dir: Directory for output files.
        prefix: Filename prefix for output files.
        password_img: Block-position shuffle seed (stored in the meta JSON).
        password_wm: Watermark-bit shuffle seed (stored in the meta JSON).

    Returns:
        Dict with keys: stego_path, wm_meta_path, psnr, capacity_report,
        bit_count, blocks.

    Raises:
        ValueError: "Insufficient blind watermark capacity: ..." when the
            watermark does not fit the host's block grid (~one bit per 8x8
            pixels).
    """
    _ensure_dependency()
    _ensure_dir(output_dir)

    # Load host as RGB (first three bands for multi-band rasters).
    host_rgb = _read_rgb_array(host_path)
    h, w = host_rgb.shape[:2]

    wm_gray = watermark_img.convert("L")
    wm_w, wm_h = wm_gray.size
    wm_bits = _to_wm_bits(wm_gray)
    bit_count = int(wm_bits.size)

    block_num = _blind_block_capacity(h, w)
    if bit_count >= block_num:
        cap = capacity_report(block_num, bit_count, n=1)
        raise ValueError(
            f"Insufficient blind watermark capacity: need {bit_count} bits but "
            f"the host image ({w}x{h}) provides only {block_num - 1} embeddable bits "
            f"(one per 8x8 pixel block). Capacity report: {cap}"
        )

    # The library expects cv2-order (BGR) arrays; feed arrays directly so no
    # cv2.imread/cv2.imwrite ever touches our (possibly non-ASCII) paths.
    host_bgr = np.ascontiguousarray(host_rgb[:, :, ::-1])
    bwm = WaterMark(password_img=password_img, password_wm=password_wm)
    bwm.read_img(img=host_bgr)
    bwm.read_wm(wm_bits.copy(), mode="bit")
    embedded_bgr = bwm.embed()
    stego_arr = np.clip(np.round(embedded_bgr[:, :, ::-1]), 0, 255).astype(np.uint8)

    # --- read host profile for GeoTIFF-aware output ---
    _host_arr, raster_profile = read_geotiff(host_path)
    is_gt = raster_profile.get("geotiff", False)
    if is_gt:
        logging.info("Blind embed: input is a GeoTIFF — CRS/transform will be preserved: %s", host_path)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stego_filename = f"{prefix}_{timestamp}_blind_stego{'_geotiff' if is_gt else ''}.{'tif' if is_gt else 'png'}"
    stego_path = os.path.join(output_dir, stego_filename)
    wm_meta_path = os.path.join(output_dir, f"{prefix}_{timestamp}_blind_wm_meta.json")

    # --- Save stego image (GeoTIFF if input was GeoTIFF, preserving CRS/transform) ---
    if is_gt:
        # Keep the original rasterio profile (including the "geotiff" marker) so
        # save_geotiff takes the GTiff path and preserves CRS/transform; it
        # strips the marker itself when building the write profile.
        stego_profile = dict(raster_profile)
        stego_profile.update({"driver": "GTiff", "height": h, "width": w, "count": 3, "dtype": "uint8"})
        # Trust the returned path: on a write failure save_geotiff falls back
        # to PNG and reports that path, so callers never record a missing file.
        stego_path = save_geotiff(stego_arr, stego_profile, stego_path)
    else:
        Image.fromarray(stego_arr, mode="RGB").save(stego_path, format="PNG")
    if not os.path.isfile(stego_path):
        raise RuntimeError(f"stego image was not written to disk: {stego_path}")

    # --- Serialize the GeoTIFF profile for the meta JSON (same as reversible) ---
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

    utility = round(bit_count / max(block_num, 1) * 100, 2)
    meta = {
        "algorithm": "blind_watermark",
        "password_img": int(password_img),
        "password_wm": int(password_wm),
        # Absolute path of the original host: extract_blind uses it as the
        # template for geometric realignment of cropped stegos.
        "host_path": host_path,
        "shape": {"height": int(h), "width": int(w), "channels": 3},
        "watermark": {"height": int(wm_h), "width": int(wm_w), "bit_count": bit_count},
        "capacity": {"block_num": int(block_num), "utilization_percent": utility},
        "geotiff": is_gt,
        "geotiff_profile": geo_profile_for_meta,
    }
    with open(wm_meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)

    psnr_value = compute_psnr(host_rgb, stego_arr)
    cap_report = capacity_report(block_num, bit_count, n=1)
    logging.info(
        "Blind embed PSNR=%.2f dB, %d bits / %d blocks (utilization %.2f%%), capacity report: %s",
        psnr_value,
        bit_count,
        block_num,
        utility,
        cap_report,
    )

    return {
        "stego_path": stego_path,
        "wm_meta_path": wm_meta_path,
        "psnr": psnr_value,
        "capacity_report": cap_report,
        "bit_count": bit_count,
        "blocks": int(block_num),
    }


def _realign_cropped(stego_rgb: np.ndarray, template_path: str) -> np.ndarray | None:
    """Paste a cropped stego back into its original frame (library recipe).

    Returns the full-frame reconstruction when a crop was detected, or None
    when the image already covers the full frame / realignment is not
    applicable (the caller then extracts directly). Pure crop attacks are
    handled with a fixed scale of 1 — rescaling attacks are out of scope.
    """
    try:
        host_rgb = _read_rgb_array(template_path)
    except Exception as exc:
        logging.warning("Blind extract: template %s unreadable (%s); extracting directly", template_path, exc)
        return None

    h_att, w_att = stego_rgb.shape[:2]
    h_org, w_org = host_rgb.shape[:2]
    if h_att > h_org or w_att > w_org:
        # An attacked image larger than the original cannot be located by
        # cv2.matchTemplate (and is not a crop); fall back to direct extract.
        return None

    try:
        tem_gray = cv2.cvtColor(stego_rgb, cv2.COLOR_RGB2GRAY)
        ori_gray = cv2.cvtColor(host_rgb, cv2.COLOR_RGB2GRAY)
        loc, ori_shape, score, _scale = _blind_recover.estimate_crop_parameters(
            ori_img=ori_gray, tem_img=tem_gray, scale=(1, 1)
        )
        x1, y1, x2, y2 = (int(v) for v in loc)
        if score < 0.5:
            logging.warning("Blind extract: template match score %.3f too low; extracting directly", score)
            return None
        if x1 == 0 and y1 == 0 and (x2 - x1) == w_org and (y2 - y1) == h_org:
            # Full frame found at the origin: nothing was cropped, direct extract.
            return None
        restored = _blind_recover.recover_crop(tem_img=stego_rgb, loc=loc, image_o_shape=ori_shape)
        logging.info(
            "Blind extract: attacked image located at (%d, %d, %d, %d) in the original (score %.3f); "
            "using crop realignment",
            x1,
            y1,
            x2,
            y2,
            score,
        )
        return np.clip(np.round(restored), 0, 255).astype(np.uint8)
    except Exception as exc:
        logging.warning("Blind extract: crop realignment failed (%s); extracting directly", exc)
        return None


def extract_blind(
    stego_path: str,
    wm_meta_path: str,
    output_path: str,
    template_path: str | None = None,
) -> str:
    """Blind-extract the watermark bitmap from a stego image.

    Args:
        stego_path: Path to the (possibly cropped) stego image.
        wm_meta_path: Path to the blind watermark meta JSON.
        output_path: Path to save the extracted watermark bitmap (PNG).
        template_path: Optional path of the original host used as the template
            for crop realignment. Defaults to the ``host_path`` recorded in
            the meta JSON; when neither exists the image is extracted as-is.

    Returns:
        output_path.
    """
    _ensure_dependency()
    with open(wm_meta_path, encoding="utf-8") as fp:
        meta = json.load(fp)

    password_img = int(meta.get("password_img", 1))
    password_wm = int(meta.get("password_wm", 1))
    wm_h = int(meta["watermark"]["height"])
    wm_w = int(meta["watermark"]["width"])

    stego_rgb = _read_rgb_array(stego_path)

    # Cropped stegos (center crops shift the block grid) are realigned with
    # the original host as template before extraction — the library's
    # documented recipe; see the module docstring for measured limits.
    template = template_path or meta.get("host_path")
    work_rgb = stego_rgb
    if template and os.path.isfile(template):
        restored = _realign_cropped(stego_rgb, template)
        if restored is not None:
            work_rgb = restored

    bwm = WaterMark(password_img=password_img, password_wm=password_wm)
    recovered = bwm.extract(
        embed_img=np.ascontiguousarray(work_rgb[:, :, ::-1]),
        wm_shape=(wm_h, wm_w),
        mode="bit",
    )
    wm_img = (recovered.reshape(wm_h, wm_w) * 255).astype(np.uint8)
    Image.fromarray(wm_img, mode="L").save(output_path, format="PNG")

    logging.info("Blind extract: recovered %dx%d watermark (%d bits) to %s", wm_w, wm_h, wm_h * wm_w, output_path)
    return output_path
