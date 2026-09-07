"""
backend/apps/processing/views.py

    POST /api/processing/{file_id}/start/   — create a job & start processing
    GET  /api/processing/{id}/              — job status/detail
    GET  /api/processing/                   — list jobs (paginated, filterable)
    GET  /api/processing/{id}/errors/       — validation errors for a job
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError
from common.pagination import paginate_list
from common.query_params import parse_page

from database.schema.models import JobStatus, ProcessingJob, ValidationError

from . import services


class StartProcessingView(APIView):
    """POST /api/processing/{file_id}/start/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id: int):
        job = services.create_job(file_id)
        return Response(job, status=status.HTTP_202_ACCEPTED)


class ProcessingDetailView(APIView):
    """GET /api/processing/{id}/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        return Response(services.get_job(job_id))


class ProcessingListView(APIView):
    """GET /api/processing/ — optional ?status=Queued|Running|Completed|Failed&upload_file_id=<int>"""
    permission_classes = [IsAuthenticated]

    _REVERSE_STATUS = {v: k for k, v in services.STATUS_DISPLAY.items()}

    def get(self, request):
        page, page_size = parse_page(request)
        status_filter = request.query_params.get("status")
        upload_file_id = request.query_params.get("upload_file_id")

        with session_scope() as session:
            query = session.query(ProcessingJob)

            if status_filter:
                raw = self._REVERSE_STATUS.get(status_filter, status_filter.lower())
                try:
                    query = query.filter(ProcessingJob.status == JobStatus(raw))
                except ValueError:
                    raise ValidationAPIError(
                        f"Invalid 'status' filter: {status_filter!r}. "
                        f"Allowed: {list(services.STATUS_DISPLAY.values())}."
                    )

            if upload_file_id:
                try:
                    query = query.filter(ProcessingJob.upload_file_id == int(upload_file_id))
                except ValueError:
                    raise ValidationAPIError("'upload_file_id' must be an integer.")

            total = query.count()
            rows = (
                query.order_by(ProcessingJob.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            results = [to_dict(r) for r in rows]

        for r in results:
            r["status"] = services.display_status(r["status"])

        meta = paginate_list(range(total), page, page_size)
        meta["results"] = results
        return Response(meta)


class ProcessingErrorsView(APIView):
    """GET /api/processing/{id}/errors/ — paginated validation_errors for this job."""
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        page, page_size = parse_page(request)

        with session_scope() as session:
            job = session.get(ProcessingJob, job_id)
            if job is None:
                raise NotFoundError(f"Processing job {job_id} not found.")

            query = session.query(ValidationError).filter(ValidationError.job_id == job_id)
            total = query.count()
            rows = (
                query.order_by(ValidationError.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            results = [to_dict(r) for r in rows]

        meta = paginate_list(range(total), page, page_size)
        meta["results"] = results
        return Response(meta)