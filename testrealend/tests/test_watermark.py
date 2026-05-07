"""Tests for watermark endpoints."""


class TestWatermarkGeneration:
    def test_requires_auth(self, client):
        resp = client.post('/api/generate_watermark', json={'application_id': 1})
        assert resp.status_code in (401, 422)

    def test_missing_application(self, client, auth_headers):
        resp = client.post('/api/generate_watermark', headers=auth_headers, json={
            'application_id': 99999
        })
        assert resp.status_code in (404, 400)

    def test_get_generate_applications(self, client, auth_headers):
        resp = client.get('/api/adm1_get_applications_generate_watermark', headers=auth_headers)
        assert resp.status_code == 200


class TestWatermarkEmbedding:
    def test_requires_auth(self, client):
        resp = client.post('/api/embedding_watermark', json={'application_id': 1})
        assert resp.status_code in (401, 422)

    def test_get_embedding_applications(self, client, auth_headers):
        resp = client.get('/api/adm2_embedding_watermark_applications', headers=auth_headers)
        assert resp.status_code == 200


class TestVectorExtract:
    def test_requires_auth(self, client):
        resp = client.post('/api/vector/extract')
        assert resp.status_code in (401, 422)

    def test_missing_fields(self, client, auth_headers):
        resp = client.post('/api/vector/extract', headers=auth_headers)
        assert resp.status_code in (400, 422)
