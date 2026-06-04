"""SQL migration runner (yoyo) + idempotent seed of categories / payment methods.

Replaces the old ``create_tables.py`` and ``create_categories_and_payment_methods.py``.
Migrations are plain numbered ``.sql`` files under ``migrations/`` — no ORM, no
Alembic, consistent with the "keep psycopg2 / raw SQL" decision.

Usage:
    python -m src.db.migrate            # apply all pending migrations + seed
    python -m src.db.migrate --rollback # roll back the most recent migration
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from yoyo import get_backend, read_migrations

from src.core.config import settings
from src.core.logging import configure_logging, get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "migrations"
CONFIG_PATH = ROOT / "config.yaml"


def _backend():
    # yoyo accepts a standard postgres DSN backed by psycopg2.
    return get_backend(settings.database_url)


def apply_migrations() -> None:
    backend = _backend()
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        to_apply = backend.to_apply(migrations)
        backend.apply_migrations(to_apply)
    log.info("db.migrate.applied", count=len(migrations))


def rollback_one() -> None:
    backend = _backend()
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        applied = backend.to_rollback(migrations)
        if applied:
            backend.rollback_migrations(applied[:1])
            log.info("db.migrate.rolled_back", migration=applied[0].id)


def seed_reference_data() -> None:
    """Seed categories and payment_methods from config.yaml. Idempotent via
    ``ON CONFLICT DO NOTHING`` on the UNIQUE name columns."""
    if not CONFIG_PATH.exists():
        log.warning("db.seed.no_config", path=str(CONFIG_PATH))
        return

    config = yaml.safe_load(CONFIG_PATH.read_text())
    categories = config.get("categories", [])
    payment_methods = config.get("payment_methods", [])

    # Imported here to avoid a circular import at module load time.
    from src.db.session import get_cursor

    with get_cursor() as cur:
        for name in categories:
            cur.execute(
                "INSERT INTO categories (category_name) VALUES (%s) "
                "ON CONFLICT (category_name) DO NOTHING",
                (name,),
            )
        for name in payment_methods:
            cur.execute(
                "INSERT INTO payment_methods (payment_method_name) VALUES (%s) "
                "ON CONFLICT (payment_method_name) DO NOTHING",
                (name,),
            )
    log.info("db.seed.done", categories=len(categories), payment_methods=len(payment_methods))


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Run database migrations.")
    parser.add_argument("--rollback", action="store_true", help="Roll back the latest migration")
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding reference data")
    args = parser.parse_args()

    if args.rollback:
        rollback_one()
        return

    apply_migrations()
    if not args.no_seed:
        seed_reference_data()


if __name__ == "__main__":
    main()
