"""Field-level evaluators for receipt-extraction quality.

Pure scoring functions (no LangSmith dependency) so they're unit-testable and
reusable both for local offline evals and as LangSmith custom evaluators.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def _norm_amount(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        cleaned = "".join(c for c in str(value) if c.isdigit() or c in ".,-").replace(",", ".")
        return Decimal(cleaned) if cleaned else None
    except (InvalidOperation, ValueError):
        return None


def amount_correct(pred, expected, *, tolerance: str = "0.01") -> bool:
    p, e = _norm_amount(pred), _norm_amount(expected)
    if p is None or e is None:
        return p == e
    return abs(p - e) <= Decimal(tolerance)


def date_correct(pred, expected) -> bool:
    return str(pred or "").strip()[:10] == str(expected or "").strip()[:10]


def text_correct(pred, expected) -> bool:
    return str(pred or "").strip().lower() == str(expected or "").strip().lower()


# field -> comparison function
_FIELD_SCORERS = {
    "date": date_correct,
    "amount": amount_correct,
    "vat": amount_correct,
    "business_personal": text_correct,
    "payment_method": text_correct,
    "category": text_correct,
}


def score_extraction(predicted: dict, expected: dict) -> dict:
    """Return per-field correctness + an aggregate accuracy over scored fields."""
    fields = {}
    for field, scorer in _FIELD_SCORERS.items():
        if field in expected:
            fields[field] = bool(scorer(predicted.get(field), expected.get(field)))
    accuracy = sum(fields.values()) / len(fields) if fields else 0.0
    return {"fields": fields, "accuracy": round(accuracy, 4)}


def aggregate(results: list[dict]) -> dict:
    """Aggregate per-example results into dataset-level metrics."""
    if not results:
        return {"examples": 0, "mean_accuracy": 0.0, "per_field": {}}

    per_field_hits: dict[str, list[bool]] = {}
    for r in results:
        for field, ok in r["fields"].items():
            per_field_hits.setdefault(field, []).append(ok)

    per_field = {f: round(sum(v) / len(v), 4) for f, v in per_field_hits.items()}
    mean_acc = round(sum(r["accuracy"] for r in results) / len(results), 4)
    return {"examples": len(results), "mean_accuracy": mean_acc, "per_field": per_field}
