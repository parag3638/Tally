"""FastAPI application entrypoint.

Replaces the old ``src/api/run_api.py``. Owns the application lifespan: opens the
psycopg2 pool on startup and closes it on shutdown. Routers are mounted here.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import RequestContextMiddleware
from src.api.routers import (
    auth_routes,
    categories_routes,
    expenses_routes,
    health_routes,
    payment_methods_routes,
)
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import configure_logging, get_logger
from src.db.pool import close_pool, init_pool

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_pool()
    log.info("app.startup", env=settings.app_env)
    try:
        yield
    finally:
        close_pool()
        log.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Expense Management API",
        version="1.0.0",
        description=(
            "Agentic receipt extraction, semantic search, text-to-SQL chat, "
            "anomaly insights, and an MCP server — over a multi-tenant FastAPI backend."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(categories_routes.router)
    app.include_router(payment_methods_routes.router)
    app.include_router(expenses_routes.router)

    return app


app = create_app()


def run() -> None:
    """Console-script entrypoint (`expense-api`)."""
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)


if __name__ == "__main__":
    run()
