"""pgvector operations — tenant-scoped semantic search + duplicate detection.

Embeddings are passed as pgvector text literals (``'[1,2,3]'``) cast with
``::vector`` so we don't need per-connection ``register_vector`` wiring on the
psycopg2 pool.
"""

from __future__ import annotations

from src.db.repositories.base import UserScopedRepository

_READ_COLS = (
    "transaction_id, date, category_id, description, amount, vat, "
    "payment_method_id, business_personal, status, confidence"
)


def to_vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


class EmbeddingsRepository(UserScopedRepository):
    def set_embedding(self, transaction_id: int, vec: list[float], receipt_text: str | None = None) -> None:
        self.cur.execute(
            "UPDATE expenses SET embedding = %s::vector, receipt_text = COALESCE(%s, receipt_text) "
            "WHERE transaction_id = %s AND user_id = %s",
            (to_vector_literal(vec), receipt_text, transaction_id, self.user_id),
        )

    def search(self, vec: list[float], *, limit: int = 10) -> list[dict]:
        self.cur.execute(
            f"SELECT {_READ_COLS}, embedding <=> %s::vector AS distance "
            "FROM expenses WHERE user_id = %s AND embedding IS NOT NULL "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (to_vector_literal(vec), self.user_id, to_vector_literal(vec), limit),
        )
        return self.cur.fetchall()

    def similar_to(self, transaction_id: int, *, limit: int = 10) -> list[dict]:
        self.cur.execute(
            f"SELECT {_READ_COLS}, "
            "embedding <=> (SELECT embedding FROM expenses WHERE transaction_id = %s AND user_id = %s) "
            "AS distance FROM expenses "
            "WHERE user_id = %s AND embedding IS NOT NULL AND transaction_id <> %s "
            "ORDER BY distance LIMIT %s",
            (transaction_id, self.user_id, self.user_id, transaction_id, limit),
        )
        return self.cur.fetchall()

    def nearest_within(self, vec: list[float], *, max_distance: float, limit: int = 5) -> list[dict]:
        """Return rows within ``max_distance`` (cosine) — used for dup detection."""
        self.cur.execute(
            f"SELECT {_READ_COLS}, embedding <=> %s::vector AS distance "
            "FROM expenses WHERE user_id = %s AND embedding IS NOT NULL "
            "AND (embedding <=> %s::vector) < %s "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (
                to_vector_literal(vec),
                self.user_id,
                to_vector_literal(vec),
                max_distance,
                to_vector_literal(vec),
                limit,
            ),
        )
        return self.cur.fetchall()

    def ids_missing_embedding(self, *, limit: int = 500) -> list[dict]:
        self.cur.execute(
            "SELECT transaction_id, description, amount, category_id, payment_method_id "
            "FROM expenses WHERE user_id = %s AND embedding IS NULL LIMIT %s",
            (self.user_id, limit),
        )
        return self.cur.fetchall()
