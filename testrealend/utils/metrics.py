"""Prometheus metrics for request tracking and business KPIs."""

import time
import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    )
    _has_prometheus = True
except (ImportError, AttributeError, Exception) as _prom_err:
    _has_prometheus = False
    Counter = Histogram = Gauge = Info = None
    logger.warning(f"prometheus_client unavailable ({_prom_err}), metrics disabled")


# ── Request metrics ──────────────────────────────────────────────
if _has_prometheus:
    REQUEST_COUNT = Counter(
        'flask_request_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    REQUEST_LATENCY = Histogram(
        'flask_request_duration_seconds',
        'Request latency in seconds',
        ['method', 'endpoint'],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    REQUEST_IN_PROGRESS = Gauge(
        'flask_requests_in_progress',
        'Number of requests currently being processed',
        ['method', 'endpoint']
    )

    # ── Business metrics ─────────────────────────────────────────────
    APPLICATIONS_TOTAL = Counter(
        'geodata_applications_total',
        'Total data applications submitted',
        ['data_type']
    )
    APPROVALS_TOTAL = Counter(
        'geodata_approvals_total',
        'Total approvals/rejections',
        ['result', 'level']
    )
    DOWNLOADS_TOTAL = Counter(
        'geodata_downloads_total',
        'Total file downloads'
    )
    ACTIVE_USERS = Gauge(
        'geodata_active_users',
        'Currently active users'
    )
    DB_ERRORS = Counter(
        'geodata_db_errors_total',
        'Database errors encountered'
    )
    CACHE_HITS = Counter(
        'geodata_cache_hits_total',
        'Cache hit/miss count',
        ['result']
    )
    WATERMARKS_GENERATED = Counter(
        'geodata_watermarks_generated_total',
        'Watermarks generated',
        ['data_type']
    )

    APP_INFO = Info(
        'geodata_app',
        'Application metadata'
    )
    APP_INFO.info({
        'version': '1.0.0',
        'service': 'geodata-security-system'
    })


def setup_metrics(app):
    """Register Prometheus metrics middleware on the Flask app."""
    if not _has_prometheus:
        return

    @app.before_request
    def before_request():
        from flask import request as req
        request._start_time = time.time()
        REQUEST_IN_PROGRESS.labels(method=req.method, endpoint=req.path).inc()

    @app.after_request
    def after_request(response):
        from flask import request as req
        if hasattr(req, '_start_time'):
            latency = time.time() - req._start_time
            REQUEST_LATENCY.labels(method=req.method, endpoint=req.path).observe(latency)
        REQUEST_COUNT.labels(
            method=req.method,
            endpoint=req.path,
            status=response.status_code
        ).inc()
        REQUEST_IN_PROGRESS.labels(method=req.method, endpoint=req.path).dec()
        return response

    @app.route('/metrics')
    def metrics():
        from flask import Response
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


def record_application(data_type='unknown'):
    if _has_prometheus:
        APPLICATIONS_TOTAL.labels(data_type=data_type).inc()


def record_approval(result='approved', level='adm1'):
    if _has_prometheus:
        APPROVALS_TOTAL.labels(result=result, level=level).inc()


def record_download():
    if _has_prometheus:
        DOWNLOADS_TOTAL.inc()


def record_cache_hit(hit=True):
    if _has_prometheus:
        CACHE_HITS.labels(result='hit' if hit else 'miss').inc()


def record_watermark(data_type='vector'):
    if _has_prometheus:
        WATERMARKS_GENERATED.labels(data_type=data_type).inc()


def record_db_error():
    if _has_prometheus:
        DB_ERRORS.inc()
