"""
backend/apps/processing/services.py

Processing orchestration.

Single file:
    create_job()

Multiple files:
    create_batch_jobs()

The actual ETL pipeline remains in data_processing.
"""

from __future__ import annotations

import logging
import threading
from typing import Iterable

from django.conf import settings
from sqlalchemy import or_

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError

from database.schema.models import (
    BatchStatus,
    Customer,
    CustomerSource,
    JobStatus,
    ProcessingBatch,
    ProcessingJob,
    UploadFile,
)

logger = logging.getLogger(__name__)


STATUS_DISPLAY = {
    "queued": "Queued",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
}


def display_status(raw_status) -> str:
    value = (
        raw_status.value
        if hasattr(raw_status, "value")
        else str(raw_status)
    )

    return STATUS_DISPLAY.get(
        value,
        value,
    )

def display_batch_status(raw_status) -> str:
    return display_status(raw_status)


# ---------------------------------------------------------------------
# EXISTING SINGLE-FILE PROCESSING
# ---------------------------------------------------------------------

def create_job(upload_file_id: int) -> dict:
    """
    Create and dispatch a processing job for one uploaded file.
    Existing API behaviour is preserved.
    """

    with session_scope() as session:
        upload_file = session.get(
            UploadFile,
            upload_file_id,
        )

        if upload_file is None:
            raise NotFoundError(
                f"File {upload_file_id} not found."
            )

        job = ProcessingJob(
            upload_file_id=upload_file_id,
            status=JobStatus.QUEUED,
        )

        session.add(job)
        session.flush()

        job_id = job.id
        file_path = upload_file.stored_path

        data = to_dict(job)

    data["status"] = display_status(
        data["status"]
    )

    _dispatch(
        job_id,
        upload_file_id,
        file_path,
    )

    return data


def _dispatch(
    job_id: int,
    upload_file_id: int,
    file_path: str,
) -> None:

    if (
        settings.USE_CELERY
        and settings.CELERY_BROKER_URL
    ):
        try:
            from .tasks import process_upload_file_task

            process_upload_file_task.delay(
                job_id,
                upload_file_id,
                file_path,
            )

            return

        except Exception:
            logger.exception(
                "Celery dispatch failed for job %s. "
                "Falling back to background thread.",
                job_id,
            )

    thread = threading.Thread(
        target=run_job,
        args=(
            job_id,
            upload_file_id,
            file_path,
        ),
        daemon=True,
    )

    thread.start()


def run_job(
    job_id: int,
    upload_file_id: int,
    file_path: str,
) -> None:

    from data_processing.pipeline.run import process_file
    from data_processing.pipeline.pipeline import PipelineError

    try:
        process_file(
            job_id=job_id,
            upload_file_id=upload_file_id,
            file_path=file_path,
        )

    except PipelineError as exc:
        logger.warning(
            "Processing job %s failed: %s",
            job_id,
            exc,
        )

    except Exception:
        logger.exception(
            "Unexpected error running processing job %s",
            job_id,
        )


# ---------------------------------------------------------------------
# MULTI-FILE PROCESSING
# ---------------------------------------------------------------------

def create_batch_jobs(
    file_ids: list[int],
    user_id: int,
) -> dict:
    """
    Create one isolated ProcessingBatch and one ProcessingJob per
    uploaded file.

    A ProcessingBatch is the isolation boundary for one processing
    operation.
    """

    if not file_ids:
        raise ValidationAPIError(
            "file_ids cannot be empty."
        )

    # Remove duplicate IDs while preserving order.
    unique_file_ids = list(
        dict.fromkeys(file_ids)
    )

    if not user_id:
        raise ValidationAPIError(
            "Authenticated user is required."
        )

    with session_scope() as session:
        files = (
            session.query(UploadFile)
            .filter(
                UploadFile.id.in_(unique_file_ids)
            )
            .all()
        )

        files_by_id = {
            file.id: file
            for file in files
        }

        missing_ids = [
            file_id
            for file_id in unique_file_ids
            if file_id not in files_by_id
        ]

        if missing_ids:
            raise NotFoundError(
                f"Files not found: {missing_ids}"
            )

        # Security: user can only process their own files.
        for file in files:
            if file.uploaded_by != user_id:
                raise ValidationAPIError(
                    f"You do not have permission to process "
                    f"file {file.id}."
                )

        # Create the isolation boundary.
        batch = ProcessingBatch(
            name=f"Processing Batch {len(unique_file_ids)} files",
            status=BatchStatus.QUEUED,
        )

        session.add(batch)
        session.flush()

        jobs = []

        for file_id in unique_file_ids:
            file = files_by_id[file_id]

            # Attach uploaded file to this processing batch.
            file.batch_id = batch.id

            job = ProcessingJob(
                upload_file_id=file.id,
                batch_id=batch.id,
                status=JobStatus.QUEUED,
            )

            session.add(job)
            session.flush()

            jobs.append(
                {
                    "job_id": job.id,
                    "file_id": file.id,
                    "file_path": file.stored_path,
                }
            )

        batch_id = batch.id

    # Run the complete batch in one background thread.
    thread = threading.Thread(
        target=run_batch,
        args=(jobs, batch_id),
        daemon=True,
    )

    thread.start()

    return {
        "message": (
            f"Batch processing started for "
            f"{len(jobs)} files."
        ),
        "batch_id": batch_id,
        "count": len(jobs),
        "jobs": [
            {
                "id": item["job_id"],
                "upload_file_id": item["file_id"],
                "status": "Queued",
            }
            for item in jobs
        ],
    }


