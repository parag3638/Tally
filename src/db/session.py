"""Connection / cursor lifecycle helpers.

``get_conn()`` checks a connection out of the pool, commits on success, rolls
back on exception, and always returns the connection. Repositories receive a
cursor and never own the connection lifecycle — this lets a single service
method run several repositories inside one atomic transaction.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from src.db.pool import get_pool


@contextmanager
def get_conn() -> Iterator[PgConnection]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor() -> Iterator[RealDictCursor]:
    """Convenience wrapper yielding a dict-returning cursor inside a transaction."""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cur
        finally:
            cur.close()
