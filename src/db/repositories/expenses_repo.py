"""Expenses repository — tenant-scoped.

Every method requires ``user_id`` (enforced by ``UserScopedRepository``) and every
WHERE clause is constrained by it, so a query can never read or mutate another
user's rows. This is the single choke point for multitenancy.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.exceptions import NotFoundError
from src.db.repositories.base import UserScopedRepository

# Columns selected for read responses. Extended by later migrations
# (receipt_id, status, confidence, created_at) — kept in one place.
_SELECT_COLS = (
    "transaction_id, date, category_id, description, amount, vat, "
    "payment_method_id, business_personal, declared_on, user_id, "
    "receipt_id, status, confidence, created_at"
)


class ExpensesRepository(UserScopedRepository):
    def list(
        self,
        *,
        category_id: int | None = None,
        payment_method_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        sql = f"SELECT {_SELECT_COLS} FROM expenses WHERE user_id = %s"
        params: list = [self.user_id]

        if category_id is not None:
            sql += " AND category_id = %s"
            params.append(category_id)
        if payment_method_id is not None:
            sql += " AND payment_method_id = %s"
            params.append(payment_method_id)
        if start_date is not None:
            sql += " AND date >= %s"
            params.append(start_date)
        if end_date is not None:
            sql += " AND date <= %s"
            params.append(end_date)

        sql += " ORDER BY date DESC NULLS LAST, transaction_id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        self.cur.execute(sql, params)
        return self.cur.fetchall()

    def get(self, transaction_id: int) -> dict | None:
        self.cur.execute(
            f"SELECT {_SELECT_COLS} FROM expenses "
            "WHERE transaction_id = %s AND user_id = %s",
            (transaction_id, self.user_id),
        )
        return self.cur.fetchone()

    def create(
        self,
        *,
        date: date | None,
        category_id: int | None,
        description: str | None,
        amount: Decimal | None,
        vat: Decimal | None,
        payment_method_id: int | None,
        business_personal: str | None,
        receipt_id: str | None = None,
        status: str = "confirmed",
        confidence: float | None = None,
    ) -> dict:
        self.cur.execute(
            "INSERT INTO expenses "
            "(date, category_id, description, amount, vat, payment_method_id, "
            " business_personal, user_id, receipt_id, status, confidence) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            f"RETURNING {_SELECT_COLS}",
            (
                date,
                category_id,
                description,
                amount,
                vat,
                payment_method_id,
                business_personal,
                self.user_id,
                receipt_id,
                status,
                confidence,
            ),
        )
        return self.cur.fetchone()

    def delete(self, transaction_id: int) -> None:
        self.cur.execute(
            "DELETE FROM expenses WHERE transaction_id = %s AND user_id = %s "
            "RETURNING transaction_id",
            (transaction_id, self.user_id),
        )
        if self.cur.fetchone() is None:
            raise NotFoundError("Expense not found")

    def set_embedding(self, transaction_id: int, embedding: list[float]) -> None:
        """Set the pgvector embedding for an expense (Phase 4)."""
        self.cur.execute(
            "UPDATE expenses SET embedding = %s "
            "WHERE transaction_id = %s AND user_id = %s",
            (embedding, transaction_id, self.user_id),
        )
