"""Prometheus metrics for request tracking and business KPIs."""

import logging
import sys
import time
import types

logger = logging.getLogger(__name__)

# On Windows, the local `resource/` package shadows the Unix built-in.
# prometheus_client needs `resource.getpagesize`; temporarily provide a stub
# so it imports cleanly, then restore the local package.
_original_resource = sys.modules.get("resource")
try:
    _stub_resource = types.ModuleType("resource")
    _stub_resource.getpagesize = lambda: 4096
    sys.modules["resource"] = _stub_resource

    # On Windows, PlatformCollector.__init__ calls platform.uname() which triggers
    # a WMI query that can hang indefinitely. Pre-register a stub so the real
    # platform_collector module body never executes.
    # prometheus_client does: from .platform_collector import PLATFORM_COLLECTOR, PlatformCollector
    _pc_stub = types.ModuleType("prometheus_client.platform_collector")
    _pc_stub.PLATFORM_COLLECTOR = None
    _pc_stub.PlatformCollector = type("PlatformCollector", (), {})
    sys.modules["prometheus_client.platform_collector"] = _pc_stub

    from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Gauge, Histogram, Info, generate_latest

    _has_prometheus = True
except (ImportError, Exception) as _prom_err:
    _has_prometheus = False
    Counter = Histogram = Gauge = Info = None
    logger.warning(f"prometheus_client unavailable ({_prom_err}), metrics disabled")
finally:
    # Restore the original `resource` module/package
    if _original_resource is not None:
        sys.modules["resource"] = _original_resource
    elif "resource" in sys.modules:
        del sys.modules["resource"]
    # Clean up the platform_collector stub so subsequent imports get the real module
    sys.modules.pop("prometheus_client.platform_collector", None)


# ── Request metrics ──────────────────────────────────────────────
if _has_prometheus:
    REQUEST_COUNT = Counter("flask_request_total", "Total HTTP requests", ["method", "endpoint", "status"])
    REQUEST_LATENCY = Histogram(
        "flask_request_duration_seconds",
        "Request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    REQUEST_IN_PROGRESS = Gauge(
        "flask_requests_in_progress", "Number of requests currently being processed", ["method", "endpoint"]
    )

    # ── Business metrics ─────────────────────────────────────────────
    APPLICATIONS_TOTAL = Counter("geodata_applications_total", "Total data applications submitted", ["data_type"])
    APPROVALS_TOTAL = Counter("geodata_approvals_total", "Total approvals/rejections", ["result", "level"])
    DOWNLOADS_TOTAL = Counter("geodata_downloads_total", "Total file downloads")
    ACTIVE_USERS = Gauge("geodata_active_users", "Currently active users")
    DB_ERRORS = Counter("geodata_db_errors_total", "Database errors encountered")
    CACHE_HITS = Counter("geodata_cache_hits_total", "Cache hit/miss count", ["result"])
    WATERMARKS_GENERATED = Counter("geodata_watermarks_generated_total", "Watermarks generated", ["data_type"])

    APP_INFO = Info("geodata_app", "Application metadata")
    APP_INFO.info({"version": "1.0.0", "service": "geodata-security-system"})


def setup_metrics(app):
    """Register Prometheus metrics middleware on the Flask app."""
    if not _has_prometheus:
        return

    @app.before_request
    def before_request():
        from flask import request as req

        req._start_time = time.time()
        REQUEST_IN_PROGRESS.labels(method=req.method, endpoint=req.path).inc()

    @app.after_request
    def after_request(response):
        from flask import request as req

        if hasattr(req, "_start_time"):
            latency = time.time() - req._start_time
            REQUEST_LATENCY.labels(method=req.method, endpoint=req.path).observe(latency)
        REQUEST_COUNT.labels(method=req.method, endpoint=req.path, status=response.status_code).inc()
        REQUEST_IN_PROGRESS.labels(method=req.method, endpoint=req.path).dec()
        return response

    @app.route("/metrics")
    def metrics():
        from flask import Response

        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


def record_application(data_type="unknown"):
    if _has_prometheus:
        APPLICATIONS_TOTAL.labels(data_type=data_type).inc()


def record_approval(result="approved", level="adm1"):
    if _has_prometheus:
        APPROVALS_TOTAL.labels(result=result, level=level).inc()


def record_download():
    if _has_prometheus:
        DOWNLOADS_TOTAL.inc()


def record_cache_hit(hit=True):
    if _has_prometheus:
        CACHE_HITS.labels(result="hit" if hit else "miss").inc()


def record_watermark(data_type="vector"):
    if _has_prometheus:
        WATERMARKS_GENERATED.labels(data_type=data_type).inc()


def record_db_error():
    if _has_prometheus:
        DB_ERRORS.inc()
