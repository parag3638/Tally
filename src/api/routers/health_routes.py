"""Liveness and readiness probes (used by Docker healthchecks)."""

from __future__ import annotations

from fastapi import APIRouter

from src.db.session import get_cursor

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness — process is up. No external dependencies checked."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    """Readiness — can we reach the database (and, later, Redis)?"""
    checks: dict[str, str] = {}
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    try:
        import redis

        from src.core.config import settings

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        client.close()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    ready = all(v == "ok" for v in checks.values())
    return {"ready": ready, "checks": checks}
