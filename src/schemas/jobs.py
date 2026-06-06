from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobOut(BaseModel):
    job_id: str
    receipt_id: str | None = None
    type: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EnqueueResponse(BaseModel):
    job_id: str
    status: str
    receipt_id: str | None = None
