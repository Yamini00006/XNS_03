"""
data_processing/pipeline/run.py

Public entry point for the background worker (Member 4).

The worker calls:

    from data_processing.pipeline.run import process_file

    result = process_file(
        job_id=1,
        upload_file_id=1,
        file_path="/path/to/uploaded/file.csv",
    )

This function:
  - Opens its own DB session
  - Runs the full ETL pipeline
  - Commits on success / rolls back on failure
  - Returns a PipelineResult dict (JSON-serializable)

The worker does NOT need to know about SQLAlchemy sessions, models, or
the internal pipeline stages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .pipeline import Pipeline, PipelineResult

# ── Lazy import to avoid circular deps ────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def process_file(
    job_id:         int,
    upload_file_id: int,
    file_path:      str | Path,
    requested_attributes: list[str] | None = None,

) -> dict[str, Any]:
    """
    Run the ETL pipeline for one file.

    Args:
        job_id         : ID of the ProcessingJob (must already exist in DB as QUEUED)
        upload_file_id : ID of the UploadFile
        file_path      : absolute path to the file on disk

    Returns:
        dict with keys: job_id, status, rows_extracted, rows_valid,
                        rows_invalid, rows_merged, duration_seconds, error_message

    Raises:
        PipelineError if the pipeline fails (job is marked FAILED in DB first)
    """
    from database.schema.connection import get_session

    session = get_session()
    try:
        pipeline = Pipeline(session)
        result   = pipeline.run(job_id, upload_file_id, file_path,    requested_attributes=requested_attributes,
)
        return _result_to_dict(result)
    finally:
        session.close()


def _result_to_dict(result: PipelineResult) -> dict[str, Any]:
    return {
        "job_id":           result.job_id,
        "status":           result.status,
        "rows_extracted":   result.rows_extracted,
        "rows_valid":       result.rows_valid,
        "rows_invalid":     result.rows_invalid,
        "rows_merged":      result.rows_merged,
        "duration_seconds": result.duration_seconds,
        "error_message":    result.error_message,
    }
