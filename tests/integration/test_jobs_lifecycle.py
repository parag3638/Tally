"""Async job lifecycle against a live DB (worker logic called directly).

The LLM and the receipt graph are mocked so we exercise the receipt->job->run->
resume plumbing and durable job state without Redis or API keys.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def user_id():
    """Create a real user row and return its id."""
    from src.services import auth_service

    email = f"jobs_{uuid.uuid4().hex[:10]}@example.com"
    user = auth_service.register(email, "supersecret123")
    return user["user_id"]


def test_process_receipt_job_records_needs_review(monkeypatch, user_id, _db_available):
    from src.services import job_service, receipt_service

    # Mock the graph run: pretend extraction needs human review.
    def fake_start(uid, image_path, receipt_id):
        return {
            "thread_id": receipt_id,
            "status": "needs_review",
            "review": {"reason": "low confidence (0.30 < 0.85)"},
        }

    monkeypatch.setattr(receipt_service, "start_processing", fake_start)

    job = job_service.create_receipt_and_job(
        user_id, b"fake-image", suffix=".jpg", mime_type="image/jpeg"
    )
    out = job_service.run_processing(
        user_id, str(job["job_id"]), str(job["receipt_id"]), job["_image_path"]
    )
    assert out["status"] == "needs_review"

    # Durable job state reflects it.
    stored = job_service.get_job(user_id, str(job["job_id"]))
    assert stored["status"] == "needs_review"
    assert stored["result"]["review"]["reason"].startswith("low confidence")


def test_resume_job_completes(monkeypatch, user_id, _db_available):
    from src.services import job_service, receipt_service

    monkeypatch.setattr(
        receipt_service,
        "start_processing",
        lambda uid, p, rid: {"thread_id": rid, "status": "needs_review", "review": {}},
    )
    monkeypatch.setattr(
        receipt_service,
        "resume_processing",
        lambda uid, tid, d: {"thread_id": tid, "status": "completed", "expense": {"transaction_id": 1}},
    )

    job = job_service.create_receipt_and_job(
        user_id, b"img", suffix=".jpg", mime_type="image/jpeg"
    )
    job_service.run_processing(
        user_id, str(job["job_id"]), str(job["receipt_id"]), job["_image_path"]
    )
    out = job_service.run_resume(
        user_id, str(job["job_id"]), str(job["receipt_id"]), {"decision": "accept"}
    )
    assert out["status"] == "completed"
    assert job_service.get_job(user_id, str(job["job_id"]))["status"] == "completed"


def test_jobs_are_tenant_scoped(monkeypatch, user_id, _db_available):
    from src.services import auth_service, job_service, receipt_service

    monkeypatch.setattr(
        receipt_service,
        "start_processing",
        lambda uid, p, rid: {"thread_id": rid, "status": "completed", "expense": {}},
    )
    job = job_service.create_receipt_and_job(
        user_id, b"img", suffix=".jpg", mime_type="image/jpeg"
    )
    other = auth_service.register(f"other_{uuid.uuid4().hex[:8]}@example.com", "supersecret123")
    # The other user cannot see this job.
    assert job_service.get_job(other["user_id"], str(job["job_id"])) is None
