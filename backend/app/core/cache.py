"""Redis access for caching upstream market data.

The cache is an optimisation, never a dependency: every failure here is logged and
swallowed so a missing or broken Redis degrades to hitting the provider directly.
"""

import logging

from redis.asyncio import Redis

from app.core.config import get_settings


logger = logging.getLogger(__name__)

_client: Redis | None = None
_initialised = False


def get_redis() -> Redis | None:
    """The shared client, or None when no redis_url is configured."""
    global _client, _initialised
    if not _initialised:
        _initialised = True
        settings = get_settings()
        if settings.redis_url:
            _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def reset_redis() -> None:
    """Drop the memoised client. Used by tests."""
    global _client, _initialised
    _client = None
    _initialised = False


async def cache_get(client: Redis | None, key: str) -> str | None:
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception:
        logger.warning("cache read failed", exc_info=True, extra={"cache_key": key})
        return None


async def cache_set(client: Redis | None, key: str, value: str, ttl_seconds: int) -> None:
    if client is None:
        return
    try:
        await client.setex(key, ttl_seconds, value)
    except Exception:
        logger.warning("cache write failed", exc_info=True, extra={"cache_key": key})
