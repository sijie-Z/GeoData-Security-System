"""Tests for the dynamic raster tile endpoint (rio-tiler) and its auth.

GET /api/raster_tiles/<data_id>/<z>/<x>/<y>.png renders each tile on demand from
the source GeoTIFF recorded in RasterData.raster_file_path — the old
pre-generated ``<UPLOAD_FOLDER>/tiles/...`` layout is not used anymore.

Auth: either an Authorization header (API clients) or a short-lived signed
``?token=`` from GET /api/raster_tiles_token/<data_id> (browsers, whose XYZ
tile loads cannot carry headers).

Note on fixtures: ``test/test_raster/test_raster.tif`` (the repo's raster
fixture) is *not* georeferenced (no CRS, identity transform), so a real,
georeferenced GeoTIFF is generated with rasterio for the tile-rendering cases;
a CRS-less source (the repo fixture when present, otherwise an equivalent
generated TIFF) is used to assert a clean 4xx.
"""

import io
import os
import sqlite3

import morecantile
import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.transform import from_bounds

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Fixture extent (WGS84), a small box over Hangzhou.
FIXTURE_BOUNDS = (119.9, 29.9, 120.1, 30.1)  # west, south, east, north
FIXTURE_ZOOM = 12


@pytest.fixture(scope="module")
def geotiff(tmp_path_factory):
    """A real, georeferenced 3-band GeoTIFF to serve tiles from."""
    path = tmp_path_factory.mktemp("tiles_src") / "geo_rgb.tif"
    rng = np.random.default_rng(42)
    data = (rng.random((3, 256, 256)) * 255).astype("uint8")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=256,
        height=256,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_bounds(*FIXTURE_BOUNDS, 256, 256),
    ) as dst:
        dst.write(data)
    return path


@pytest.fixture(scope="module")
def valid_tile():
    """A WebMercator tile (z/x/y) that intersects the geotiff's extent."""
    import morecantile

    tms = morecantile.tms.get("WebMercatorQuad")
    tiles = list(tms.tiles(*FIXTURE_BOUNDS, zooms=[FIXTURE_ZOOM]))
    assert tiles
    return tiles[len(tiles) // 2]


def _make_raster(db, path, name="tile-src"):
    from model.Raster_Data import RasterData

    record = RasterData(name=name, alias=name, raster_file_path=str(path), url="", layer="")
    db.session.add(record)
    db.session.commit()
    return record


def _tile_url(data_id, tile, token=None):
    url = f"/api/raster_tiles/{data_id}/{tile.z}/{tile.x}/{tile.y}.png"
    return f"{url}?token={token}" if token else url


REPO_RASTER_FIXTURE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test", "test_raster", "test_raster.tif")
)


@pytest.fixture(scope="module")
def no_crs_tif(tmp_path_factory):
    """A plain, non-georeferenced TIFF — the repo fixture, or an equivalent one.

    Reduced CI mounts may contain only ``testrealend/`` (the repo-root ``test/``
    folder then does not exist at its expected location), so generate an
    equivalent identity-transform, CRS-less TIFF when the repo file is absent
    instead of losing the no-CRS assertion.
    """
    if os.path.exists(REPO_RASTER_FIXTURE):
        return REPO_RASTER_FIXTURE
    path = tmp_path_factory.mktemp("no_crs") / "no_crs.tif"
    rng = np.random.default_rng(7)
    data = (rng.random((64, 64)) * 255).astype("uint8")
    with rasterio.open(path, "w", driver="GTiff", width=64, height=64, count=1, dtype="uint8") as dst:
        dst.write(data, 1)
    return path


