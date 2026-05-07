"""Tests for Prometheus metrics endpoint."""


class TestMetrics:
    def test_metrics_endpoint(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200
        assert 'text/plain' in resp.content_type

    def test_metrics_contains_request_counter(self, client):
        # Make a request first to generate some metrics
        client.get('/api/health')
        resp = client.get('/metrics')
        body = resp.data.decode()
        assert 'flask_request_total' in body
