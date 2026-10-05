"""Tests for the raster tile serving endpoint.

GET /api/raster_tiles/<data_id>/<z>/<x>/<y>.png must serve tiles from the
same nested layout that generate_raster_tiles writes:
<UPLOAD_FOLDER>/tiles/<data_id>/<z>/<x>/<y>.png
"""


class TestRasterTiles:
    def _write_fake_tile(self, root, data_id, z, x, y, payload=b"\x89PNG\r\n\x1a\nfake-tile"):
        tile_dir = root / "tiles" / str(data_id) / str(z) / str(x)
        tile_dir.mkdir(parents=True, exist_ok=True)
        tile_file = tile_dir / f"{y}.png"
        tile_file.write_bytes(payload)
        return tile_file

    def test_get_tile_serves_nested_path(self, client, app, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))
        payload = b"\x89PNG\r\n\x1a\nfake-tile"
        self._write_fake_tile(tmp_path, 7, 2, 3, 5, payload)

        resp = client.get("/api/raster_tiles/7/2/3/5.png", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.mimetype == "image/png"
        assert resp.data == payload

    def test_get_tile_missing_returns_404(self, client, app, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))

        resp = client.get("/api/raster_tiles/7/2/3/5.png", headers=auth_headers)

        assert resp.status_code == 404
