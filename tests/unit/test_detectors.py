"""Statistical anomaly detectors (no DB, no LLM)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.agents.insights_agent.detectors import (
    detect_category_spikes,
    detect_same_day_duplicates,
)


def _series(category, monthly_totals):
    return [
        {"category_name": category, "month": date(2026, m, 1), "total": Decimal(str(v))}
        for m, v in enumerate(monthly_totals, start=1)
    ]


def test_detects_a_clear_spike():
    # Four normal months ~100, then a 500 spike.
    series = _series("Food", [100, 110, 90, 105, 500])
    anomalies = detect_category_spikes(series)
    assert len(anomalies) == 1
    a = anomalies[0]
    assert a["type"] == "category_spike"
    assert a["category"] == "Food"
    assert a["amount"] == 500.0
    assert a["z_score"] >= 2.0


def test_no_spike_for_stable_spending():
    series = _series("Rent", [1000, 1000, 1000, 1000, 1000])
    assert detect_category_spikes(series) == []


def test_ignores_categories_with_too_few_months():
    series = _series("Travel", [50, 9000])  # only 2 months
    assert detect_category_spikes(series) == []


def test_detects_same_day_duplicates():
    rows = [
        {
            "date": date(2026, 6, 1),
            "amount": Decimal("42.50"),
            "occurrences": 2,
            "transaction_ids": [10, 11],
        }
    ]
    out = detect_same_day_duplicates(rows)
    assert out[0]["type"] == "possible_duplicate_charge"
    assert out[0]["amount"] == "42.50"
    assert out[0]["transaction_ids"] == [10, 11]
