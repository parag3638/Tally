"""ARQ background worker.

Runs the receipt-extraction graph off the request path. The graph + DB code is
synchronous (psycopg2 / sync LangGraph), so each task offloads to a thread via
``asyncio.to_thread`` to avoid blocking the event loop.

Run with:  arq src.worker.WorkerSettings   (or the ``tally-worker`` script)
"""

from __future__ import annotations

import asyncio

from arq import cron

from src.core.logging import configure_logging, get_logger
from src.queue import redis_settings
from src.services import job_service

log = get_logger("worker")


async def process_receipt(ctx, job_id: str, user_id: int, receipt_id: str, image_path: str) -> dict:
    log.info("worker.process_receipt", job_id=job_id)
    return await asyncio.to_thread(
        job_service.run_processing, user_id, job_id, receipt_id, image_path
    )


async def resume_receipt(ctx, job_id: str, user_id: int, thread_id: str, decision: dict) -> dict:
    log.info("worker.resume_receipt", job_id=job_id)
    return await asyncio.to_thread(
        job_service.run_resume, user_id, job_id, thread_id, decision
    )


async def backfill_embeddings(ctx, user_id: int) -> dict:
    """Phase 4: embed any expenses missing a vector."""
    from src.services import embedding_service

    count = await asyncio.to_thread(embedding_service.backfill_user, user_id)
    return {"embedded": count}


async def generate_monthly_insights(ctx) -> dict:
    """Phase 6: scheduled monthly anomaly/insights brief for all users."""
    from src.services import insights_service

    return await asyncio.to_thread(insights_service.run_scheduled_brief)


async def on_startup(ctx) -> None:
    configure_logging()
    from src.db.pool import init_pool

    init_pool()
    log.info("worker.startup")


async def on_shutdown(ctx) -> None:
    from src.db.checkpoint_pool import close_checkpoint_pool
    from src.db.pool import close_pool

    close_checkpoint_pool()
    close_pool()
    log.info("worker.shutdown")


class WorkerSettings:
    functions = [
        process_receipt,
        resume_receipt,
        backfill_embeddings,
        generate_monthly_insights,
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = redis_settings()
    max_jobs = 10
    # Monthly insights brief at 00:00 on the 1st of each month.
    cron_jobs = [cron(generate_monthly_insights, day=1, hour=0, minute=0)]


def run() -> None:
    """Console-script entrypoint (`tally-worker`)."""
    from arq import run_worker

    run_worker(WorkerSettings)


if __name__ == "__main__":
    run()
