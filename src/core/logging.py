"""Structured logging via structlog.

In development emits colorized key/value lines; in production (or LOG_JSON=true)
emits one JSON object per line for ingestion by log platforms. A ``request_id``
contextvar is bound per request by the API middleware.
"""

from __future__ import annotations

import logging
import sys

import structlog

from src.core.config import settings

# Keys whose values must never reach the logs (PII / secrets).
_REDACT_KEYS = {
    "password", "password_hash", "image_base64", "authorization", "token",
    "access_token", "jwt_secret", "api_key", "openai_api_key", "anthropic_api_key",
}


def _redact_pii(logger, method_name, event_dict):
    for key in list(event_dict.keys()):
        if key.lower() in _REDACT_KEYS:
            event_dict[key] = "***redacted***"
    return event_dict


def configure_logging() -> None:
    log_json = settings.log_json or settings.is_production
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _redact_pii,
    ]

    if log_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
