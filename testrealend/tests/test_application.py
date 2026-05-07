import pytest


class TestApplicationSubmission:
    """Tests for application submission."""

    def test_submit_requires_auth(self, client):
        response = client.post('/api/submit_application', json={
            'data_id': 1,
            'data_name': 'Test Data',
            'data_alias': 'test',
            'applicant_name': 'Test User',
            'applicant_user_number': '12345'
        })
        assert response.status_code == 401

    def test_submit_missing_required_fields(self, client, auth_headers):
        if not auth_headers:
            pytest.skip('No auth headers available')
        response = client.post('/api/submit_application',
                               json={},
                               headers=auth_headers)
        # Should fail due to missing fields
        assert response.status_code in [400, 500]


class TestApplicationApproval:
    """Tests for application approval workflow."""

    def test_approve_requires_auth(self, client):
        response = client.post('/api/adm1_pass', json={'id': 1})
        assert response.status_code == 401

    def test_approve_nonexistent_application(self, client, auth_headers):
        if not auth_headers:
            pytest.skip('No auth headers available')
        response = client.post('/api/adm1_pass',
                               json={'id': 999999},
                               headers=auth_headers)
        assert response.status_code == 404
