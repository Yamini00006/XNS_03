"""
data_processing/pipeline/pipeline.py

Orchestrates the full ETL pipeline for one uploaded file:

  1. EXTRACT   — read raw rows from the file
  2. TRANSFORM — map schema + clean/normalize fields
  3. VALIDATE  — check field values against business rules
  4. MERGE     — deduplicate within this file's batch
  5. LOAD      — write to database

The pipeline is designed to be called by the background worker (Member 4).
The worker creates a ProcessingJob row, then calls:

    result = Pipeline(session).run(job_id, upload_file_id, file_path)

The pipeline updates the job's status throughout.

On failure the job is marked FAILED and the exception is re-raised
so the worker can log it at the infrastructure level.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config.settings import PIPELINE_VERSION
from ..extractors.factory import get_extractor
from ..transformers.transformer import Transformer
from ..validators.validator import Validator
from ..merger.merger import Merger
from ..loaders.loader import Loader
from ..schemas.detector import detect_schema

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from database.schema.models import JobStatus, ProcessingJob


@dataclass
class PipelineResult:
    """Summary returned to the caller (background worker / tests)."""
    job_id:          int
    status:          str
    rows_extracted:  int
    rows_valid:      int
    rows_invalid:    int
    rows_merged:     int      # duplicates found
    duration_seconds: float
    error_message:   str | None = None


class Pipeline:
    """
    Full ETL pipeline for one file.

    Args:
        session : open SQLAlchemy session. The pipeline commits on success
                  and rolls back on failure.
    """

    def __init__(self, session: Session):
        self.session = session

    def run(
        self,
        job_id:         int,
        upload_file_id: int,
        file_path:      str | Path,
    ) -> PipelineResult:
        """
        Run the full pipeline for a single file.

        Returns PipelineResult with final counts and status.
        Raises PipelineError on unrecoverable failure (job is marked FAILED first).
        """
        file_path  = Path(file_path)
        started_at = datetime.utcnow()
        loader     = Loader(self.session, job_id, upload_file_id)

        # Mark job as RUNNING
        loader.update_job(
            status     = JobStatus.RUNNING,
            started_at = started_at,
        )
        self.session.commit()

        try:
            result = self._run_stages(file_path, loader, job_id, upload_file_id, started_at)
            self.session.commit()
            return result

        except Exception as exc:
            self.session.rollback()
            error_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            # Re-open connection after rollback to update job status
            try:
                loader.update_job(
                    status        = JobStatus.FAILED,
                    error_message = str(exc)[:2000],
                    completed_at  = datetime.utcnow(),
                )
                loader._log("ERROR", "pipeline", f"Pipeline failed: {exc}")
                self.session.commit()
            except Exception:
                pass  # if we can't even update status, let the worker handle it
            raise PipelineError(str(exc)) from exc

    # ─── Internal stages ──────────────────────────────────────

    def _run_stages(
        self,
        file_path:      Path,
        loader:         Loader,
        job_id:         int,
        upload_file_id: int,
        started_at:     datetime,
    ) -> PipelineResult:

        # ── 1. EXTRACT ────────────────────────────────────────
        loader._log("INFO", "extract", f"Starting extraction: {file_path.name}")
        extractor = get_extractor(file_path)
        extraction = extractor.extract(file_path)

        if extraction.errors:
            for err in extraction.errors:
                loader._log("WARNING", "extract", err)

        raw_rows = extraction.rows
        loader._log("INFO", "extract", f"Extracted {len(raw_rows)} rows")

        if not raw_rows:
            completed_at = datetime.utcnow()
            loader.update_job(
                status        = JobStatus.COMPLETED,
                rows_extracted = 0,
                completed_at  = completed_at,
                started_at    = started_at,
                error_message = "No rows extracted from file",
            )
            return PipelineResult(
                job_id=job_id, status="completed",
                rows_extracted=0, rows_valid=0, rows_invalid=0, rows_merged=0,
                duration_seconds=(completed_at - started_at).total_seconds(),
                error_message="No rows extracted",
            )

        # ── 2. DETECT SCHEMA ─────────────────────────────────
        loader._log("INFO", "extract", "Detecting schema...")
        schema_mapping = detect_schema(raw_rows)
        loader._log(
            "INFO", "extract",
            f"Schema: {len(schema_mapping.column_map)} columns mapped, "
            f"{len(schema_mapping.unknown_cols)} unknown",
            detail=schema_mapping.summary(),
        )

        # ── 3. TRANSFORM ─────────────────────────────────────
        loader._log("INFO", "transform", "Transforming rows...")
        transformer     = Transformer()
        transform_result = transformer.transform(raw_rows, schema_mapping)

        for warn in transform_result.warnings:
            loader._log("WARNING", "transform", f"Row {warn.row_number} [{warn.field_name}]: {warn.message}")

        transformed_rows = transform_result.rows
        loader._log("INFO", "transform", f"Transformed {len(transformed_rows)} rows")

        # ── 4. VALIDATE ───────────────────────────────────────
        loader._log("INFO", "validate", "Validating rows...")
        validator         = Validator()
        validation_result = validator.validate(transformed_rows)

        loader._log(
            "INFO", "validate",
            f"Validation: {len(validation_result.valid_rows)} valid, "
            f"{len(validation_result.invalid_rows)} invalid, "
            f"{validation_result.error_count} errors, "
            f"{validation_result.warning_count} warnings",
        )

        # ── 5. MERGE (dedup within batch) ─────────────────────
        loader._log("INFO", "merge", "Deduplicating...")
        merger       = Merger()
        merge_result = merger.merge(validation_result.valid_rows)

        loader._log(
            "INFO", "merge",
            f"Merge: {merge_result.unique_count} unique, "
            f"{merge_result.duplicate_count} duplicates removed",
        )

        # ── 6. LOAD ───────────────────────────────────────────
        loader._log("INFO", "load", "Loading into database...")

        # 6a. Source rows (lineage) for ALL raw rows
        mapped_rows = [schema_mapping.apply(r) for r in raw_rows]
        source_ids  = loader.load_sources(raw_rows, mapped_rows)

        # 6b. Validation errors
        loader.load_validation_errors(validation_result, source_ids, raw_rows)

        # 6c. Customer golden records (only valid, deduped rows)
        loader.load_customers(merge_result, source_ids, raw_rows)

        # 6d. Data quality aggregate
        loader.load_quality_report(validation_result, merge_result, len(raw_rows))

        # 6e. Final job update
        completed_at = datetime.utcnow()
        loader.update_job(
            status         = JobStatus.COMPLETED,
            rows_extracted = len(raw_rows),
            rows_valid     = len(validation_result.valid_rows),
            rows_invalid   = len(validation_result.invalid_rows),
            rows_merged    = merge_result.duplicate_count,
            started_at     = started_at,
            completed_at   = completed_at,
        )

        duration = (completed_at - started_at).total_seconds()
        loader._log("INFO", "pipeline", f"Pipeline completed in {duration:.2f}s")

        return PipelineResult(
            job_id           = job_id,
            status           = "completed",
            rows_extracted   = len(raw_rows),
            rows_valid       = len(validation_result.valid_rows),
            rows_invalid     = len(validation_result.invalid_rows),
            rows_merged      = merge_result.duplicate_count,
            duration_seconds = duration,
        )


class PipelineError(Exception):
    """Raised when the pipeline fails unrecoverably."""
    pass
