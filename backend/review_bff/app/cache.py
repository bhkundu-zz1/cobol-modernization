"""Redis TTL cache wrapper for the Review BFF (architecture.md section 9.1).

Explicit deferred tradeoff (docs/deferred_scope.md): this is a simple TTL
cache, not `_changes`-feed-driven invalidation. A reviewer approving an
item may see stale review-queue state on another client for up to
CACHE_TTL_SECONDS — acceptable for this pass, called out rather than
silently dropped. invalidate() is called explicitly after a decision write
so the *same* client sees its own change immediately even before the TTL
expires.
"""

import json
from typing import Any

import redis

from .config import settings


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        db=settings.redis_db_cache,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )


def get_cached(client: redis.Redis, key: str) -> Any | None:
    try:
        raw = client.get(key)
    except redis.RedisError:
        return None
    return json.loads(raw) if raw is not None else None


def set_cached(client: redis.Redis, key: str, value: Any, ttl_seconds: int | None = None) -> None:
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds or settings.cache_ttl_seconds)
    except redis.RedisError:
        pass  # cache is a performance optimization, not a correctness dependency


def invalidate(client: redis.Redis, key_prefix: str) -> None:
    try:
        for key in client.scan_iter(match=f"{key_prefix}*"):
            client.delete(key)
    except redis.RedisError:
        pass
