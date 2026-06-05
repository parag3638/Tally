"""Node: persist the finalized expense via the service layer.

Calls ``expense_service.create_expense`` directly (in-process) instead of the old
HTTP self-call to ``/expenses``. Embedding generation (Phase 4) is wired in here.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.agents.receipt_graph.state import ReceiptState
from src.core.logging import get_logger
from src.services import expense_service

log = get_logger(__name__)


def _to_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        # Strip currency symbols / spaces, keep digits, separators and sign.
        cleaned = "".join(c for c in str(value) if c.isdigit() or c in ".,-").replace(",", ".")
        return Decimal(cleaned) if cleaned else None
    except (InvalidOperation, ValueError):
        return None


def _to_date(value) -> date_type | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def persist_node(state: ReceiptState) -> dict:
    try:
        expense = expense_service.create_expense(
            state["user_id"],
            date=_to_date(state.get("date")),
            category_id=state.get("category_id"),
            description=state.get("description"),
            amount=_to_decimal(state.get("amount")),
            vat=_to_decimal(state.get("vat")),
            payment_method_id=state.get("payment_method_id"),
            business_personal=state.get("business_personal"),
            receipt_id=state.get("receipt_id"),
            status="confirmed",
            confidence=state.get("confidence"),
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("receipt.persist.failed")
        return {"status": "failed", "error": str(exc)}

    log.info("receipt.persisted", transaction_id=expense.get("transaction_id"))

    # Phase 4 hook: generate + store the embedding (best-effort, never blocks save).
    try:
        from src.services import embedding_service

        embedding_service.embed_expense(state["user_id"], expense)
    except Exception:  # noqa: BLE001
        log.warning("receipt.embedding.skipped", transaction_id=expense.get("transaction_id"))

    return {"status": "completed", "created_expense": expense}
