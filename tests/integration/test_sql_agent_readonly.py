"""The text-to-SQL execution path against a live DB: read-only + tenant-scoped."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.core.exceptions import GuardrailError

pytestmark = pytest.mark.integration


def _new_user():
    from src.services import auth_service

    return auth_service.register(f"sql_{uuid.uuid4().hex[:10]}@example.com", "supersecret123")[
        "user_id"
    ]


def _add_expense(user_id, description, amount):
    from src.services import expense_service

    return expense_service.create_expense(
        user_id,
        date=None,
        category_id=None,
        description=description,
        amount=Decimal(amount),
        vat=Decimal("0"),
        payment_method_id=None,
        business_personal="personal",
    )


def test_readonly_query_is_scoped_to_user(_db_available):
    from src.db.readonly import run_readonly

    a, b = _new_user(), _new_user()
    _add_expense(a, "A coffee", "5.00")
    _add_expense(a, "A lunch", "15.00")
    _add_expense(b, "B dinner", "50.00")

    a_rows = run_readonly("SELECT COUNT(*) AS n, SUM(amount) AS total FROM my_expenses", a)
    assert a_rows[0]["n"] == 2
    assert Decimal(a_rows[0]["total"]) == Decimal("20.00")

    b_rows = run_readonly("SELECT COUNT(*) AS n, SUM(amount) AS total FROM my_expenses", b)
    assert b_rows[0]["n"] == 1
    assert Decimal(b_rows[0]["total"]) == Decimal("50.00")


def test_write_query_is_blocked_before_execution(_db_available):
    from src.db.readonly import run_readonly

    a = _new_user()
    _add_expense(a, "A coffee", "5.00")
    with pytest.raises(GuardrailError):
        run_readonly("DELETE FROM my_expenses", a)
    # Data still intact.
    rows = run_readonly("SELECT COUNT(*) AS n FROM my_expenses", a)
    assert rows[0]["n"] == 1


def test_cannot_reach_other_tenant_via_raw_table(_db_available):
    from src.db.readonly import run_readonly

    a = _new_user()
    with pytest.raises(GuardrailError):
        run_readonly("SELECT * FROM expenses", a)  # raw table not allow-listed
