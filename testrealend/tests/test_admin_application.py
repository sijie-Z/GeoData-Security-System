"""Tests for admin application (promotion request) endpoints."""


class TestAdminApplication:
    def test_eligibility_requires_auth(self, client):
        resp = client.get('/api/admin-application/eligibility')
        assert resp.status_code in (401, 422)

    def test_submit_requires_auth(self, client):
        resp = client.post('/api/admin-application/submit', json={'reason': 'test'})
        assert resp.status_code in (401, 422)

    def test_list_requires_auth(self, client):
        resp = client.get('/api/admin-application/list')
        assert resp.status_code in (401, 422)

    def test_list_applications(self, client, auth_headers):
        resp = client.get('/api/admin-application/list', headers=auth_headers)
        assert resp.status_code == 200

    def test_my_applications_requires_auth(self, client):
        resp = client.get('/api/admin-application/my')
        assert resp.status_code in (401, 422)

    def test_nonexistent_detail(self, client, auth_headers):
        resp = client.get('/api/admin-application/99999', headers=auth_headers)
        assert resp.status_code in (404, 200)

    def test_vote_requires_auth(self, client):
        resp = client.post('/api/admin-application/1/vote', json={'vote': 'agree'})
        assert resp.status_code in (401, 422)
