"""Node: flag possible duplicates before deciding auto-accept.

Best-effort: if embeddings are unavailable (no API key, etc.) it silently yields
no duplicates so the pipeline still runs. Any hits are surfaced into the
human-review payload by the confidence router.
"""

from __future__ import annotations

from src.agents.receipt_graph.state import ReceiptState
from src.core.logging import get_logger

log = get_logger(__name__)


def duplicate_check_node(state: ReceiptState) -> dict:
    pseudo_expense = {
        "transaction_id": None,
        "description": state.get("description"),
        "amount": state.get("amount"),
        "business_personal": state.get("business_personal"),
    }
    try:
        from src.services import embedding_service

        dupes = embedding_service.find_possible_duplicates(state["user_id"], pseudo_expense)
    except Exception:  # noqa: BLE001
        log.warning("receipt.duplicate_check.skipped")
        return {"possible_duplicates": []}

    if dupes:
        log.info("receipt.duplicate.flagged", count=len(dupes))
    # Keep only lightweight fields for the review payload.
    summary = [
        {
            "transaction_id": d.get("transaction_id"),
            "description": d.get("description"),
            "amount": str(d.get("amount")),
            "distance": round(float(d.get("distance", 0)), 4),
        }
        for d in dupes
    ]
    return {"possible_duplicates": summary}
