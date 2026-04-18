"""Redis-backed caching layer for production use."""

import json
import hashlib
import logging
from typing import Any
from functools import wraps

import redis.asyncio as aioredis
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def cache_get(key: str) -> Any | None:
    try:
        r = await get_redis()
        val = await r.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Cache GET failed for {key}: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = 300):
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache SET failed for {key}: {e}")


async def cache_delete(key: str):
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as e:
        logger.warning(f"Cache DELETE failed for {key}: {e}")


async def cache_delete_pattern(pattern: str):
    try:
        r = await get_redis()
        async for key in r.scan_iter(match=pattern):
            await r.delete(key)
    except Exception as e:
        logger.warning(f"Cache DELETE pattern failed for {pattern}: {e}")


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a deterministic cache key from arguments."""
    parts = [prefix] + [str(a) for a in args]
    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}={v}")
    raw = ":".join(parts)
    return f"meddiagnose:{hashlib.md5(raw.encode()).hexdigest()}"


# OAuth state storage (Redis-backed for production; in-memory fallback when Redis unavailable)
_oauth_fallback: dict[str, dict] = {}
OAUTH_STATE_TTL = 600  # 10 minutes


async def oauth_state_set(state: str, data: dict) -> bool:
    """Store OAuth state. Uses Redis when available, else in-memory fallback."""
    try:
        r = await get_redis()
        key = f"meddiagnose:oauth:{state}"
        await r.setex(key, OAUTH_STATE_TTL, json.dumps(data, default=str))
        return True
    except Exception as e:
        logger.warning(f"OAuth state Redis set failed, using fallback: {e}")
        _oauth_fallback[state] = data
        return True


async def oauth_state_get(state: str) -> dict | None:
    """Get and remove OAuth state. Uses Redis when available."""
    try:
        r = await get_redis()
        key = f"meddiagnose:oauth:{state}"
        val = await r.get(key)
        if val:
            await r.delete(key)
            return json.loads(val)
    except Exception as e:
        logger.warning(f"OAuth state Redis get failed, using fallback: {e}")
    return _oauth_fallback.pop(state, None)
