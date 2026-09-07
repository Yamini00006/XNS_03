"""
data_processing/loaders/loader.py

Loads pipeline output into the database.

Responsibilities:
  - Insert/update Customer golden records
  - Insert CustomerSource rows (data lineage)
  - Insert ValidationError rows
  - Insert DataQuality aggregate
  - Write ProcessingLog entries
  - Update ProcessingJob status and counters

Uses batched inserts for performance (LOADER_BATCH_SIZE from settings).
Does NOT commit within this module — the pipeline (orchestrator) owns transactions.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..config.settings import LOADER_BATCH_SIZE
from ..validators.validator import ValidationResult, ValidationIssue
from ..merger.merger import MergeResult
from ..schemas.detector import SchemaMapping


# Import DB models — these live in database/schema/models.py
# (Member 3 owns both data_processing/ and database/)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from database.schema.models import (
    Customer, CustomerSource, ValidationError,
    DataQuality, ProcessingLog, ProcessingJob,
    JobStatus, ValidationSeverity,
)

# Fields that map directly to Customer columns
_CUSTOMER_COLUMNS = {
    "email", "phone", "full_name", "first_name", "last_name",
    "address_line1", "address_line2", "city", "state",
    "postal_code", "country",
}

_META_KEYS = {
    "_source_row", "_source_sheet", "_source_page", "_raw_text",
    "_transform_failed", "_validation_errors", "source_count",
}


def _split_customer_fields(row: dict[str, Any]) -> tuple[dict, dict]:
    """
    Split a transformed row into:
      - known_fields : fields that map to Customer columns
      - extra_fields : everything else (stored in Customer.extra_fields JSON)
    """
    known: dict = {}
    extra: dict = {}
    for k, v in row.items():
        if k in _META_KEYS:
            continue
        if k in _CUSTOMER_COLUMNS:
            known[k] = v
        else:
            extra[k] = v
    return known, extra


class Loader:
    """
    Writes ETL pipeline output to the database.

    Args:
        session        : open SQLAlchemy session (caller manages commit/rollback)
        job_id         : ID of the ProcessingJob this load belongs to
        upload_file_id : ID of the UploadFile
    """

    def __init__(self, session: Session, job_id: int, upload_file_id: int):
        self.session        = session
        self.job_id         = job_id
        self.upload_file_id = upload_file_id

    # ─── Public API ───────────────────────────────────────────

    def load_sources(
        self,
        raw_rows: list[dict[str, Any]],
        mapped_rows: list[dict[str, Any]],
    ) -> list[int]:
        """
        Insert CustomerSource rows (raw + mapped data for lineage).
        Returns list of inserted source IDs in the same order as raw_rows.
        """
        source_ids: list[int] = []

        for batch_start in range(0, len(raw_rows), LOADER_BATCH_SIZE):
            batch_raw    = raw_rows[batch_start : batch_start + LOADER_BATCH_SIZE]
            batch_mapped = mapped_rows[batch_start : batch_start + LOADER_BATCH_SIZE]

            objs = []
            for raw, mapped in zip(batch_raw, batch_mapped):
                src = CustomerSource(
                    job_id         = self.job_id,
                    upload_file_id = self.upload_file_id,
                    source_row_num = raw.get("_source_row"),
                    raw_data       = {k: str(v) if v is not None else None
                                      for k, v in raw.items()},
                    mapped_data    = mapped,
                    is_valid       = True,
                    extracted_at   = datetime.utcnow(),
                )
                objs.append(src)

            self.session.add_all(objs)
            self.session.flush()   # get IDs without committing
            source_ids.extend(obj.id for obj in objs)

        self._log("INFO", "extract", f"Inserted {len(source_ids)} source rows")
        return source_ids

    def load_customers(
        self,
        merge_result: MergeResult,
        source_ids: list[int],
        raw_rows: list[dict[str, Any]],
    ) -> None:
        """
        Insert Customer golden records and link them to their source rows.
        """
        customers_created = 0

        for batch_start in range(0, len(merge_result.merged_rows), LOADER_BATCH_SIZE):
            batch = merge_result.merged_rows[batch_start : batch_start + LOADER_BATCH_SIZE]

            for row in batch:
                known, extra = _split_customer_fields(row)
                customer = Customer(
                    source_count = row.get("source_count", 1),
                    extra_fields = extra if extra else None,
                    created_at   = datetime.utcnow(),
                    updated_at   = datetime.utcnow(),
                    **known,
                )
                self.session.add(customer)
                self.session.flush()

                # Link the source row(s) that contributed to this customer
                src_row_num = row.get("_source_row")
                for i, raw in enumerate(raw_rows):
                    if raw.get("_source_row") == src_row_num and i < len(source_ids):
                        src_obj = self.session.get(CustomerSource, source_ids[i])
                        if src_obj:
                            src_obj.customer_id = customer.id

                customers_created += 1

        self._log("INFO", "load", f"Inserted {customers_created} customer records")

    def load_validation_errors(
        self,
        validation_result: ValidationResult,
        source_ids: list[int],
        raw_rows: list[dict[str, Any]],
    ) -> None:
        """Persist all validation issues to the validation_errors table."""
        if not validation_result.issues:
            return

        objs = []
        # Build row_num → source_id lookup
        row_to_src: dict[int, int] = {}
        for i, raw in enumerate(raw_rows):
            rn = raw.get("_source_row", 0)
            if i < len(source_ids):
                row_to_src[rn] = source_ids[i]

        for issue in validation_result.issues:
            severity = (ValidationSeverity.ERROR
                        if issue.severity == "error"
                        else ValidationSeverity.WARNING)
            objs.append(ValidationError(
                job_id        = self.job_id,
                source_row_id = row_to_src.get(issue.row_number),
                row_number    = issue.row_number,
                field_name    = issue.field_name,
                error_code    = issue.error_code,
                error_message = issue.error_message,
                severity      = severity,
                raw_value     = issue.raw_value,
                created_at    = datetime.utcnow(),
            ))

        for batch_start in range(0, len(objs), LOADER_BATCH_SIZE):
            self.session.add_all(objs[batch_start : batch_start + LOADER_BATCH_SIZE])
            self.session.flush()

        self._log("INFO", "validate", f"Recorded {len(objs)} validation issues")

    def load_quality_report(
        self,
        validation_result: ValidationResult,
        merge_result: MergeResult,
        total_extracted: int,
    ) -> None:
        """Compute and persist data quality aggregate for this job."""
        total    = total_extracted
        valid    = len(validation_result.valid_rows)
        invalid  = len(validation_result.invalid_rows)
        dupes    = merge_result.duplicate_count

        # Missing fields: count null values across all valid rows
        tracked_fields = list(_CUSTOMER_COLUMNS)
        missing_count  = 0
        for row in validation_result.valid_rows:
            for f in tracked_fields:
                if row.get(f) is None:
                    missing_count += 1

        total_field_slots = valid * len(tracked_fields) if valid else 1
        missing_pct       = (missing_count / total_field_slots) * 100

        completeness = max(0.0, 100.0 - missing_pct)
        uniqueness   = ((total - dupes) / total * 100) if total else 100.0

        quality = DataQuality(
            job_id                 = self.job_id,
            total_rows             = total,
            valid_rows             = valid,
            invalid_rows           = invalid,
            duplicate_rows         = dupes,
            missing_fields_count   = missing_count,
            missing_pct            = round(missing_pct, 2),
            validation_error_count = validation_result.error_count,
            completeness_score     = round(completeness, 2),
            uniqueness_score       = round(uniqueness, 2),
            computed_at            = datetime.utcnow(),
        )
        self.session.add(quality)
        self.session.flush()
        self._log("INFO", "load", f"Quality — completeness={completeness:.1f}% uniqueness={uniqueness:.1f}%")

    def update_job(
        self,
        status: JobStatus,
        rows_extracted: int = 0,
        rows_valid: int = 0,
        rows_invalid: int = 0,
        rows_merged: int = 0,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update the ProcessingJob record."""
        job = self.session.get(ProcessingJob, self.job_id)
        if not job:
            return
        job.status        = status
        job.rows_extracted = rows_extracted
        job.rows_valid    = rows_valid
        job.rows_invalid  = rows_invalid
        job.rows_merged   = rows_merged
        job.error_message = error_message
        if started_at:
            job.started_at  = started_at
        if completed_at:
            job.completed_at = completed_at
            if job.started_at:
                job.duration_seconds = (completed_at - job.started_at).total_seconds()
        self.session.flush()

    # ─── Internal helpers ─────────────────────────────────────

    def _log(self, level: str, stage: str, message: str, detail: dict | None = None) -> None:
        """Write a structured log line for this job."""
        entry = ProcessingLog(
            job_id    = self.job_id,
            level     = level,
            stage     = stage,
            message   = message,
            detail    = detail,
            logged_at = datetime.utcnow(),
        )
        self.session.add(entry)
        # Don't flush here — keep batched with surrounding work
