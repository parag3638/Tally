"""ARQ (Redis) queue helpers shared by the API (enqueue) and worker (consume)."""

from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings

from src.core.config import settings

_pool = None


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def get_arq_pool():
    """Lazily create the shared ARQ Redis pool used to enqueue jobs."""
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
