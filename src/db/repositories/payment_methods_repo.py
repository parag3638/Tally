"""Payment methods — a global reference table shared across all users."""

from __future__ import annotations

from src.core.exceptions import ConflictError, NotFoundError
from src.db.repositories.base import BaseRepository


class PaymentMethodsRepository(BaseRepository):
    def list(self) -> list[dict]:
        self.cur.execute(
            "SELECT payment_method_id, payment_method_name FROM payment_methods "
            "ORDER BY payment_method_name"
        )
        return self.cur.fetchall()

    def get(self, payment_method_id: int) -> dict | None:
        self.cur.execute(
            "SELECT payment_method_id, payment_method_name FROM payment_methods "
            "WHERE payment_method_id = %s",
            (payment_method_id,),
        )
        return self.cur.fetchone()

    def create(self, name: str) -> dict:
        try:
            self.cur.execute(
                "INSERT INTO payment_methods (payment_method_name) VALUES (%s) "
                "RETURNING payment_method_id, payment_method_name",
                (name,),
            )
        except Exception as exc:
            raise ConflictError(f"Payment method '{name}' already exists") from exc
        return self.cur.fetchone()

    def delete(self, payment_method_id: int) -> None:
        self.cur.execute(
            "DELETE FROM payment_methods WHERE payment_method_id = %s "
            "RETURNING payment_method_id",
            (payment_method_id,),
        )
        if self.cur.fetchone() is None:
            raise NotFoundError("Payment method not found")

    def name_to_id_map(self) -> dict[str, int]:
        return {r["payment_method_name"]: r["payment_method_id"] for r in self.list()}
