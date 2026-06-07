from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    transaction_id: int
    description: str | None = None
    amount: Any | None = None
    category_id: int | None = None
    distance: float
