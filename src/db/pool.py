"""psycopg2 connection pool — the production-safe replacement for the old
single global ``conn``/``cursor`` shared across every request.

FastAPI runs sync route handlers in a threadpool, so a ``ThreadedConnectionPool``
is the correct primitive. The pool is created at application startup (lifespan)
and closed at shutdown.
"""

from __future__ import annotations

from psycopg2.pool import ThreadedConnectionPool

from src.core.config import settings
from src.core.logging import get_logger

log = get_logger(__name__)

_pool: ThreadedConnectionPool | None = None


def init_pool() -> ThreadedConnectionPool:
    """Create the global pool. Idempotent."""
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            minconn=settings.db_pool_min,
            maxconn=settings.db_pool_max,
            dsn=settings.database_url,
        )
        log.info("db.pool.initialized", minconn=settings.db_pool_min, maxconn=settings.db_pool_max)
    return _pool


def get_pool() -> ThreadedConnectionPool:
    if _pool is None:
        return init_pool()
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        log.info("db.pool.closed")
