"""GeoServer REST API helper — auto-publish vector/raster layers."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _get_config():
    """Read GeoServer settings from env (lazy to avoid import-time errors)."""
    return {
        "url": os.environ.get("GEOSERVER_URL", "http://localhost:8080/geoserver"),
        "username": os.environ.get("GEOSERVER_USER", "admin"),
        "password": os.environ.get("GEOSERVER_PASSWORD", "geoserver"),
        "workspace": os.environ.get("GEOSERVER_WORKSPACE", "test"),
    }


def _auth():
    cfg = _get_config()
    return httpx.BasicAuth(cfg["username"], cfg["password"])


def _base():
    return _get_config()["url"].rstrip("/")


def _workspace():
    return _get_config()["workspace"]


# ── Workspace ──────────────────────────────────────────────


def ensure_workspace(workspace: str | None = None) -> bool:
    """Create workspace if it doesn't exist. Returns True on success."""
    ws = workspace or _workspace()
    url = f"{_base()}/rest/workspaces"
    try:
        # Check if exists
        r = httpx.get(f"{url}/{ws}", auth=_auth(), timeout=10)
        if r.status_code == 200:
            return True
        # Create
        r = httpx.post(
            url,
            auth=_auth(),
            headers={"Content-Type": "application/json"},
            json={"workspace": {"name": ws}},
            timeout=10,
        )
        if r.status_code in (200, 201):
            logger.info("GeoServer workspace '%s' created", ws)
            return True
        logger.error("GeoServer create workspace failed: %s %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.error("GeoServer ensure_workspace error: %s", e)
        return False


# ── Publish Shapefile ──────────────────────────────────────


def publish_shapefile(shp_zip_path: str, layer_name: str, workspace: str | None = None) -> dict:
    """
    Upload a zipped Shapefile to GeoServer and publish it as a layer.

    Args:
        shp_zip_path: Path to the .zip file containing .shp/.dbf/.shx/.prj
        layer_name:   Name for the published layer (used as both store and layer name)
        workspace:    GeoServer workspace (defaults to env GEOSERVER_WORKSPACE)

    Returns:
        {"success": True, "wms_url": "...", "layer": "workspace:layer_name"} or
        {"success": False, "error": "..."}
    """
    ws = workspace or _workspace()

    if not os.path.isfile(shp_zip_path):
        return {"success": False, "error": f"File not found: {shp_zip_path}"}

    # Ensure workspace exists
    if not ensure_workspace(ws):
        return {"success": False, "error": "Cannot create/access GeoServer workspace"}

    # Store name = layer name (simplified)
    store_name = layer_name

    # Upload Shapefile zip via PUT to the datastores endpoint
    # GeoServer REST: PUT /rest/workspaces/{ws}/datastores/{ds}/file.shp
    url = f"{_base()}/rest/workspaces/{ws}/datastores/{store_name}/file.shp"

    try:
        with open(shp_zip_path, "rb") as f:
            r = httpx.put(
                url,
                auth=_auth(),
                headers={"Content-Type": "application/zip"},
                content=f.read(),
                timeout=60,
            )

        if r.status_code in (200, 201):
            wms_url = f"{_base()}/{ws}/wms"
            full_layer = f"{ws}:{layer_name}"
            logger.info("Published Shapefile '%s' to GeoServer as %s", layer_name, full_layer)
            return {"success": True, "wms_url": wms_url, "layer": full_layer}

        # If store already exists, try to update
        if r.status_code in (400, 409) and "already exists" in r.text.lower():
            # Re-upload to existing store
            url2 = f"{_base()}/rest/workspaces/{ws}/datastores/{store_name}/file.shp?update=overwrite"
            with open(shp_zip_path, "rb") as f:
                r2 = httpx.put(
                    url2,
                    auth=_auth(),
                    headers={"Content-Type": "application/zip"},
                    content=f.read(),
                    timeout=60,
                )
            if r2.status_code in (200, 201):
                wms_url = f"{_base()}/{ws}/wms"
                full_layer = f"{ws}:{layer_name}"
                logger.info("Updated Shapefile '%s' on GeoServer", layer_name)
                return {"success": True, "wms_url": wms_url, "layer": full_layer}

        logger.error("GeoServer publish Shapefile failed: %s %s", r.status_code, r.text[:300])
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

    except Exception as e:
        logger.error("GeoServer publish_shapefile error: %s", e)
        return {"success": False, "error": str(e)}


# ── Publish GeoTIFF ────────────────────────────────────────


def publish_geotiff(tiff_path: str, layer_name: str, workspace: str | None = None) -> dict:
    """
    Upload a GeoTIFF to GeoServer and publish it as a coverage layer.

    Args:
        tiff_path:   Path to the .tif / .tiff file
        layer_name:  Name for the published layer
        workspace:   GeoServer workspace (defaults to env GEOSERVER_WORKSPACE)

    Returns:
        {"success": True, "wms_url": "...", "layer": "workspace:layer_name"} or
        {"success": False, "error": "..."}
    """
    ws = workspace or _workspace()

    if not os.path.isfile(tiff_path):
        return {"success": False, "error": f"File not found: {tiff_path}"}

    if not ensure_workspace(ws):
        return {"success": False, "error": "Cannot create/access GeoServer workspace"}

    store_name = layer_name

    # Upload GeoTIFF via PUT to coveragestores endpoint
    # GeoServer REST: PUT /rest/workspaces/{ws}/coveragestores/{cs}/file.geotiff
    url = f"{_base()}/rest/workspaces/{ws}/coveragestores/{store_name}/file.geotiff"

    try:
        with open(tiff_path, "rb") as f:
            r = httpx.put(
                url,
                auth=_auth(),
                headers={"Content-Type": "image/tiff"},
                content=f.read(),
                timeout=120,  # GeoTIFF can be large
            )

        if r.status_code in (200, 201):
            wms_url = f"{_base()}/{ws}/wms"
            full_layer = f"{ws}:{layer_name}"
            logger.info("Published GeoTIFF '%s' to GeoServer as %s", layer_name, full_layer)
            return {"success": True, "wms_url": wms_url, "layer": full_layer}

        # If store already exists, try to update
        if r.status_code in (400, 409) and "already exists" in r.text.lower():
            url2 = f"{_base()}/rest/workspaces/{ws}/coveragestores/{store_name}/file.geotiff?update=overwrite"
            with open(tiff_path, "rb") as f:
                r2 = httpx.put(
                    url2,
                    auth=_auth(),
                    headers={"Content-Type": "image/tiff"},
                    content=f.read(),
                    timeout=120,
                )
            if r2.status_code in (200, 201):
                wms_url = f"{_base()}/{ws}/wms"
                full_layer = f"{ws}:{layer_name}"
                logger.info("Updated GeoTIFF '%s' on GeoServer", layer_name)
                return {"success": True, "wms_url": wms_url, "layer": full_layer}

        logger.error("GeoServer publish GeoTIFF failed: %s %s", r.status_code, r.text[:300])
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

    except Exception as e:
        logger.error("GeoServer publish_geotiff error: %s", e)
        return {"success": False, "error": str(e)}


# ── Delete Layer ───────────────────────────────────────────


def delete_layer(layer_name: str, workspace: str | None = None, recurse: bool = True) -> bool:
    """Delete a layer and its associated store from GeoServer."""
    ws = workspace or _workspace()
    recurse_param = "true" if recurse else "false"
    url = f"{_base()}/rest/layers/{ws}:{layer_name}?recurse={recurse_param}"
    try:
        r = httpx.delete(url, auth=_auth(), timeout=10)
        if r.status_code in (200, 404):
            return True
        logger.warning("GeoServer delete layer failed: %s %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.error("GeoServer delete_layer error: %s", e)
        return False
