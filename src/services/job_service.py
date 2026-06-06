"""Job + receipt orchestration (synchronous DB side).

These functions are called from two places:
  * the API (to create receipt+job rows before enqueuing), and
  * the ARQ worker (to actually run the graph and record results).

Keeping them sync (psycopg2 + sync LangGraph) means the worker wraps them in a
thread, and the API calls them via ``run_in_threadpool``.
"""

from __future__ import annotations

import hashlib
import uuid

from src.core.logging import get_logger
from src.db.repositories.jobs_repo import JobsRepository
from src.db.repositories.receipts_repo import ReceiptsRepository
from src.db.session import get_cursor
from src.services import receipt_service

log = get_logger(__name__)


def create_receipt_and_job(
    user_id: int, file_bytes: bytes, *, suffix: str, mime_type: str | None
) -> dict:
    """Persist the upload + create receipt and job rows. Returns the job row."""
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    receipt_id, path = receipt_service.save_upload(file_bytes, suffix=suffix)
    job_id = str(uuid.uuid4())

    with get_cursor() as cur:
        ReceiptsRepository(cur, user_id).create(
            receipt_id=receipt_id,
            file_path=path,
            mime_type=mime_type,
            sha256=sha256,
        )
        job = JobsRepository(cur, user_id).create(
            job_id=job_id, receipt_id=receipt_id, type="process_receipt"
        )

    job["_image_path"] = path  # convenience for the caller's enqueue step
    return job


def get_job(user_id: int, job_id: str) -> dict | None:
    with get_cursor() as cur:
        return JobsRepository(cur, user_id).get(job_id)


def list_jobs(user_id: int, *, status: str | None = None) -> list[dict]:
    with get_cursor() as cur:
        return JobsRepository(cur, user_id).list(status=status)


def _set_status(user_id: int, job_id: str, status: str) -> None:
    with get_cursor() as cur:
        JobsRepository(cur, user_id).update(job_id, status=status)


def run_processing(user_id: int, job_id: str, receipt_id: str, image_path: str) -> dict:
    """Run the extraction graph and record the outcome on the job row."""
    _set_status(user_id, job_id, "processing")
    try:
        out = receipt_service.start_processing(user_id, image_path, receipt_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("job.process.failed", job_id=job_id)
        with get_cursor() as cur:
            JobsRepository(cur, user_id).update(job_id, status="failed", error=str(exc))
        raise

    with get_cursor() as cur:
        JobsRepository(cur, user_id).update(job_id, status=out["status"], result=out)
    return out


def run_resume(user_id: int, job_id: str, thread_id: str, decision: dict) -> dict:
    """Resume an interrupted run and record the new outcome on the job row."""
    _set_status(user_id, job_id, "processing")
    out = receipt_service.resume_processing(user_id, thread_id, decision)
    with get_cursor() as cur:
        JobsRepository(cur, user_id).update(job_id, status=out["status"], result=out)
    return out
