"""psycopg3 connection pool dedicated to the LangGraph Postgres checkpointer.

The app's repositories use psycopg2 (per project decision). LangGraph's
``PostgresSaver`` is built on **psycopg3** and needs ``autocommit=True`` with a
``dict_row`` row factory. Rather than force one driver to do both jobs, we run a
small dedicated psycopg3 pool here against the *same* database. The two drivers
coexist cleanly.

``get_checkpointer()`` returns a process-wide ``PostgresSaver`` and runs its
idempotent ``setup()`` once (creates the checkpoint tables).
"""

from __future__ import annotations

from psycopg_pool import ConnectionPool

from src.core.config import settings
from src.core.logging import get_logger

log = get_logger(__name__)

_pool: ConnectionPool | None = None
_checkpointer = None
_setup_done = False


def _connection_kwargs() -> dict:
    # PostgresSaver requires autocommit; dict_row makes rows behave like mappings.
    from psycopg.rows import dict_row

    return {"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}


def get_checkpoint_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=max(2, settings.db_pool_max // 2),
            kwargs=_connection_kwargs(),
            open=True,
        )
        log.info("checkpoint.pool.initialized")
    return _pool


def get_checkpointer():
    """Return the shared PostgresSaver, running setup() once."""
    global _checkpointer, _setup_done
    from langgraph.checkpoint.postgres import PostgresSaver

    if _checkpointer is None:
        _checkpointer = PostgresSaver(get_checkpoint_pool())
    if not _setup_done:
        _checkpointer.setup()
        _setup_done = True
        log.info("checkpoint.setup.done")
    return _checkpointer


def close_checkpoint_pool() -> None:
    global _pool, _checkpointer, _setup_done
    if _pool is not None:
        _pool.close()
        _pool = None
        _checkpointer = None
        _setup_done = False
        log.info("checkpoint.pool.closed")
