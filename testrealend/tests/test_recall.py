"""Tests for recall proposal endpoints."""


class TestRecallProposals:
    def test_list_requires_auth(self, client):
        resp = client.get('/api/recall/list')
        assert resp.status_code in (401, 422)

    def test_list_recalls(self, client, auth_headers):
        resp = client.get('/api/recall/list', headers=auth_headers)
        assert resp.status_code == 200

    def test_create_recall_requires_auth(self, client):
        resp = client.post('/api/recall/create', json={'application_id': 1, 'reason': 'test'})
        assert resp.status_code in (401, 422)

    def test_create_recall_missing_fields(self, client, auth_headers):
        resp = client.post('/api/recall/create', headers=auth_headers, json={})
        assert resp.status_code in (400, 404, 422)

    def test_vote_requires_auth(self, client):
        resp = client.post('/api/recall/1/vote', json={'vote': 'agree'})
        assert resp.status_code in (401, 422)

    def test_detail_requires_auth(self, client):
        resp = client.get('/api/recall/1')
        assert resp.status_code in (401, 422)

    def test_nonexistent_recall(self, client, auth_headers):
        resp = client.get('/api/recall/99999', headers=auth_headers)
        assert resp.status_code in (404, 200)
