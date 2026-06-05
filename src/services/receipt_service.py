"""Receipt orchestration: save the upload, run the extraction graph, and
drive the interrupt/resume human-in-the-loop cycle.

Phase 2 runs the graph synchronously. Phase 3 reuses these same functions from
the ARQ worker (durable jobs). The thread id == receipt id, so one receipt maps
to one resumable graph thread in the checkpointer.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from langgraph.types import Command

from src.agents.receipt_graph.graph import get_receipt_graph
from src.core.config import settings
from src.core.logging import get_logger
from src.db.repositories.categories_repo import CategoriesRepository
from src.db.repositories.payment_methods_repo import PaymentMethodsRepository
from src.db.session import get_cursor

log = get_logger(__name__)


def _reference_dicts() -> tuple[dict[int, str], dict[int, str]]:
    with get_cursor() as cur:
        cats = CategoriesRepository(cur).list()
        pms = PaymentMethodsRepository(cur).list()
    return (
        {c["category_id"]: c["category_name"] for c in cats},
        {p["payment_method_id"]: p["payment_method_name"] for p in pms},
    )


def save_upload(file_bytes: bytes, suffix: str = ".jpg") -> tuple[str, str]:
    """Persist the uploaded image to the storage dir. Returns (receipt_id, path)."""
    receipt_id = uuid.uuid4().hex
    storage = Path(settings.receipt_storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / f"{receipt_id}{suffix}"
    path.write_bytes(file_bytes)
    return receipt_id, str(path)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _result_from_state(graph, thread_id: str) -> dict:
    """Normalize a run into a stable API shape by inspecting the checkpoint.

    LangGraph surfaces a pending ``interrupt()`` through ``get_state().tasks``
    (not the invoke() return value), so state is the single source of truth for
    both the synchronous path and the async worker.
    """
    snapshot = graph.get_state(_config(thread_id))
    values = snapshot.values or {}
    interrupts = [t for task in snapshot.tasks for t in (task.interrupts or [])]
    if interrupts:
        return {"thread_id": thread_id, "status": "needs_review", "review": interrupts[0].value}
    return {
        "thread_id": thread_id,
        "status": values.get("status", "completed"),
        "expense": values.get("created_expense"),
        "error": values.get("error"),
    }


def start_processing(user_id: int, image_path: str, receipt_id: str) -> dict:
    categories, payment_methods = _reference_dicts()
    graph = get_receipt_graph()
    initial: dict[str, Any] = {
        "user_id": user_id,
        "receipt_id": receipt_id,
        "image_path": image_path,
        "categories": categories,
        "payment_methods": payment_methods,
        "model_attempts": 0,
        "status": "processing",
    }
    graph.invoke(initial, _config(receipt_id))
    out = _result_from_state(graph, receipt_id)
    log.info("receipt.run.start", receipt_id=receipt_id, status=out["status"])
    return out


def resume_processing(user_id: int, thread_id: str, decision: dict) -> dict:
    """Resume an interrupted run with a review decision.

    The user_id is verified against the checkpointed thread state so a user can
    only resume their own receipts.
    """
    graph = get_receipt_graph()
    snapshot = graph.get_state(_config(thread_id))
    if not snapshot.values:
        from src.core.exceptions import NotFoundError

        raise NotFoundError("No such receipt processing thread")
    if snapshot.values.get("user_id") != user_id:
        from src.core.exceptions import PermissionError_

        raise PermissionError_("You do not own this receipt")

    graph.invoke(Command(resume=decision), _config(thread_id))
    log.info("receipt.run.resume", thread_id=thread_id, decision=decision.get("decision"))
    return _result_from_state(graph, thread_id)


def get_status(user_id: int, thread_id: str) -> dict:
    graph = get_receipt_graph()
    snapshot = graph.get_state(_config(thread_id))
    if not snapshot.values:
        from src.core.exceptions import NotFoundError

        raise NotFoundError("No such receipt processing thread")
    if snapshot.values.get("user_id") != user_id:
        from src.core.exceptions import PermissionError_

        raise PermissionError_("You do not own this receipt")
    return _result_from_state(graph, thread_id)