class TestTileRendering:
    def test_header_auth_returns_rendered_png(self, client, db, auth_headers, geotiff, valid_tile):
        record = _make_raster(db, geotiff)
        resp = client.get(_tile_url(record.id, valid_tile), headers=auth_headers)
        assert resp.status_code == 200
        assert resp.mimetype == "image/png"
        assert resp.data.startswith(PNG_SIGNATURE)

    def test_query_token_returns_rendered_png(self, client, db, auth_headers, geotiff, valid_tile):
        record = _make_raster(db, geotiff)
        token_resp = client.get(f"/api/raster_tiles_token/{record.id}", headers=auth_headers)
        assert token_resp.status_code == 200
        token = token_resp.get_json()["token"]
        # Simulate the browser: bare GET, no Authorization header at all.
        resp = client.get(_tile_url(record.id, valid_tile, token=token))
        assert resp.status_code == 200
        assert resp.mimetype == "image/png"
        assert resp.data.startswith(PNG_SIGNATURE)

    def test_source_file_missing_returns_404(self, client, db, auth_headers, tmp_path, valid_tile):
        record = _make_raster(db, tmp_path / "does-not-exist.tif")
        resp = client.get(_tile_url(record.id, valid_tile), headers=auth_headers)
        assert resp.status_code == 404

    def test_unknown_data_id_returns_404(self, client, db, auth_headers, valid_tile):
        resp = client.get(_tile_url(10_000_000, valid_tile), headers=auth_headers)
        assert resp.status_code == 404

    def test_out_of_range_coordinates_return_4xx(self, client, db, auth_headers, geotiff, valid_tile):
        record = _make_raster(db, geotiff)
        # Valid grid position but far outside the raster extent.
        far = morecantile.Tile(valid_tile.x + 1000, valid_tile.y, valid_tile.z)
        resp = client.get(_tile_url(record.id, far), headers=auth_headers)
        assert resp.status_code == 400
        # z far beyond any reasonable zoom level.
        deep = morecantile.Tile(valid_tile.x, valid_tile.y, 40)
        resp = client.get(_tile_url(record.id, deep), headers=auth_headers)
        assert resp.status_code == 400

    def test_source_without_crs_returns_4xx_not_500(self, client, db, auth_headers, valid_tile, no_crs_tif):
        # The fixture is a plain (non-georeferenced) TIFF — prove it really
        # has no CRS, then assert the endpoint fails cleanly instead of 500.
        with rasterio.open(no_crs_tif) as src:
            assert src.crs is None
        record = _make_raster(db, no_crs_tif, name="no-crs")
        resp = client.get(_tile_url(record.id, valid_tile), headers=auth_headers)
        assert resp.status_code in (400, 422)

    def test_legacy_tiles_directory_is_ignored(
        self, client, db, auth_headers, geotiff, valid_tile, tmp_path, monkeypatch
    ):
        """A leftover pre-generated tile file must not be served anymore."""
        monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(tmp_path))
        record = _make_raster(db, geotiff)
        legacy = tmp_path / "tiles" / str(record.id) / str(valid_tile.z) / str(valid_tile.x)
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / f"{valid_tile.y}.png").write_bytes(b"legacy-pre-generated-tile")
        resp = client.get(_tile_url(record.id, valid_tile), headers=auth_headers)
        assert resp.status_code == 200
        assert resp.data.startswith(PNG_SIGNATURE)
        assert resp.data != b"legacy-pre-generated-tile"