def run_batch(
    jobs: list[dict],
    batch_id: int,
) -> None:
    """
    Process every file in one isolated processing batch.

    Customers produced by these jobs are assigned to this batch before
    cross-file merging. Customers from other processing batches are
    never included.
    """

    successful_file_ids = []

    try:
        # Mark the batch as running.
        with session_scope() as session:
            batch = session.get(
                ProcessingBatch,
                batch_id,
            )

            if batch is None:
                logger.error(
                    "Processing batch %s not found.",
                    batch_id,
                )
                return

            batch.status = BatchStatus.RUNNING

        # Process files sequentially.
        for item in jobs:
            try:
                from data_processing.pipeline.run import process_file

                process_file(
                    job_id=item["job_id"],
                    upload_file_id=item["file_id"],
                    file_path=item["file_path"],
                )

                with session_scope() as session:
                    job = session.get(
                        ProcessingJob,
                        item["job_id"],
                    )

                    if (
                        job
                        and job.status == JobStatus.COMPLETED
                    ):
                        # Find customers produced by this job.
                        source_rows = (
                            session.query(CustomerSource)
                            .filter(
                                CustomerSource.job_id
                                == item["job_id"]
                            )
                            .all()
                        )

                        customer_ids = {
                            source.customer_id
                            for source in source_rows
                            if source.customer_id is not None
                        }

                        # Assign those customers to this batch.
                        if customer_ids:
                            (
                                session.query(Customer)
                                .filter(
                                    Customer.id.in_(customer_ids)
                                )
                                .update(
                                    {
                                        Customer.batch_id: batch_id
                                    },
                                    synchronize_session=False,
                                )
                            )

                        successful_file_ids.append(
                            item["file_id"]
                        )

            except Exception:
                logger.exception(
                    "Batch processing failed for job %s",
                    item["job_id"],
                )

        # Merge only customers belonging to this batch.
        if successful_file_ids:
            try:
                merge_batch_customers(
                    successful_file_ids,
                    batch_id=batch_id,
                )
            except Exception:
                logger.exception(
                    "Cross-file customer merge failed "
                    "for files %s",
                    successful_file_ids,
                )

        # Determine final batch status.
        with session_scope() as session:
            batch = session.get(
                ProcessingBatch,
                batch_id,
            )

            if batch is None:
                return

            jobs_in_batch = (
                session.query(ProcessingJob)
                .filter(
                    ProcessingJob.batch_id == batch_id
                )
                .all()
            )

            if any(
                job.status == JobStatus.FAILED
                for job in jobs_in_batch
            ):
                batch.status = BatchStatus.FAILED
            else:
                batch.status = BatchStatus.COMPLETED

            from datetime import datetime

            batch.completed_at = datetime.utcnow()

    except Exception as exc:
        logger.exception(
            "Unexpected error running processing batch %s",
            batch_id,
        )

        with session_scope() as session:
            batch = session.get(
                ProcessingBatch,
                batch_id,
            )

            if batch is not None:
                batch.status = BatchStatus.FAILED
                batch.error_message = str(exc)

                from datetime import datetime

                batch.completed_at = datetime.utcnow()
# ---------------------------------------------------------------------
# CROSS-FILE CUSTOMER MERGING
# ---------------------------------------------------------------------

def _normalize(value) -> str | None:
    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    return value


def _customer_keys(customer: Customer) -> list[tuple]:
    """
    Build reliable identity keys.

    Priority:
        1. exact email
        2. exact phone
        3. full name + city
        4. first name + last name + city
    """

    keys = []

    email = _normalize(customer.email)

    if email:
        keys.append(
            ("email", email)
        )

    phone = _normalize(customer.phone)

    if phone:
        keys.append(
            ("phone", phone)
        )

    full_name = _normalize(customer.full_name)
    city = _normalize(customer.city)

    if full_name and city:
        keys.append(
            ("name_city", full_name, city)
        )

    first_name = _normalize(customer.first_name)
    last_name = _normalize(customer.last_name)

    if first_name and last_name and city:
        keys.append(
            (
                "person_city",
                first_name,
                last_name,
                city,
            )
        )

    return keys


