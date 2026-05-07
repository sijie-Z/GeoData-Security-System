"""Tests for data upload endpoints."""


class TestUpload:
    def test_shp_upload_requires_auth(self, client):
        resp = client.post('/api/upload_shp_data')
        assert resp.status_code in (401, 422)

    def test_raster_upload_requires_auth(self, client):
        resp = client.post('/api/upload_raster_data')
        assert resp.status_code in (401, 422)

    def test_shp_upload_no_file(self, client, auth_headers):
        resp = client.post('/api/upload_shp_data', headers=auth_headers)
        assert resp.status_code in (400, 422)

    def test_raster_upload_no_file(self, client, auth_headers):
        resp = client.post('/api/upload_raster_data', headers=auth_headers)
        assert resp.status_code in (400, 422)
