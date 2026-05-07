import pytest


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get('/api/health')
        data = response.get_json()
        assert 'status' in data
        assert 'service' in data

    def test_health_service_name(self, client):
        response = client.get('/api/health')
        data = response.get_json()
        assert data['service'] == 'geodata-security-system'
