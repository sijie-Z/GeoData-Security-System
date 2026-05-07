"""Per-user rate limiting based on JWT identity (not just IP)."""

import logging
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger(__name__)

# In-memory store for per-user request counts (use Redis in production cluster)
_user_counts = {}
_cleanup_counter = 0


def _get_user_key():
    """Extract a rate-limit key from the current JWT identity."""
    try:
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity.get('number', 'unknown')}"
    except Exception:
        pass
    return f"ip:{request.remote_addr}"


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
            global _cleanup_counter
            import time

            key = _get_user_key() if per_user else f"ip:{request.remote_addr}"
            now = time.time()

            if key not in _user_counts:
                _user_counts[key] = []

            # Clean old entries
            _user_counts[key] = [t for t in _user_counts[key] if t > now - window]

            if len(_user_counts[key]) >= max_requests:
                retry_after = int(window - (now - _user_counts[key][0]))
                return jsonify({
                    'status': False,
                    'msg': f'请求过于频繁，请{retry_after}秒后重试',
                    'retry_after': retry_after
                }), 429

            _user_counts[key].append(now)

            # Periodic cleanup of stale keys
            _cleanup_counter += 1
            if _cleanup_counter > 1000:
                _cleanup_counter = 0
                cutoff = now - window * 2
                stale = [k for k, v in _user_counts.items() if not v or v[-1] < cutoff]
                for k in stale:
                    del _user_counts[k]

            return f(*args, **kwargs)
        return wrapper
    return decorator


# Pre-configured limiters for common use cases
strict_limit = lambda f: user_rate_limit(max_requests=10, window=60)(f)
normal_limit = lambda f: user_rate_limit(max_requests=60, window=60)(f)
relaxed_limit = lambda f: user_rate_limit(max_requests=200, window=60)(f)
