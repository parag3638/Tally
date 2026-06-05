"""Node: human-in-the-loop review via LangGraph ``interrupt()``.

This replaces the old blocking ``input()`` prompt. When reached, the graph
*pauses* and persists its state to the Postgres checkpoint tables; the pending
payload is surfaced over HTTP. The caller later resumes with
``Command(resume={"decision": ...})`` and ``interrupt()`` returns that value here.

Decisions:
  * accept       -> proceed to persist
  * correct      -> apply free-text correction (corrector node), then review again
  * retry_model  -> re-extract with the alternate provider
"""

from __future__ import annotations

from langgraph.types import interrupt

from src.agents.models import model_names_for_role
from src.agents.receipt_graph.state import ReceiptState


def _alternate_model(role: str, current_override: str | None) -> str:
    """Pick a model different from the one currently used for this role."""
    names = model_names_for_role(role)
    current = current_override or names[0]
    for n in names:
        if n != current:
            return n
    return current  # only one model configured; nothing to switch to


def human_review_node(state: ReceiptState) -> dict:
    payload = {
        "receipt_id": state.get("receipt_id"),
        "reason": state.get("needs_review_reason"),
        "confidence": state.get("confidence"),
        "possible_duplicates": state.get("possible_duplicates") or [],
        "extracted": {
            "date": state.get("date"),
            "category": state.get("category"),
            "description": state.get("description"),
            "amount": state.get("amount"),
            "vat": state.get("vat"),
            "business_personal": state.get("business_personal"),
            "payment_method": state.get("payment_method"),
        },
        "options": ["accept", "correct", "retry_model"],
    }

    # Pauses here until resumed. The resume value is returned.
    response = interrupt(payload)

    decision = (response or {}).get("decision", "accept")
    updates: dict = {"review_decision": decision}

    if decision == "correct":
        updates["correction_text"] = (response or {}).get("correction", "")
    elif decision == "retry_model":
        updates["vision_model_override"] = _alternate_model(
            "vision", state.get("vision_model_override")
        )
        updates["categorizer_model_override"] = _alternate_model(
            "categorizer", state.get("categorizer_model_override")
        )

    return updates
