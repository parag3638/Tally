"""Read-only query execution for the text-to-SQL agent.

Runs guard-sanitized SELECTs in a READ ONLY transaction with a bounded
``statement_timeout`` and a per-transaction ``app.current_user_id`` GUC that
scopes the ``my_expenses`` view to the caller. Uses a small dedicated pool
against ``readonly_database_url`` (a real read-only Postgres role in production).
"""

from __future__ import annotations

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from src.agents.sql_agent.sql_guard import sanitize
from src.core.config import settings

_ro_pool: ThreadedConnectionPool | None = None


def _pool() -> ThreadedConnectionPool:
    global _ro_pool
    if _ro_pool is None:
        _ro_pool = ThreadedConnectionPool(1, 5, dsn=settings.readonly_database_url)
    return _ro_pool


def close_readonly_pool() -> None:
    global _ro_pool
    if _ro_pool is not None:
        _ro_pool.closeall()
        _ro_pool = None


def run_readonly(query: str, user_id: int, *, timeout_ms: int = 5000) -> list[dict]:
    safe_sql = sanitize(query)
    pool = _pool()
    conn = pool.getconn()
    try:
        conn.set_session(readonly=True, autocommit=False)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SET LOCAL statement_timeout = %s", (timeout_ms,))
        cur.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
        cur.execute(safe_sql)
        rows = cur.fetchall()
        cur.close()
        conn.rollback()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
