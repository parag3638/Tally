"""Tenancy is enforced at the repository layer — every query must be scoped to
``user_id``. These tests assert that invariant against a fake cursor."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.db.repositories.base import UserScopedRepository
from src.db.repositories.expenses_repo import ExpensesRepository


def test_user_scoped_repo_requires_user_id(fake_cursor):
    with pytest.raises(ValueError):
        UserScopedRepository(fake_cursor, None)


def test_list_always_filters_by_user_id(fake_cursor):
    repo = ExpensesRepository(fake_cursor, user_id=42)
    repo.list()
    sql, params = fake_cursor.calls[-1]
    assert "WHERE user_id = %s" in sql
    assert params[0] == 42


def test_list_applies_all_filters_with_user_id_first(fake_cursor):
    repo = ExpensesRepository(fake_cursor, user_id=7)
    repo.list(
        category_id=3,
        payment_method_id=2,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )
    sql, params = fake_cursor.calls[-1]
    assert sql.count("AND") >= 4
    assert params[0] == 7  # user_id is always the leading bound param
    assert 3 in params and 2 in params


def test_get_is_user_scoped(fake_cursor):
    repo = ExpensesRepository(fake_cursor, user_id=99)
    repo.get(123)
    sql, params = fake_cursor.calls[-1]
    assert "transaction_id = %s AND user_id = %s" in sql
    assert params == (123, 99)


def test_create_injects_user_id(fake_cursor):
    fake_cursor._rows = [{"transaction_id": 1}]
    repo = ExpensesRepository(fake_cursor, user_id=5)
    repo.create(
        date=date(2026, 6, 1),
        category_id=1,
        description="Coffee",
        amount=Decimal("4.50"),
        vat=Decimal("0.40"),
        payment_method_id=1,
        business_personal="personal",
    )
    _, params = fake_cursor.calls[-1]
    assert 5 in params  # user_id bound into the INSERT


def test_delete_is_user_scoped(fake_cursor):
    fake_cursor._rows = [{"transaction_id": 1}]
    repo = ExpensesRepository(fake_cursor, user_id=8)
    repo.delete(1)
    sql, params = fake_cursor.calls[-1]
    assert "WHERE transaction_id = %s AND user_id = %s" in sql
    assert params == (1, 8)
