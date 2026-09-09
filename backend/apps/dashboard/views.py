"""
backend/apps/dashboard/views.py

    GET /api/dashboard/metrics/

Aggregate statistics for the dashboard UI: total files, job
success/failure counts, average processing time, missing-data
percentage, validation error counts, duplicate counts, and current
processing status breakdown (PART 22 of the handoff).
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sqlalchemy import func

from common.db import session_scope
from database.schema.models import (
    Customer,
    DataQuality,
    JobStatus,
    ProcessingJob,
    UploadFile,
    ValidationError,
    ValidationSeverity,
)


class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        with session_scope() as session:
            total_files = session.query(func.count(UploadFile.id)).scalar() or 0

            status_counts = dict(
                session.query(ProcessingJob.status, func.count(ProcessingJob.id))
                .group_by(ProcessingJob.status)
                .all()
            )
            jobs_by_status = {
                "queued": status_counts.get(JobStatus.QUEUED, 0),
                "running": status_counts.get(JobStatus.RUNNING, 0),
                "completed": status_counts.get(JobStatus.COMPLETED, 0),
                "failed": status_counts.get(JobStatus.FAILED, 0),
            }
            total_jobs = sum(jobs_by_status.values())

            avg_duration = (
                session.query(func.avg(ProcessingJob.duration_seconds))
                .filter(ProcessingJob.status == JobStatus.COMPLETED)
                .scalar()
            )

            avg_missing_pct = session.query(func.avg(DataQuality.missing_pct)).scalar()

            error_count = (
                session.query(func.count(ValidationError.id))
                .filter(ValidationError.severity == ValidationSeverity.ERROR)
                .scalar() or 0
            )
            warning_count = (
                session.query(func.count(ValidationError.id))
                .filter(ValidationError.severity == ValidationSeverity.WARNING)
                .scalar() or 0
            )

            duplicate_rows_total = session.query(func.sum(DataQuality.duplicate_rows)).scalar() or 0
            duplicate_customers = (
                session.query(func.count(Customer.id))
                .filter(Customer.is_duplicate.is_(True))
                .scalar() or 0
            )

            total_customers = session.query(func.count(Customer.id)).scalar() or 0

        return Response({
            "total_files": total_files,
            "jobs": {
                "total": total_jobs,
                "queued": jobs_by_status["queued"],
                "running": jobs_by_status["running"],
                "completed": jobs_by_status["completed"],
                "failed": jobs_by_status["failed"],
            },
            "average_processing_time_seconds": round(avg_duration, 3) if avg_duration is not None else None,
            "missing_data_percentage": round(avg_missing_pct, 2) if avg_missing_pct is not None else None,
            "validation_errors": {
                "errors": error_count,
                "warnings": warning_count,
                "total": error_count + warning_count,
            },
            "duplicates": {
                "duplicate_rows_total": int(duplicate_rows_total),
                "duplicate_customers": duplicate_customers,
            },
            "total_customers": total_customers,
        })