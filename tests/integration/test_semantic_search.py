"""Semantic search + duplicate detection against a live pgvector DB.

``embed_text`` is replaced with a deterministic toy embedding (keyword bag over a
fixed vocabulary) so we exercise the real pgvector storage, HNSW index, and
``<=>`` distance ordering without calling OpenAI.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration

# A tiny deterministic embedding: map known words to fixed dimensions.
_VOCAB = ["coffee", "uber", "taxi", "groceries", "walmart", "hotel", "flight", "lunch"]


def _toy_embed(text: str) -> list[float]:
    text = (text or "").lower()
    vec = [0.0] * 1536
    for i, word in enumerate(_VOCAB):
        if word in text:
            vec[i] = 1.0
    # Avoid an all-zero vector (cosine distance undefined): seed one dim.
    vec[100] = 0.1
    return vec


@pytest.fixture
def user_id():
    from src.services import auth_service

    return auth_service.register(f"sem_{uuid.uuid4().hex[:10]}@example.com", "supersecret123")[
        "user_id"
    ]


@pytest.fixture
def patched_embed(monkeypatch):
    from src.services import embedding_service

    monkeypatch.setattr(embedding_service, "embed_text", _toy_embed)


def _make_expense(user_id, description, amount="10.00"):
    from src.services import embedding_service, expense_service

    exp = expense_service.create_expense(
        user_id,
        date=None,
        category_id=None,
        description=description,
        amount=Decimal(amount),
        vat=Decimal("0"),
        payment_method_id=None,
        business_personal="personal",
    )
    embedding_service.embed_expense(user_id, exp)
    return exp


def test_semantic_search_orders_by_similarity(user_id, patched_embed):
    from src.services import embedding_service

    _make_expense(user_id, "Walmart groceries weekly shop")
    _make_expense(user_id, "Uber taxi ride downtown")
    _make_expense(user_id, "Hotel stay business trip")

    hits = embedding_service.search(user_id, "groceries from walmart", limit=3)
    assert hits, "expected at least one hit"
    # The groceries/walmart expense must rank first (smallest distance).
    assert "walmart" in hits[0]["description"].lower()
    assert hits[0]["distance"] <= hits[-1]["distance"]


def test_duplicate_detection_flags_near_identical(user_id, patched_embed):
    from src.services import embedding_service

    first = _make_expense(user_id, "Uber taxi ride downtown")
    # A semantically identical new (unsaved) receipt.
    candidate = {
        "transaction_id": None,
        "description": "Uber taxi ride downtown",
        "amount": "10.00",
        "business_personal": "personal",
    }
    dupes = embedding_service.find_possible_duplicates(user_id, candidate)
    assert any(d["transaction_id"] == first["transaction_id"] for d in dupes)


def test_similar_excludes_self(user_id, patched_embed):
    from src.services import embedding_service

    a = _make_expense(user_id, "Lunch at cafe")
    _make_expense(user_id, "Coffee and lunch")
    similar = embedding_service.similar(user_id, a["transaction_id"], limit=5)
    assert all(s["transaction_id"] != a["transaction_id"] for s in similar)
