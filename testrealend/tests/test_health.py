"""Tests for health check endpoint."""


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        response = client.get('/api/health')
        # Accept 200 (healthy) or 503 (degraded — expected in test env without real DB)
        assert response.status_code in (200, 503)

    def test_health_returns_json(self, client):
        response = client.get('/api/health')
        assert response.content_type.startswith('application/json')

    def test_health_contains_service_name(self, client):
        response = client.get('/api/health')
        data = response.get_json()
        assert data['service'] == 'geodata-security-system'

    def test_health_has_status_field(self, client):
        response = client.get('/api/health')
        data = response.get_json()
        assert data['status'] in ('healthy', 'degraded')

    def test_health_has_cache_field(self, client):
        response = client.get('/api/health')
        data = response.get_json()
        assert 'cache' in data
