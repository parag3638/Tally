"""Embeddings: generation, storage, semantic search, and duplicate detection.

``embed_text`` is the single seam the rest of the app (and tests) mock. Embeddings
are generated with OpenAI ``text-embedding-3-small`` (1536-dim) by default.
"""

from __future__ import annotations

from src.core.config import settings
from src.core.logging import get_logger
from src.db.repositories.embeddings_repo import EmbeddingsRepository
from src.db.session import get_cursor

log = get_logger(__name__)

_client = None


def _embeddings_client():
    global _client
    if _client is None:
        from langchain_openai import OpenAIEmbeddings

        _client = OpenAIEmbeddings(model=settings.embedding_model)
    return _client


def embed_text(text: str) -> list[float]:
    """Return the embedding vector for ``text``. Mock this in tests."""
    return _embeddings_client().embed_query(text)


def canonical_text(expense: dict) -> str:
    parts = [
        str(expense.get("description") or ""),
        str(expense.get("business_personal") or ""),
        f"amount {expense.get('amount')}" if expense.get("amount") is not None else "",
    ]
    return " | ".join(p for p in parts if p)


def embed_expense(user_id: int, expense: dict) -> None:
    text = canonical_text(expense)
    if not text.strip():
        return
    vec = embed_text(text)
    with get_cursor() as cur:
        EmbeddingsRepository(cur, user_id).set_embedding(
            expense["transaction_id"], vec, receipt_text=text
        )
    log.info("embedding.stored", transaction_id=expense.get("transaction_id"))


def search(user_id: int, query: str, *, limit: int = 10) -> list[dict]:
    vec = embed_text(query)
    with get_cursor() as cur:
        return EmbeddingsRepository(cur, user_id).search(vec, limit=limit)


def similar(user_id: int, transaction_id: int, *, limit: int = 10) -> list[dict]:
    with get_cursor() as cur:
        return EmbeddingsRepository(cur, user_id).similar_to(transaction_id, limit=limit)


def find_possible_duplicates(user_id: int, expense: dict, *, limit: int = 5) -> list[dict]:
    """Return existing expenses semantically close to ``expense``."""
    text = canonical_text(expense)
    if not text.strip():
        return []
    vec = embed_text(text)
    with get_cursor() as cur:
        rows = EmbeddingsRepository(cur, user_id).nearest_within(
            vec, max_distance=settings.duplicate_distance_threshold, limit=limit
        )
    # Exclude the expense itself if it was already persisted.
    return [r for r in rows if r.get("transaction_id") != expense.get("transaction_id")]


def backfill_user(user_id: int) -> int:
    """Embed every expense missing a vector. Returns the count embedded."""
    with get_cursor() as cur:
        rows = EmbeddingsRepository(cur, user_id).ids_missing_embedding()

    count = 0
    for row in rows:
        text = canonical_text(row)
        if not text.strip():
            continue
        vec = embed_text(text)
        with get_cursor() as cur:
            EmbeddingsRepository(cur, user_id).set_embedding(
                row["transaction_id"], vec, receipt_text=text
            )
        count += 1
    log.info("embedding.backfill.done", user_id=user_id, count=count)
    return count
