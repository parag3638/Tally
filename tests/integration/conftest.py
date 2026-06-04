"""Integration fixtures — require a live Postgres reachable via the PG* env vars.

If the DB is unreachable the whole integration module is skipped, so unit-only
runs (and CI without a DB) stay green.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def _db_available() -> bool:
    try:
        from src.db.session import get_cursor

        with get_cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"No live database available: {exc}")
        return False


@pytest.fixture()
def client(_db_available) -> TestClient:
    from src.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def make_user(client):
    """Factory: register a fresh user and return (email, auth_headers)."""

    def _make() -> tuple[str, dict]:
        email = f"user_{uuid.uuid4().hex[:10]}@example.com"
        password = "supersecret123"
        r = client.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        return email, {"Authorization": f"Bearer {token}"}

    return _make
