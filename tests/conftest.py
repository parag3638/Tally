"""Shared test fixtures.

A ``FakeCursor`` records executed SQL + params so repository logic (especially
tenancy scoping) can be unit-tested without a live Postgres. Integration tests
that need a real DB are marked ``@pytest.mark.integration`` and skipped unless a
database is configured.
"""

from __future__ import annotations

import pytest


class FakeCursor:
    """Minimal RealDictCursor stand-in. Returns queued rows; records calls."""

    def __init__(self, rows: list | None = None):
        self._rows = list(rows or [])
        self.calls: list[tuple[str, tuple | list]] = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def close(self):
        pass

    @property
    def last_sql(self) -> str:
        return self.calls[-1][0]

    @property
    def last_params(self):
        return self.calls[-1][1]


@pytest.fixture
def fake_cursor():
    return FakeCursor()
