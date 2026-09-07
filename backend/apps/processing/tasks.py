"""
backend/apps/processing/tasks.py

Optional Celery task wrapper. Only imported/used when
settings.USE_CELERY is true and a broker is configured (see
services._dispatch). Kept separate from services.run_job so a Celery
worker process can `from apps.processing.tasks import
process_upload_file_task` without pulling in Django's request-handling
code.

Member 4 owns wiring up the actual Celery worker/broker in
infrastructure/; this file just defines the task shape it can run.
"""

from __future__ import annotations

try:
    from celery import shared_task
except ImportError:  # celery not installed — Celery dispatch is opt-in
    shared_task = None


if shared_task is not None:

    @shared_task(name="processing.process_upload_file")
    def process_upload_file_task(job_id: int, upload_file_id: int, file_path: str) -> None:
        from .services import run_job
        run_job(job_id, upload_file_id, file_path)