"""Node: decide whether extraction is trustworthy enough to auto-persist.

Sets ``needs_review_reason`` (None => auto-accept). The conditional edge in the
graph reads it. This is a guardrail: low-confidence or incomplete extractions —
and anything flagged as a possible duplicate — are routed to a human.
"""

from __future__ import annotations

from src.agents.receipt_graph.state import ReceiptState
from src.core.config import settings


def confidence_router_node(state: ReceiptState) -> dict:
    confidence = float(state.get("confidence") or 0.0)
    reasons: list[str] = []

    if confidence < settings.auto_accept_threshold:
        reasons.append(f"low confidence ({confidence:.2f} < {settings.auto_accept_threshold})")

    missing = [
        field
        for field in ("date", "amount", "category_id")
        if not state.get(field)
    ]
    if missing:
        reasons.append(f"missing required fields: {', '.join(missing)}")

    if state.get("possible_duplicates"):
        reasons.append("possible duplicate detected")

    return {"needs_review_reason": "; ".join(reasons) if reasons else None}
