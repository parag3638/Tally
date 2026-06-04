"""Request-scoped middleware: bind a request id, log timing.

The request id is bound into structlog's contextvars so every log line emitted
while handling the request carries it. The id is also echoed back in the
``X-Request-ID`` response header.
"""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.core.logging import get_logger

log = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("http.request.error", method=request.method)
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        log.info(
            "http.request",
            method=request.method,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
