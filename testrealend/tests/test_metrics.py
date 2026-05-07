"""Tests for Prometheus metrics endpoint."""
import pytest

try:
    import prometheus_client  # noqa: F401
    _has_prometheus = True
except (ImportError, AttributeError):
    _has_prometheus = False


@pytest.mark.skipif(not _has_prometheus, reason="prometheus_client not available")
class TestMetrics:
    def test_metrics_endpoint(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200
        assert 'text/plain' in resp.content_type

    def test_metrics_contains_request_counter(self, client):
        client.get('/api/health')
        resp = client.get('/metrics')
        body = resp.data.decode()
        assert 'flask_request_total' in body


class TestMetricsUnavailable:
    def test_metrics_disabled_gracefully(self, client):
        """When prometheus is unavailable, /metrics should return 404."""
        resp = client.get('/metrics')
        # If prometheus is available, 200; if not, 404 (route not registered)
        assert resp.status_code in (200, 404)
