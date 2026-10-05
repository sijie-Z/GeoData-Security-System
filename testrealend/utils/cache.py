"""In-memory caching layer for GET endpoint responses.

No external dependencies (Redis etc.) — sufficient for single-process
deployments and small-to-medium workloads.
"""

import hashlib
import json
import logging
import threading
import time
from functools import wraps

from flask import request

logger = logging.getLogger(__name__)

_cache = {}
_lock = threading.Lock()


def _get(key):
    with _lock:
        entry = _cache.get(key)
        if entry and entry[1] > time.time():
            return entry[0]
        if entry:
            del _cache[key]
    return None


def _set(key, value, timeout):
    with _lock:
        _cache[key] = (value, time.time() + timeout)
        # 超过 500 条淘汰最旧的
        if len(_cache) > 500:
            oldest = min(_cache, key=lambda k: _cache[k][1])
            del _cache[oldest]


def init_cache(app):
    """No-op — kept for API compatibility."""
    logger.info("In-memory cache ready (no Redis required)")


def get_redis():
    """No-op — kept for API compatibility."""
    return None


def is_cache_available():
    return True


def cache_key(*args, **kwargs):
    """Build a deterministic cache key from arguments."""
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def cached(timeout=300, key_prefix="cache"):
    """Decorator to cache GET endpoint responses in memory."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.method != "GET":
                return f(*args, **kwargs)

            from flask_jwt_extended import get_jwt_identity

            try:
                identity = get_jwt_identity()
                user_id = identity.get("number", "anon") if identity else "anon"
            except Exception:
                user_id = "anon"

            ckey = hashlib.md5(
                f"{key_prefix}:{f.__name__}:{user_id}:{request.full_path}".encode()
            ).hexdigest()

            cached_val = _get(ckey)
            if cached_val is not None:
                return cached_val

            result = f(*args, **kwargs)

            try:
                if isinstance(result, tuple) and len(result) >= 1:
                    _set(ckey, result[0], timeout)
            except Exception:
                pass

            return result

        return wrapper

    return decorator


def invalidate_prefix(prefix):
    """Invalidate all cache keys matching a prefix."""
    with _lock:
        for key in list(_cache.keys()):
            if key.startswith(prefix):
                del _cache[key]


def invalidate_all():
    """Flush all cached data."""
    with _lock:
        _cache.clear()