def _merge_customer_values(
    primary: Customer,
    duplicate: Customer,
) -> None:
    """
    Fill missing values in the primary customer
    from the duplicate record.

    Existing non-empty primary values are never overwritten.
    """

    fields = [
        "email",
        "phone",
        "full_name",
        "first_name",
        "last_name",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        "country",
    ]

    for field in fields:
        primary_value = getattr(
            primary,
            field,
        )

        duplicate_value = getattr(
            duplicate,
            field,
        )

        if (
            (
                primary_value is None
                or str(primary_value).strip() == ""
            )
            and duplicate_value is not None
            and str(duplicate_value).strip() != ""
        ):
            setattr(
                primary,
                field,
                duplicate_value,
            )

    # Merge extra JSON fields.
    primary_extra = (
        primary.extra_fields or {}
    )

    duplicate_extra = (
        duplicate.extra_fields or {}
    )

    if isinstance(primary_extra, dict) and isinstance(
        duplicate_extra,
        dict,
    ):
        merged_extra = dict(
            duplicate_extra
        )

        merged_extra.update(
            primary_extra
        )

        primary.extra_fields = merged_extra

    primary.source_count = (
        (primary.source_count or 1)
        + (duplicate.source_count or 1)
    )


def merge_batch_customers(
    upload_file_ids: Iterable[int],
    batch_id: int | None = None,
) -> dict:
    """
    Merge customers that originated from the same
    multi-file processing batch.

    Duplicate records are retained for lineage but marked:

        is_duplicate = True
        merged_into_id = primary.id

    Their CustomerSource rows are moved to the
    primary customer.
    """

    upload_file_ids = list(
        dict.fromkeys(upload_file_ids)
    )

    if not upload_file_ids:
        return {
            "merged": 0,
            "unique": 0,
        }

    with session_scope() as session:

        source_rows = (
            session.query(CustomerSource)
            .filter(
                CustomerSource.upload_file_id.in_(
                    upload_file_ids
                )
            )
            .filter(
                CustomerSource.customer_id.isnot(None)
            )
            .all()
        )

        customer_ids = list(
            {
                source.customer_id
                for source in source_rows
                if source.customer_id is not None
            }
        )

        if not customer_ids:
            return {
                "merged": 0,
                "unique": 0,
            }

        customer_query = (
            session.query(Customer)
            .filter(
                Customer.id.in_(customer_ids)
            )
        )
        if batch_id is not None:
            customer_query = customer_query.filter(Customer.batch_id == batch_id)
        customers = (
            customer_query.order_by(Customer.id.asc()).all()
        )
        # key -> primary customer
        seen = {}

        merged_count = 0

        for customer in customers:

            # A record already merged by this operation
            # does not become another primary.
            if customer.is_duplicate:
                continue

            matched_primary = None

            for key in _customer_keys(customer):
                if key in seen:
                    matched_primary = seen[key]
                    break

            if matched_primary is None:
                for key in _customer_keys(customer):
                    seen[key] = customer

                continue

            if matched_primary.id == customer.id:
                continue

            # Keep the more complete record as primary.
            primary = matched_primary
            duplicate = customer

            def completeness(record):
                fields = [
                    record.email,
                    record.phone,
                    record.full_name,
                    record.first_name,
                    record.last_name,
                    record.city,
                    record.state,
                    record.country,
                ]

                return sum(
                    value is not None
                    and str(value).strip() != ""
                    for value in fields
                )

            if completeness(customer) > completeness(
                matched_primary
            ):
                primary = customer
                duplicate = matched_primary

            _merge_customer_values(
                primary,
                duplicate,
            )

            duplicate.is_duplicate = True
            duplicate.merged_into_id = primary.id

            # Move all source rows to the golden record.
            (
                session.query(CustomerSource)
                .filter(
                    CustomerSource.customer_id
                    == duplicate.id
                )
                .update(
                    {
                        CustomerSource.customer_id:
                            primary.id
                    },
                    synchronize_session=False,
                )
            )

            # Register the primary's keys.
            for key in _customer_keys(primary):
                seen[key] = primary

            merged_count += 1

        session.flush()

        unique_count = (
            session.query(Customer)
            .filter(
                Customer.id.in_(customer_ids)
            )
            .filter(
                Customer.is_duplicate.is_(False)
            )
            .count()
        )

        return {
            "merged": merged_count,
            "unique": unique_count,
        }


# ---------------------------------------------------------------------
# EXISTING JOB LOOKUP
# ---------------------------------------------------------------------

def get_job(job_id: int) -> dict:
    with session_scope() as session:
        job = session.get(
            ProcessingJob,
            job_id,
        )

        if job is None:
            raise NotFoundError(
                f"Processing job {job_id} not found."
            )

        data = to_dict(job)

    data["status"] = display_status(
        data["status"]
    )

    return data