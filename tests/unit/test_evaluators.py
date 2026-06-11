"""Eval scoring functions + log PII redaction."""

from __future__ import annotations

from src.core.logging import _redact_pii
from src.evals import evaluators


def test_amount_correct_within_tolerance():
    assert evaluators.amount_correct("42.50", "42.50")
    assert evaluators.amount_correct("$42.50", "42.50")
    assert evaluators.amount_correct("42,50", "42.50")
    assert not evaluators.amount_correct("43.00", "42.50")


def test_date_correct_normalizes():
    assert evaluators.date_correct("2026-06-01", "2026-06-01")
    assert evaluators.date_correct("2026-06-01T00:00:00", "2026-06-01")
    assert not evaluators.date_correct("2026-06-02", "2026-06-01")


def test_score_and_aggregate():
    predicted = {"amount": "42.50", "category": "Food", "payment_method": "Cash"}
    expected = {"amount": "42.50", "category": "Travel", "payment_method": "Cash"}
    score = evaluators.score_extraction(predicted, expected)
    assert score["fields"] == {"amount": True, "category": False, "payment_method": True}
    assert score["accuracy"] == round(2 / 3, 4)

    agg = evaluators.aggregate([score, score])
    assert agg["examples"] == 2
    assert agg["per_field"]["amount"] == 1.0
    assert agg["per_field"]["category"] == 0.0


def test_pii_redaction_processor():
    event = {"password": "hunter2", "image_base64": "AAAA", "user_id": 1, "msg": "ok"}
    out = _redact_pii(None, "info", dict(event))
    assert out["password"] == "***redacted***"
    assert out["image_base64"] == "***redacted***"
    assert out["user_id"] == 1  # non-sensitive preserved
