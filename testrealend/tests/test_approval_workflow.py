"""Tests for the full application approval workflow."""


class TestApprovalWorkflow:
    def test_adm1_pending_list(self, client, auth_headers):
        resp = client.get('/api/adm1_get_applications', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'application_data' in data

    def test_adm1_shp_applications(self, client, auth_headers):
        resp = client.get('/api/adm1_get_shp_applications', headers=auth_headers)
        assert resp.status_code == 200

    def test_adm1_raster_applications(self, client, auth_headers):
        resp = client.get('/api/adm1_get_raster_applications', headers=auth_headers)
        assert resp.status_code == 200

    def test_adm2_approved_list(self, client, adm2_headers):
        resp = client.get('/api/adm2_get_approved', headers=adm2_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'approved_application_data' in data

    def test_adm1_pass_nonexistent(self, client, auth_headers):
        resp = client.post('/api/adm1_pass', headers=auth_headers, json={
            'id': 99999, 'user_name': 'Admin', 'user_number': 'admin1'
        })
        assert resp.status_code in (404, 400)

    def test_adm1_fail_nonexistent(self, client, auth_headers):
        resp = client.post('/api/adm1_fail', headers=auth_headers, json={
            'id': 99999, 'user_name': 'Admin', 'user_number': 'admin1'
        })
        assert resp.status_code in (404, 400)

    def test_adm2_pass_nonexistent(self, client, adm2_headers):
        resp = client.post('/api/adm2_pass', headers=adm2_headers, json={
            'id': 99999, 'user_name': 'Admin', 'user_number': 'admin2'
        })
        assert resp.status_code in (404, 400)

    def test_adm2_fail_nonexistent(self, client, adm2_headers):
        resp = client.post('/api/adm2_fail', headers=adm2_headers, json={
            'id': 99999, 'user_name': 'Admin', 'user_number': 'admin2'
        })
        assert resp.status_code in (404, 400)

    def test_batch_review_requires_auth(self, client):
        resp = client.post('/api/admin/batch_review', json={})
        assert resp.status_code in (401, 422)

    def test_all_applications(self, client, auth_headers):
        resp = client.get('/api/applications', headers=auth_headers)
        assert resp.status_code == 200
