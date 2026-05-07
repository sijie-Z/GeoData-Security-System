"""Per-user rate limiting based on JWT identity.

Uses Redis when available (for production clustering), falls back to in-memory.
"""

import logging
import time
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger(__name__)

# In-memory fallback store
_user_counts = {}
_cleanup_counter = 0

_redis_client = None


def init_user_limiter(app):
    """Initialize with Redis client if available."""
    global _redis_client
    try:
        from utils.cache import get_redis
        _redis_client = get_redis()
        if _redis_client:
            logger.info("Per-user rate limiter using Redis backend")
    except Exception:
        pass


def _get_user_key():
    """Extract a rate-limit key from the current JWT identity."""
    try:
        identity = get_jwt_identity()
        if identity:
            return f"ratelimit:user:{identity.get('number', 'unknown')}"
    except Exception:
        pass
    return f"ratelimit:ip:{request.remote_addr}"


def _check_rate_redis(key, max_requests, window):
    """Check rate limit using Redis sliding window."""
    now = time.time()
    pipe = _redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zcard(key)
    pipe.zadd(key, {f"{now}": now})
    pipe.expire(key, window + 1)
    results = pipe.execute()
    current_count = results[1]
    if current_count >= max_requests:
        retry_after = int(window - (now - _redis_client.zrange(key, 0, 0, withscores=True)[0][1]))
        return False, retry_after
    return True, 0


def _check_rate_memory(key, max_requests, window):
    """Check rate limit using in-memory store."""
    global _cleanup_counter
    now = time.time()

    if key not in _user_counts:
        _user_counts[key] = []

    _user_counts[key] = [t for t in _user_counts[key] if t > now - window]

    if len(_user_counts[key]) >= max_requests:
        retry_after = int(window - (now - _user_counts[key][0]))
        return False, retry_after

    _user_counts[key].append(now)

    _cleanup_counter += 1
    if _cleanup_counter > 1000:
        _cleanup_counter = 0
        cutoff = now - window * 2
        stale = [k for k, v in _user_counts.items() if not v or v[-1] < cutoff]
        for k in stale:
            del _user_counts[k]

    return True, 0


def user_rate_limit(max_requests=60, window=60, per_user=True):
    """Decorator for per-user rate limiting.

    Args:
        max_requests: Maximum requests allowed in the window.
        window: Time window in seconds.
        per_user: If True, limit per JWT user; if False, per IP.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = _get_user_key() if per_user else f"ratelimit:ip:{request.remote_addr}"

            if _redis_client:
                allowed, retry_after = _check_rate_redis(key, max_requests, window)
            else:
                allowed, retry_after = _check_rate_memory(key, max_requests, window)

            if not allowed:
                return jsonify({
                    'status': False,
                    'msg': f'请求过于频繁，请{retry_after}秒后重试',
                    'retry_after': retry_after
                }), 429

            return f(*args, **kwargs)
        return wrapper
    return decorator


# Pre-configured limiters
strict_limit = lambda f: user_rate_limit(max_requests=10, window=60)(f)
normal_limit = lambda f: user_rate_limit(max_requests=60, window=60)(f)
relaxed_limit = lambda f: user_rate_limit(max_requests=200, window=60)(f)