class TestTileAuth:
    def test_tile_without_any_auth_returns_401(self, client, db, geotiff, valid_tile):
        record = _make_raster(db, geotiff)
        resp = client.get(_tile_url(record.id, valid_tile))
        assert resp.status_code == 401

    def test_garbage_token_returns_401(self, client, db, geotiff, valid_tile):
        record = _make_raster(db, geotiff)
        resp = client.get(_tile_url(record.id, valid_tile, token="not-a-real-token"))
        assert resp.status_code == 401

    def test_token_for_other_data_id_returns_401(self, client, db, auth_headers, geotiff, valid_tile):
        record_a = _make_raster(db, geotiff, name="a")
        record_b = _make_raster(db, geotiff, name="b")
        token = client.get(f"/api/raster_tiles_token/{record_a.id}", headers=auth_headers).get_json()["token"]
        resp = client.get(_tile_url(record_b.id, valid_tile, token=token))
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, db, app, geotiff, valid_tile):
        from resource.raster_resource import generate_tile_token

        record = _make_raster(db, geotiff)
        with app.app_context():
            expired = generate_tile_token(record.id, expires_in=-60)
        resp = client.get(_tile_url(record.id, valid_tile, token=expired))
        assert resp.status_code == 401

    def test_token_endpoint_requires_auth(self, client):
        resp = client.get("/api/raster_tiles_token/1")
        assert resp.status_code == 401

    def test_token_endpoint_issues_scoped_token(self, client, db, auth_headers):
        from resource.raster_resource import verify_tile_token

        resp = client.get("/api/raster_tiles_token/7", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["expires_in"] == 3600
        assert isinstance(body["token"], str) and body["token"]
        with client.application.app_context():
            assert verify_tile_token(body["token"], 7)
            assert not verify_tile_token(body["token"], 8)


class TestProjEnvGuard:
    """Unit tests for the PROJ_LIB/PROJ_DATA compatibility guard."""

    @staticmethod
    def _make_projdb(path, layout_minor):
        path.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(path / "proj.db"))
        con.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
        con.execute(
            "INSERT INTO metadata (key, value) VALUES ('DATABASE.LAYOUT.VERSION.MINOR', ?)",
            (str(layout_minor),),
        )
        con.commit()
        con.close()

    def test_incompatible_proj_db_is_dropped(self, tmp_path, monkeypatch):
        from resource.raster_resource import _ensure_proj_data_env

        self._make_projdb(tmp_path / "oldproj", 2)
        monkeypatch.setenv("PROJ_LIB", str(tmp_path / "oldproj"))
        monkeypatch.delenv("PROJ_DATA", raising=False)
        _ensure_proj_data_env()
        assert "PROJ_LIB" not in os.environ
        assert "PROJ_DATA" not in os.environ

    def test_compatible_proj_db_is_kept(self, tmp_path, monkeypatch):
        from resource.raster_resource import _ensure_proj_data_env

        self._make_projdb(tmp_path / "newproj", 6)
        monkeypatch.setenv("PROJ_LIB", str(tmp_path / "newproj"))
        monkeypatch.delenv("PROJ_DATA", raising=False)
        _ensure_proj_data_env()
        assert os.environ["PROJ_LIB"] == str(tmp_path / "newproj")

    def test_missing_proj_db_is_dropped(self, tmp_path, monkeypatch):
        from resource.raster_resource import _ensure_proj_data_env

        monkeypatch.setenv("PROJ_DATA", str(tmp_path / "empty"))
        monkeypatch.setenv("PROJ_LIB", str(tmp_path / "empty"))
        _ensure_proj_data_env()
        assert "PROJ_DATA" not in os.environ
        assert "PROJ_LIB" not in os.environ

    def test_no_override_is_left_alone(self, monkeypatch):
        from resource.raster_resource import _ensure_proj_data_env

        monkeypatch.delenv("PROJ_DATA", raising=False)
        monkeypatch.delenv("PROJ_LIB", raising=False)
        _ensure_proj_data_env()
        assert "PROJ_DATA" not in os.environ
        assert "PROJ_LIB" not in os.environ


class TestGenerateTilesCompatEndpoint:
    def test_generate_tiles_is_noop(self, client, auth_headers):
        resp = client.post("/api/raster/generate_tiles", json={"data_id": 1}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json() == {"status": True, "message": "dynamic tiles enabled"}

    def test_generate_tiles_requires_auth(self, client):
        resp = client.post("/api/raster/generate_tiles", json={"data_id": 1})
        assert resp.status_code in (401, 422)


class TestFloatTileRendering:
    """O2 regression: float rasters used to render as opaque black tiles —
    rio-tiler's PNG fallback rescales against the float64 dtype range, whose
    span overflows to +inf and maps every pixel to 0."""

    @pytest.fixture(scope="class")
    def float_geotiff(self, tmp_path_factory):
        path = tmp_path_factory.mktemp("tiles_float") / "geo_float.tif"
        rng = np.random.default_rng(7)
        data = (rng.random((3, 256, 256)) * 3000).astype("float64")
        data[:, :20, :20] = np.nan  # no-data corner
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=256,
            height=256,
            count=3,
            dtype="float64",
            crs="EPSG:4326",
            transform=from_bounds(*FIXTURE_BOUNDS, 256, 256),
        ) as dst:
            dst.write(data)
        return path

    def test_float_tile_is_rendered_not_black(self, client, db, auth_headers, float_geotiff, valid_tile):
        record = _make_raster(db, float_geotiff, name="float-src")
        resp = client.get(_tile_url(record.id, valid_tile), headers=auth_headers)
        assert resp.status_code == 200
        assert resp.data.startswith(PNG_SIGNATURE)
        arr = np.array(Image.open(io.BytesIO(resp.data)))
        assert arr[:, :, :3].max() > 0, "float tile rendered all-black despite valid data"
