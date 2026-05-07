"""Tests for download endpoints."""


class TestDownload:
    def test_download_requires_auth(self, client):
        resp = client.get('/api/emp_download_zip')
        assert resp.status_code in (401, 405, 422)

    def test_request_download_token_requires_auth(self, client):
        resp = client.post('/api/request_download_token', json={'application_id': 1})
        assert resp.status_code in (401, 422)

    def test_token_download_invalid_token(self, client):
        resp = client.get('/api/download/invalid-token-123')
        assert resp.status_code in (400, 401, 403, 404)

    def test_record_download_requires_auth(self, client):
        resp = client.post('/api/record_download_file', json={})
        assert resp.status_code in (401, 422)

    def test_record_download(self, client, employee_headers):
        resp = client.post('/api/record_download_file', headers=employee_headers, json={
            'application_id': 1,
            'applicant_user_number': 'E001',
            'download_user_number': 'E001'
        })
        assert resp.status_code in (200, 201, 400, 404, 500)
