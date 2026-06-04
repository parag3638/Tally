"""Users repository — backs registration, login, and current-user lookup."""

from __future__ import annotations

from src.core.exceptions import ConflictError
from src.db.repositories.base import BaseRepository


class UsersRepository(BaseRepository):
    def get_by_id(self, user_id: int) -> dict | None:
        self.cur.execute(
            "SELECT user_id, email, password_hash, is_active, created_at "
            "FROM users WHERE user_id = %s",
            (user_id,),
        )
        return self.cur.fetchone()

    def get_by_email(self, email: str) -> dict | None:
        self.cur.execute(
            "SELECT user_id, email, password_hash, is_active, created_at "
            "FROM users WHERE email = %s",
            (email,),
        )
        return self.cur.fetchone()

    def all_active_ids(self) -> list[int]:
        self.cur.execute("SELECT user_id FROM users WHERE is_active ORDER BY user_id")
        return [r["user_id"] for r in self.cur.fetchall()]

    def create(self, email: str, password_hash: str) -> dict:
        if self.get_by_email(email):
            raise ConflictError("A user with that email already exists")
        self.cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) "
            "RETURNING user_id, email, is_active, created_at",
            (email, password_hash),
        )
        return self.cur.fetchone()
