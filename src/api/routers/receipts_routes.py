"""Async receipt processing: upload -> enqueue -> poll job -> resume.

This is the production path (non-blocking). The synchronous demo path lives in
graph_routes.py. Heavy/sync DB work is offloaded to a threadpool so the event
loop stays responsive.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from src.api.deps import CurrentUser, get_current_user
from src.core.exceptions import NotFoundError
from src.schemas.jobs import EnqueueResponse, JobOut
from src.schemas.receipts import ReviewDecision
from src.services import job_service

router = APIRouter(tags=["receipts-async"])


@router.post("/receipts", response_model=EnqueueResponse, status_code=202)
async def upload_receipt(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> EnqueueResponse:
    contents = await file.read()
    suffix = Path(file.filename or "receipt.jpg").suffix or ".jpg"

    job = await run_in_threadpool(
        job_service.create_receipt_and_job,
        current_user.user_id,
        contents,
        suffix=suffix,
        mime_type=file.content_type,
    )

    from src.queue import get_arq_pool

    pool = await get_arq_pool()
    await pool.enqueue_job(
        "process_receipt",
        str(job["job_id"]),
        current_user.user_id,
        str(job["receipt_id"]),
        job["_image_path"],
    )
    return EnqueueResponse(
        job_id=str(job["job_id"]), status="pending", receipt_id=str(job["receipt_id"])
    )


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await run_in_threadpool(job_service.list_jobs, current_user.user_id, status=status)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str, current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    job = await run_in_threadpool(job_service.get_job, current_user.user_id, job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return job


@router.post("/jobs/{job_id}/resume", response_model=EnqueueResponse, status_code=202)
async def resume_job(
    job_id: str,
    body: ReviewDecision,
    current_user: CurrentUser = Depends(get_current_user),
) -> EnqueueResponse:
    job = await run_in_threadpool(job_service.get_job, current_user.user_id, job_id)
    if job is None:
        raise NotFoundError("Job not found")

    from src.queue import get_arq_pool

    pool = await get_arq_pool()
    await pool.enqueue_job(
        "resume_receipt",
        job_id,
        current_user.user_id,
        str(job["receipt_id"]),
        body.model_dump(exclude_none=True),
    )
    return EnqueueResponse(
        job_id=job_id, status="processing", receipt_id=str(job["receipt_id"])
    )
