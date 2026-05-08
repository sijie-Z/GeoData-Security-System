"""GeoTIFF-aware raster I/O utilities.

Provides read / write helpers that preserve CRS, transform and other
georeference metadata when watermarking GeoTIFF rasters.  Falls back to
PIL (Pillow) when rasterio is not available.
"""

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy rasterio availability check
# ---------------------------------------------------------------------------
_RASTERIO_AVAILABLE: bool | None = None


def _check_rasterio() -> bool:
    global _RASTERIO_AVAILABLE
    if _RASTERIO_AVAILABLE is None:
        try:
            import rasterio  # noqa: F401
            _RASTERIO_AVAILABLE = True
        except ImportError:
            _RASTERIO_AVAILABLE = False
            logger.warning(
                "rasterio is not installed. GeoTIFF metadata will NOT be "
                "preserved. Install with: pip install rasterio"
            )
    return _RASTERIO_AVAILABLE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_geotiff(path: str) -> bool:
    """Check whether *path* is a GeoTIFF file.

    Returns ``True`` only when rasterio can open the file **as a GTiff**
    and it carries a geospatial CRS (or a non-identity transform).
    Plain TIFFs without georeference, PNGs, JPEGs etc. return ``False``.

    A quick file-extension guard avoids opening non-TIFF files with
    rasterio (prevents Windows file-locking issues and unnecessary I/O).
    """
    # Fast path: only .tif / .tiff files can be GeoTIFFs
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".tif", ".tiff"):
        return False
    if not _check_rasterio():
        return False
    try:
        import rasterio
        with rasterio.open(path) as src:
            driver = src.driver
            crs = src.crs
            transform = src.transform
        # Has an explicit CRS -> definitely a GeoTIFF
        if crs is not None:
            return True
        # No CRS but has a non-identity geotransform -> still georeferenced
        if transform is not None and not transform.is_identity:
            return True
        return False
    except Exception:
        return False


def read_geotiff(path: str) -> tuple[np.ndarray, dict]:
    """Read a raster image, returning ``(array, profile)``.

    When rasterio is available *and* the file is a GeoTIFF the returned
    **profile** dict contains the full rasterio profile (crs, transform,
    nodata, driver, etc.) so it can be round-tripped later.

    For non-GeoTIFF files (PNG, JPEG, …) or when rasterio is missing the
    profile will be a minimal dict with just ``{"height", "width",
    "count", "dtype", "geotiff": False}`` so callers can distinguish the
    two paths.
    """
    # Only use rasterio for actual GeoTIFF files to avoid band-ordering
    # and dtype differences when rasterio opens PNGs, JPEGs, etc.
    if is_geotiff(path):
        try:
            import rasterio
            with rasterio.open(path) as src:
                # Read all bands; rasterio returns (bands, H, W)
                arr = src.read()
                profile = dict(src.profile)
                profile["geotiff"] = True
                # Convert to HWC for downstream code that expects it
                if arr.ndim == 3:
                    arr = np.moveaxis(arr, 0, -1)  # (bands,H,W) -> (H,W,bands)
                else:
                    # Single-band -> treat as grayscale
                    arr = arr[np.newaxis, :, :]  # add band axis
                    arr = np.moveaxis(arr, 0, -1)
                logger.debug("Read GeoTIFF %s  shape=%s  crs=%s", path, arr.shape, profile.get("crs"))
                return arr, profile
        except Exception as exc:
            logger.debug("rasterio read failed for %s (%s), falling back to PIL", path, exc)

    # --- PIL fallback (non-GeoTIFF or rasterio unavailable) ---
    from PIL import Image
    img = Image.open(path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    h, w = arr.shape[:2]
    profile = {"height": h, "width": w, "count": 3, "dtype": "uint8", "geotiff": False}
    logger.debug("Read %s via PIL fallback  shape=%s", path, arr.shape)
    return arr, profile


def save_geotiff(arr: np.ndarray, profile: dict, output_path: str) -> str:
    """Save *arr* as a raster image.

    If *profile* carries ``geotiff=True`` **and** rasterio is available the
    output will be a GeoTIFF that preserves the original CRS and
    transform.  Otherwise the image is saved as PNG via PIL.

    Parameters
    ----------
    arr : np.ndarray
        Image data in ``(H, W, C)`` uint8 layout.
    profile : dict
        A profile dict originally obtained from :func:`read_geotiff`.
    output_path : str
        Destination path.

    Returns
    -------
    str
        The path that was actually written (may differ from *output_path*
        if the extension was adjusted).
    """
    is_gt = profile.get("geotiff", False)

    if is_gt and _check_rasterio():
        try:
            import rasterio
            # Build write-profile from the original one
            write_profile = {k: v for k, v in profile.items() if k != "geotiff"}
            # Ensure output extension is .tif / .tiff
            base, ext = os.path.splitext(output_path)
            if ext.lower() not in (".tif", ".tiff"):
                output_path = base + ".tif"
            # Update dimensions to match the array
            if arr.ndim == 3:
                h, w, c = arr.shape
            else:
                h, w = arr.shape
                c = 1
            write_profile.update({
                "driver": "GTiff",
                "height": h,
                "width": w,
                "count": c,
                "dtype": str(arr.dtype),
            })
            # Convert HWC -> CHW for rasterio
            if arr.ndim == 3:
                write_arr = np.moveaxis(arr, -1, 0)
            else:
                write_arr = arr[np.newaxis, :, :]
            with rasterio.open(output_path, "w", **write_profile) as dst:
                dst.write(write_arr)
            logger.info("Saved GeoTIFF %s  crs=%s  transform=%s", output_path, write_profile.get("crs"), write_profile.get("transform"))
            return output_path
        except Exception as exc:
            logger.warning("Failed to write GeoTIFF (%s), falling back to PNG: %s", output_path, exc)

    # --- PIL fallback (non-GeoTIFF or rasterio unavailable) ---
    from PIL import Image
    base, ext = os.path.splitext(output_path)
    if ext.lower() in (".tif", ".tiff"):
        output_path = base + ".png"
    if arr.ndim == 3:
        if arr.shape[2] == 1:
            img = Image.fromarray(arr[:, :, 0], mode="L")
        else:
            img = Image.fromarray(arr, mode="RGB")
    else:
        img = Image.fromarray(arr, mode="L")
    img.save(output_path, format="PNG")
    logger.debug("Saved PNG fallback %s", output_path)
    return output_path
