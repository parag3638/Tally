"""Anomaly detection over real aggregation SQL against a live DB."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def user_id():
    from src.services import auth_service

    return auth_service.register(f"ins_{uuid.uuid4().hex[:10]}@example.com", "supersecret123")[
        "user_id"
    ]


def _food_category(user_id):
    from src.services import expense_service

    return expense_service.list_categories()[0]["category_id"]


def _add(user_id, cat, amount, d):
    from src.services import expense_service

    expense_service.create_expense(
        user_id,
        date=d,
        category_id=cat,
        description="test",
        amount=Decimal(str(amount)),
        vat=Decimal("0"),
        payment_method_id=None,
        business_personal="personal",
    )


def test_detects_monthly_category_spike(user_id, _db_available):
    from src.services import insights_service

    cat = _food_category(user_id)
    # Stable months then a spike in the latest.
    for m, amt in [(1, 100), (2, 110), (3, 95), (4, 105)]:
        _add(user_id, cat, amt, date(2026, m, 15))
    _add(user_id, cat, 800, date(2026, 5, 15))

    out = insights_service.detect_anomalies(user_id)
    spikes = [a for a in out["anomalies"] if a["type"] == "category_spike"]
    assert spikes, "expected a category spike to be detected"
    assert spikes[0]["amount"] == 800.0


def test_detects_same_day_duplicate(user_id, _db_available):
    from src.services import insights_service

    cat = _food_category(user_id)
    _add(user_id, cat, 42.50, date(2026, 6, 1))
    _add(user_id, cat, 42.50, date(2026, 6, 1))  # duplicate

    out = insights_service.detect_anomalies(user_id)
    dupes = [a for a in out["anomalies"] if a["type"] == "possible_duplicate_charge"]
    assert dupes
    assert dupes[0]["occurrences"] >= 2
