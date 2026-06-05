"""Agentic receipt processing endpoints (synchronous in Phase 2).

    POST /receipts/upload-graph        -> upload image, run graph, return result
    GET  /receipts/{thread_id}/status  -> current state / pending review
    POST /receipts/{thread_id}/resume  -> resume an interrupted run with a decision

The Phase-3 async variant (enqueue + job status) lives in receipts_routes.py.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.deps import CurrentUser, get_current_user
from src.schemas.receipts import ReceiptProcessResult, ReviewDecision
from src.services import receipt_service

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("/upload-graph", response_model=ReceiptProcessResult)
async def upload_and_process(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    contents = await file.read()
    suffix = Path(file.filename or "receipt.jpg").suffix or ".jpg"
    receipt_id, path = receipt_service.save_upload(contents, suffix=suffix)
    return receipt_service.start_processing(current_user.user_id, path, receipt_id)


@router.get("/{thread_id}/status", response_model=ReceiptProcessResult)
def status(
    thread_id: str, current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    return receipt_service.get_status(current_user.user_id, thread_id)


@router.post("/{thread_id}/resume", response_model=ReceiptProcessResult)
def resume(
    thread_id: str,
    body: ReviewDecision,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return receipt_service.resume_processing(
        current_user.user_id, thread_id, body.model_dump(exclude_none=True)
    )
