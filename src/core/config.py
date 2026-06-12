"""Centralized application configuration via pydantic-settings.

Replaces the scattered ``os.getenv`` calls that used to live in every module.
Import the singleton ``settings`` anywhere; it is loaded once from the
environment (and ``.env`` in development).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Application ----
    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    # ---- Database ----
    pghost: str = "localhost"
    pgport: int = 5432
    pgdatabase: str = "expenses"
    pguser: str = "expenses"
    pgpassword: str = "expenses"
    db_pool_min: int = 1
    db_pool_max: int = 10

    pg_readonly_user: str | None = None
    pg_readonly_password: str | None = None

    # ---- Redis / worker ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- Auth ----
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ---- AI providers ----
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    vision_model: str = "gpt-4o"
    vision_fallback_model: str | None = "claude-3-7-sonnet-20250219"
    categorizer_model: str = "gpt-4o-mini"
    categorizer_fallback_model: str | None = "claude-3-5-haiku-20241022"
    chat_model: str = "gpt-4o"
    insights_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    auto_accept_threshold: float = 0.85
    duplicate_distance_threshold: float = 0.15

    # ---- LangSmith ----
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str | None = None
    langchain_project: str = "tally"

    # ---- Storage ----
    receipt_storage_dir: str = "./data/receipts"

    # ---- MCP ----
    mcp_user_id: int = 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """libpq-style DSN used by both psycopg2 and psycopg3."""
        return (
            f"postgresql://{self.pguser}:{self.pgpassword}"
            f"@{self.pghost}:{self.pgport}/{self.pgdatabase}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def readonly_database_url(self) -> str:
        """DSN for the text-to-SQL agent. Falls back to the app user if no
        dedicated read-only role is configured (development convenience)."""
        user = self.pg_readonly_user or self.pguser
        password = self.pg_readonly_password or self.pgpassword
        return (
            f"postgresql://{user}:{password}"
            f"@{self.pghost}:{self.pgport}/{self.pgdatabase}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenient module-level singleton.
settings = get_settings()
