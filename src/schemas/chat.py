from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
