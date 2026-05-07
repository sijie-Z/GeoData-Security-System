"""Tests for raster endpoints."""


class TestRaster:
    def test_raster_preview_requires_auth(self, client):
        resp = client.get('/api/raster/preview')
        assert resp.status_code in (401, 422)

    def test_raster_generate_requires_auth(self, client):
        resp = client.post('/api/generate_raster_watermark', json={'application_id': 1})
        assert resp.status_code in (401, 422)

    def test_crmark_embed_requires_auth(self, client):
        resp = client.post('/api/crmark/embed', json={})
        assert resp.status_code in (401, 422)

    def test_crmark_recover_requires_auth(self, client):
        resp = client.post('/api/crmark/recover', json={})
        assert resp.status_code in (401, 422)

    def test_crmark_decode_requires_auth(self, client):
        resp = client.post('/api/crmark/decode', json={})
        assert resp.status_code in (401, 422)

    def test_embed_dispatch_requires_auth(self, client):
        resp = client.post('/api/admin/embed_dispatch', json={})
        assert resp.status_code in (401, 422)

    def test_raster_applications_generate(self, client, auth_headers):
        resp = client.get('/api/adm1_get_raster_applications_generate_watermark', headers=auth_headers)
        assert resp.status_code == 200
