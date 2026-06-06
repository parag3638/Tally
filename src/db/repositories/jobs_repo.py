"""Jobs repository — durable state for background processing.

Job state lives here (not just in ARQ's result backend) so status survives worker
restarts and is queryable per user.
"""

from __future__ import annotations

import json

from src.core.exceptions import NotFoundError
from src.db.repositories.base import UserScopedRepository

_COLS = "job_id, user_id, receipt_id, type, status, result, error, created_at, updated_at"


class JobsRepository(UserScopedRepository):
    def create(self, *, job_id: str, receipt_id: str | None, type: str) -> dict:
        self.cur.execute(
            "INSERT INTO jobs (job_id, user_id, receipt_id, type, status) "
            f"VALUES (%s, %s, %s, %s, 'pending') RETURNING {_COLS}",
            (job_id, self.user_id, receipt_id, type),
        )
        return self.cur.fetchone()

    def get(self, job_id: str) -> dict | None:
        self.cur.execute(
            f"SELECT {_COLS} FROM jobs WHERE job_id = %s AND user_id = %s",
            (job_id, self.user_id),
        )
        return self.cur.fetchone()

    def list(self, *, status: str | None = None, limit: int = 50) -> list[dict]:
        sql = f"SELECT {_COLS} FROM jobs WHERE user_id = %s"
        params: list = [self.user_id]
        if status:
            sql += " AND status = %s"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        self.cur.execute(sql, params)
        return self.cur.fetchall()

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> dict:
        sets = ["updated_at = now()"]
        params: list = []
        if status is not None:
            sets.append("status = %s")
            params.append(status)
        if result is not None:
            sets.append("result = %s")
            params.append(json.dumps(result, default=str))
        if error is not None:
            sets.append("error = %s")
            params.append(error)
        params.extend([job_id, self.user_id])

        self.cur.execute(
            f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = %s AND user_id = %s "
            f"RETURNING {_COLS}",
            params,
        )
        row = self.cur.fetchone()
        if row is None:
            raise NotFoundError("Job not found")
        return row
