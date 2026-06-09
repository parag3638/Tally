"""Statistical anomaly detectors (pure functions over aggregated rows).

These run *before* any LLM call — cheap, deterministic, and unit-testable. The
LLM only narrates what these surface, so reported numbers are always grounded.
"""

from __future__ import annotations

from decimal import Decimal
from statistics import mean, pstdev

# z-score threshold for flagging a category's latest month as a spike.
SPIKE_Z = 2.0
MIN_MONTHS = 3


def _f(x) -> float:
    return float(x) if x is not None else 0.0


def detect_category_spikes(series: list[dict]) -> list[dict]:
    """Flag categories whose most recent month is a statistical outlier.

    ``series`` rows: {category_name, month, total} ordered oldest-first.
    """
    by_cat: dict[str, list[tuple]] = {}
    for row in series:
        by_cat.setdefault(row["category_name"] or "Uncategorized", []).append(
            (row["month"], _f(row["total"]))
        )

    anomalies: list[dict] = []
    for category, points in by_cat.items():
        if len(points) < MIN_MONTHS:
            continue
        points.sort(key=lambda p: p[0])
        *history, latest = points
        hist_values = [v for _, v in history]
        mu = mean(hist_values)
        sigma = pstdev(hist_values)
        latest_month, latest_value = latest
        if sigma == 0:
            continue
        z = (latest_value - mu) / sigma
        if z >= SPIKE_Z:
            anomalies.append(
                {
                    "type": "category_spike",
                    "severity": "high" if z >= 3 else "medium",
                    "category": category,
                    "month": str(latest_month),
                    "amount": round(latest_value, 2),
                    "average": round(mu, 2),
                    "z_score": round(z, 2),
                    "detail": (
                        f"{category} spending in {latest_month} was {latest_value:.2f}, "
                        f"{z:.1f}σ above the typical {mu:.2f}."
                    ),
                }
            )
    return anomalies


def detect_same_day_duplicates(rows: list[dict]) -> list[dict]:
    """Flag identical amounts charged multiple times on the same day."""
    anomalies = []
    for r in rows:
        amount = r["amount"]
        amount_str = f"{Decimal(amount):.2f}" if amount is not None else "?"
        anomalies.append(
            {
                "type": "possible_duplicate_charge",
                "severity": "medium",
                "date": str(r["date"]),
                "amount": amount_str,
                "occurrences": int(r["occurrences"]),
                "transaction_ids": list(r["transaction_ids"]),
                "detail": (
                    f"{r['occurrences']} charges of {amount_str} on {r['date']} "
                    "— possible duplicate."
                ),
            }
        )
    return anomalies
