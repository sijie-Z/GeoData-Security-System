"""Redis caching layer with graceful fallback to no-op when Redis is unavailable."""

import json
import hashlib
import logging
from functools import wraps
from flask import request

logger = logging.getLogger(__name__)

_redis_client = None
_cache_available = False


def init_cache(app):
    """Initialize Redis connection from app config."""
    global _redis_client, _cache_available
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        _cache_available = True
        logger.info(f"Redis connected: {redis_url}")
    except Exception as e:
        _cache_available = False
        _redis_client = None
        logger.warning(f"Redis unavailable ({e}), caching disabled")


def get_redis():
    """Get the Redis client (may be None)."""
    return _redis_client


def is_cache_available():
    return _cache_available


def cache_key(*args, **kwargs):
    """Build a deterministic cache key from arguments."""
    raw = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def cached(timeout=300, key_prefix='cache'):
    """Decorator to cache GET endpoint responses in Redis.

    Falls through to the original function if Redis is unavailable.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not _cache_available or request.method != 'GET':
                return f(*args, **kwargs)

            # Build cache key from endpoint + query params + user identity
            from flask_jwt_extended import get_jwt_identity
            try:
                identity = get_jwt_identity()
                user_id = identity.get('number', 'anon') if identity else 'anon'
            except Exception:
                user_id = 'anon'

            ckey = f"{key_prefix}:{f.__name__}:{user_id}:{request.full_path}"
            ckey = hashlib.md5(ckey.encode()).hexdigest()

            try:
                cached_val = _redis_client.get(ckey)
                if cached_val:
                    return json.loads(cached_val)
            except Exception:
                pass

            result = f(*args, **kwargs)

            try:
                # result is (body, status_code) tuple
                if isinstance(result, tuple) and len(result) >= 1:
                    _redis_client.setex(ckey, timeout, json.dumps(result[0], default=str))
            except Exception:
                pass

            return result
        return wrapper
    return decorator


def invalidate_prefix(prefix):
    """Invalidate all cache keys matching a prefix."""
    if not _cache_available:
        return
    try:
        pattern = f"{prefix}:*"
        for key in _redis_client.scan_iter(match=pattern, count=100):
            _redis_client.delete(key)
    except Exception:
        pass


def invalidate_all():
    """Flush all cached data (use sparingly)."""
    if not _cache_available:
        return
    try:
        _redis_client.flushdb()
    except Exception:
        pass
