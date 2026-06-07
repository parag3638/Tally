"""Semantic search + similar-expense + duplicate endpoints (pgvector)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from src.api.deps import CurrentUser, get_current_user
from src.schemas.search import SemanticSearchRequest
from src.services import embedding_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/semantic")
async def semantic_search(
    body: SemanticSearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await run_in_threadpool(
        embedding_service.search, current_user.user_id, body.query, limit=body.limit
    )


@router.get("/similar/{transaction_id}")
async def similar_expenses(
    transaction_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await run_in_threadpool(
        embedding_service.similar, current_user.user_id, transaction_id, limit=limit
    )
