from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ReviewDecision(BaseModel):
    decision: Literal["accept", "correct", "retry_model"] = "accept"
    correction: str | None = None


class ReceiptProcessResult(BaseModel):
    thread_id: str
    status: str
    review: dict[str, Any] | None = None
    expense: dict[str, Any] | None = None
    error: str | None = None
