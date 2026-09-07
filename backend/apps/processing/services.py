"""
backend/apps/processing/services.py

Bridges the REST API to the existing Member-3 ETL entry point:

    from data_processing.pipeline.run import process_file
    process_file(job_id, upload_file_id, file_path)

Conceptual flow (PART 20 of the handoff):

    Upload -> create UploadFile row -> create ProcessingJob (Queued)
           -> background worker -> Running -> pipeline.run() -> Completed/Failed

Background execution has two modes, chosen by settings.USE_CELERY:
  - Celery (if USE_CELERY=true and a broker is configured) — see tasks.py.
    This is the path Member 4 can wire into a real worker deployment.
  - An in-process background thread (default) — zero extra infrastructure,
    good enough for a hackathon demo, and keeps the HTTP request from
    blocking on potentially slow file processing.

Either way, the actual ETL work (and all job-status updates) happens
inside Member 3's Pipeline class — this module never touches
processing_jobs' business logic directly, it only creates the initial
Queued row and invokes process_file().
"""

from __future__ import annotations

import logging
import threading

from django.conf import settings

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError
from database.schema.models import JobStatus, ProcessingJob, UploadFile

logger = logging.getLogger(__name__)

STATUS_DISPLAY = {
    "queued": "Queued",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
}


def display_status(raw_status) -> str:
    value = raw_status.value if hasattr(raw_status, "value") else str(raw_status)
    return STATUS_DISPLAY.get(value, value)


def create_job(upload_file_id: int) -> dict:
    """
    Create a Queued ProcessingJob for an existing UploadFile and dispatch
    background execution. Returns the job as a plain dict.
    """
    with session_scope() as session:
        upload_file = session.get(UploadFile, upload_file_id)
        if upload_file is None:
            raise NotFoundError(f"File {upload_file_id} not found.")

        job = ProcessingJob(
            upload_file_id=upload_file_id,
            status=JobStatus.QUEUED,
        )
        session.add(job)
        session.flush()
        job_id = job.id
        file_path = upload_file.stored_path
        data = to_dict(job)

    data["status"] = display_status(data["status"])
    _dispatch(job_id, upload_file_id, file_path)
    return data


def _dispatch(job_id: int, upload_file_id: int, file_path: str) -> None:
    if settings.USE_CELERY and settings.CELERY_BROKER_URL:
        try:
            from .tasks import process_upload_file_task
            process_upload_file_task.delay(job_id, upload_file_id, file_path)
            return
        except Exception:
            logger.exception(
                "Celery dispatch failed for job %s; falling back to a background thread.",
                job_id,
            )

    thread = threading.Thread(
        target=run_job,
        args=(job_id, upload_file_id, file_path),
        daemon=True,
    )
    thread.start()


def run_job(job_id: int, upload_file_id: int, file_path: str) -> None:
    """
    Invoke the existing Member-3 pipeline entry point.

    All status transitions (Queued -> Running -> Completed/Failed) and
    error-message recording are handled inside Pipeline.run() itself;
    this function just calls it and makes sure a failure never escapes
    as an unhandled exception in a background thread.
    """
    from data_processing.pipeline.run import process_file
    from data_processing.pipeline.pipeline import PipelineError

    try:
        process_file(job_id=job_id, upload_file_id=upload_file_id, file_path=file_path)
    except PipelineError as exc:
        # Already recorded as FAILED on the job row by the pipeline itself.
        logger.warning("Processing job %s failed: %s", job_id, exc)
    except Exception:
        logger.exception("Unexpected error running processing job %s", job_id)


def get_job(job_id: int) -> dict:
    with session_scope() as session:
        job = session.get(ProcessingJob, job_id)
        if job is None:
            raise NotFoundError(f"Processing job {job_id} not found.")
        data = to_dict(job)
    data["status"] = display_status(data["status"])
    return data