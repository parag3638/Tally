"""Receipts repository — tenant-scoped uploaded-file metadata."""

from __future__ import annotations

from src.db.repositories.base import UserScopedRepository

_COLS = "receipt_id, user_id, file_path, mime_type, sha256, status, uploaded_at"


class ReceiptsRepository(UserScopedRepository):
    def create(
        self,
        *,
        receipt_id: str,
        file_path: str,
        mime_type: str | None,
        sha256: str | None,
        status: str = "uploaded",
    ) -> dict:
        self.cur.execute(
            "INSERT INTO receipts (receipt_id, user_id, file_path, mime_type, sha256, status) "
            f"VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_COLS}",
            (receipt_id, self.user_id, file_path, mime_type, sha256, status),
        )
        return self.cur.fetchone()

    def get(self, receipt_id: str) -> dict | None:
        self.cur.execute(
            f"SELECT {_COLS} FROM receipts WHERE receipt_id = %s AND user_id = %s",
            (receipt_id, self.user_id),
        )
        return self.cur.fetchone()

    def set_status(self, receipt_id: str, status: str) -> None:
        self.cur.execute(
            "UPDATE receipts SET status = %s WHERE receipt_id = %s AND user_id = %s",
            (status, receipt_id, self.user_id),
        )

    def find_by_sha256(self, sha256: str) -> dict | None:
        self.cur.execute(
            f"SELECT {_COLS} FROM receipts WHERE sha256 = %s AND user_id = %s "
            "ORDER BY uploaded_at DESC LIMIT 1",
            (sha256, self.user_id),
        )
        return self.cur.fetchone()
