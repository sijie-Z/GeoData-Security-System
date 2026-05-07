"""Tests for employee profile endpoints."""


class TestEmployeeProfile:
    def test_get_profile_requires_auth(self, client):
        resp = client.get('/api/employee/profile')
        assert resp.status_code in (401, 422)

    def test_get_profile(self, client, employee_headers):
        resp = client.get('/api/employee/profile', headers=employee_headers)
        assert resp.status_code in (200, 404)

    def test_update_profile_requires_auth(self, client):
        resp = client.put('/api/employee/profile', json={'name': 'Test'})
        assert resp.status_code in (401, 422)

    def test_change_password_requires_auth(self, client):
        resp = client.put('/api/employee/password', json={'old': 'a', 'new': 'b'})
        assert resp.status_code in (401, 422)

    def test_change_password_missing_fields(self, client, employee_headers):
        resp = client.put('/api/employee/password', headers=employee_headers, json={})
        assert resp.status_code in (400, 422)

    def test_photo_requires_auth(self, client):
        resp = client.get('/api/employee/photo/E001')
        assert resp.status_code in (401, 422, 404)
