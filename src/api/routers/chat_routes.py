"""Conversational text-to-SQL chat endpoints (one-shot + SSE streaming)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from src.api.deps import CurrentUser, get_current_user
from src.schemas.chat import ChatRequest, ChatResponse
from src.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest, current_user: CurrentUser = Depends(get_current_user)
) -> ChatResponse:
    answer = await run_in_threadpool(
        chat_service.ask, current_user.user_id, body.message, body.conversation_id
    )
    return ChatResponse(conversation_id=body.conversation_id, answer=answer)


@router.post("/stream")
async def chat_stream(
    body: ChatRequest, current_user: CurrentUser = Depends(get_current_user)
):
    def event_gen():
        for token in chat_service.stream(
            current_user.user_id, body.message, body.conversation_id
        ):
            yield {"event": "token", "data": token}
        yield {"event": "done", "data": body.conversation_id}

    return EventSourceResponse(event_gen())
