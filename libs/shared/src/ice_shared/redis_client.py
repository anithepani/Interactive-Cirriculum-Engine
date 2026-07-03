"""Redis client (cache + Celery broker/result handles)."""
from __future__ import annotations

from redis.asyncio import Redis, from_url

from ice_shared.settings import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(settings.redis.url, decode_responses=True)
    return _redis
