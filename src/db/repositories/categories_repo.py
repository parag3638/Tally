"""Categories — a global reference table shared across all users."""

from __future__ import annotations

from src.core.exceptions import ConflictError, NotFoundError
from src.db.repositories.base import BaseRepository


class CategoriesRepository(BaseRepository):
    def list(self) -> list[dict]:
        self.cur.execute(
            "SELECT category_id, category_name FROM categories ORDER BY category_name"
        )
        return self.cur.fetchall()

    def get(self, category_id: int) -> dict | None:
        self.cur.execute(
            "SELECT category_id, category_name FROM categories WHERE category_id = %s",
            (category_id,),
        )
        return self.cur.fetchone()

    def get_by_name(self, name: str) -> dict | None:
        self.cur.execute(
            "SELECT category_id, category_name FROM categories WHERE category_name = %s",
            (name,),
        )
        return self.cur.fetchone()

    def create(self, name: str) -> dict:
        try:
            self.cur.execute(
                "INSERT INTO categories (category_name) VALUES (%s) "
                "RETURNING category_id, category_name",
                (name,),
            )
        except Exception as exc:  # unique violation surfaces here
            raise ConflictError(f"Category '{name}' already exists") from exc
        return self.cur.fetchone()

    def delete(self, category_id: int) -> None:
        self.cur.execute(
            "DELETE FROM categories WHERE category_id = %s RETURNING category_id",
            (category_id,),
        )
        if self.cur.fetchone() is None:
            raise NotFoundError("Category not found")

    def name_to_id_map(self) -> dict[str, int]:
        return {r["category_name"]: r["category_id"] for r in self.list()}
