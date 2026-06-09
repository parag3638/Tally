"""Insights orchestration: run detectors over a user's data, optionally narrate.

The statistical layer is independent of any LLM, so anomaly detection works (and
is tested) without API keys. ``generate_brief`` adds the natural-language summary.
"""

from __future__ import annotations

from src.agents.insights_agent import detectors
from src.core.logging import get_logger
from src.db.repositories.analytics_repo import AnalyticsRepository
from src.db.repositories.users_repo import UsersRepository
from src.db.session import get_cursor

log = get_logger(__name__)


def detect_anomalies(user_id: int) -> dict:
    with get_cursor() as cur:
        repo = AnalyticsRepository(cur, user_id)
        series = repo.category_monthly_series()
        dup_rows = repo.same_day_amount_duplicates()

    anomalies = detectors.detect_category_spikes(series) + detectors.detect_same_day_duplicates(
        dup_rows
    )
    return {"count": len(anomalies), "anomalies": anomalies}


def monthly_summary(user_id: int) -> dict:
    with get_cursor() as cur:
        repo = AnalyticsRepository(cur, user_id)
        return {
            "monthly": repo.monthly_summary(),
            "by_category": repo.category_breakdown(months=1),
        }


def generate_brief(user_id: int) -> dict:
    found = detect_anomalies(user_id)
    summary = monthly_summary(user_id)
    from src.agents.insights_agent.graph import generate_brief as narrate

    text = narrate(found["anomalies"], summary["monthly"])
    return {"brief": text, "anomalies": found["anomalies"], "summary": summary}


def run_scheduled_brief() -> dict:
    """Generate (and log) a monthly brief for every active user. Called by ARQ cron."""
    with get_cursor() as cur:
        user_ids = UsersRepository(cur).all_active_ids()

    results = 0
    for uid in user_ids:
        try:
            found = detect_anomalies(uid)
            log.info("insights.scheduled", user_id=uid, anomalies=found["count"])
            results += 1
        except Exception:  # noqa: BLE001
            log.exception("insights.scheduled.failed", user_id=uid)
    return {"users_processed": results}
