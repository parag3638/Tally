"""Receipt graph logic: confidence routing + interrupt/resume cycle.

The LLM nodes are bypassed by monkeypatching ``structured_model`` so the graph's
control flow (auto-accept vs human review, accept/correct/retry_model resume) is
tested deterministically without any API calls. Uses an in-memory checkpointer.
"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver

import src.agents.receipt_graph.nodes.categorizer as categorizer_mod
import src.agents.receipt_graph.nodes.extractor as extractor_mod
from src.agents.receipt_graph.graph import get_receipt_graph
from src.agents.receipt_graph.state import CategoryChoice, ReceiptData


class _Fake:
    def __init__(self, obj):
        self._obj = obj

    def invoke(self, _messages):
        return self._obj


@pytest.fixture
def patched_models(monkeypatch):
    """Return a controller letting each test set extraction confidence."""

    state = {"confidence": 0.95}

    def fake_extract(role, schema, model_override=None):
        return _Fake(
            ReceiptData(
                date="2026-06-01",
                description="Walmart groceries",
                amount="42.50",
                vat="3.50",
                business_personal="personal",
                payment_method="Credit Card",
                confidence=state["confidence"],
            )
        )

    def fake_categorize(role, schema, model_override=None):
        return _Fake(CategoryChoice(category="Food"))

    monkeypatch.setattr(extractor_mod, "structured_model", fake_extract)
    monkeypatch.setattr(categorizer_mod, "structured_model", fake_categorize)
    return state


@pytest.fixture
def persisted(monkeypatch):
    """Capture persisted expenses instead of hitting the DB."""
    import src.agents.receipt_graph.nodes.persist as persist_mod

    saved = []

    def fake_create(user_id, **kwargs):
        row = {"transaction_id": len(saved) + 1, "user_id": user_id, **kwargs}
        saved.append(row)
        return row

    monkeypatch.setattr(persist_mod.expense_service, "create_expense", fake_create)
    return saved


def _initial(tmp_image):
    return {
        "user_id": 1,
        "receipt_id": "rcpt-1",
        "image_path": str(tmp_image),
        "categories": {1: "Food", 2: "Travel"},
        "payment_methods": {1: "Credit Card", 2: "Cash"},
        "model_attempts": 0,
        "status": "processing",
    }


@pytest.fixture
def tmp_image(tmp_path):
    p = tmp_path / "receipt.jpg"
    p.write_bytes(b"fake-image-bytes")
    return p


def test_high_confidence_auto_persists(patched_models, persisted, tmp_image):
    patched_models["confidence"] = 0.95
    graph = get_receipt_graph(checkpointer=MemorySaver())
    result = graph.invoke(_initial(tmp_image), {"configurable": {"thread_id": "t1"}})
    assert "__interrupt__" not in result
    assert result["status"] == "completed"
    assert result["created_expense"]["category_id"] == 1
    assert len(persisted) == 1


def test_low_confidence_interrupts_then_accept(patched_models, persisted, tmp_image):
    from langgraph.types import Command

    patched_models["confidence"] = 0.30
    graph = get_receipt_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "t2"}}

    graph.invoke(_initial(tmp_image), cfg)
    snapshot = graph.get_state(cfg)
    interrupts = [t for task in snapshot.tasks for t in (task.interrupts or [])]
    assert interrupts  # paused for human review
    review = interrupts[0].value
    assert "low confidence" in review["reason"]
    assert review["extracted"]["category"] == "Food"
    assert len(persisted) == 0  # nothing saved yet

    # Human accepts -> graph resumes and persists.
    final = graph.invoke(Command(resume={"decision": "accept"}), cfg)
    assert final["status"] == "completed"
    assert len(persisted) == 1


def test_correct_path_revises_then_persists(patched_models, persisted, tmp_image, monkeypatch):
    from langgraph.types import Command

    import src.agents.receipt_graph.nodes.corrector as corrector_mod
    from src.agents.receipt_graph.state import CorrectedSummary

    def fake_correct(role, schema, model_override=None):
        return _Fake(
            CorrectedSummary(
                date="2026-06-01",
                category="Travel",
                description="Uber ride",
                amount="20.00",
                vat="0",
                business_personal="business",
                payment_method="Cash",
            )
        )

    monkeypatch.setattr(corrector_mod, "structured_model", fake_correct)

    patched_models["confidence"] = 0.20
    graph = get_receipt_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "t3"}}

    graph.invoke(_initial(tmp_image), cfg)
    # Correct -> re-review -> accept
    graph.invoke(Command(resume={"decision": "correct", "correction": "it was an Uber"}), cfg)
    final = graph.invoke(Command(resume={"decision": "accept"}), cfg)

    assert final["status"] == "completed"
    saved = persisted[-1]
    assert saved["category_id"] == 2  # Travel
    assert saved["description"] == "Uber ride"
