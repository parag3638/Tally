"""Insights + anomaly-detection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from src.api.deps import CurrentUser, get_current_user
from src.services import insights_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/anomalies")
async def anomalies(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return await run_in_threadpool(insights_service.detect_anomalies, current_user.user_id)


@router.get("/monthly")
async def monthly(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return await run_in_threadpool(insights_service.monthly_summary, current_user.user_id)


@router.post("/brief")
async def brief(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Natural-language insights brief (anomalies narrated by the LLM)."""
    return await run_in_threadpool(insights_service.generate_brief, current_user.user_id)
