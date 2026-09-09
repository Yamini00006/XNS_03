from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError
from common.pagination import paginate_list
from common.query_params import parse_page

from database.schema.models import (
    JobStatus,
    ProcessingJob,
    ValidationError,
)

from . import services


class StartProcessingView(APIView):
    """
    POST /api/processing/{file_id}/start/

    Existing single-file processing endpoint.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, file_id: int):
        job = services.create_job(file_id)

        return Response(
            job,
            status=status.HTTP_202_ACCEPTED,
        )


class StartBatchProcessingView(APIView):
    """
    POST /api/processing/batch/start/

    Request:

    {
        "file_ids": [1, 2, 3]
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get("file_ids")

        if not isinstance(file_ids, list):
            raise ValidationAPIError(
                "'file_ids' must be a list."
            )

        if not file_ids:
            raise ValidationAPIError(
                "'file_ids' cannot be empty."
            )

        normalized_ids = []

        for value in file_ids:
            try:
                file_id = int(value)
            except (TypeError, ValueError):
                raise ValidationAPIError(
                    "Every file_id must be an integer."
                )

            if file_id <= 0:
                raise ValidationAPIError(
                    "Every file_id must be greater than zero."
                )

            normalized_ids.append(file_id)

        result = services.create_batch_jobs(
            normalized_ids,
            request.user.id,
        )

        return Response(
            result,
            status=status.HTTP_202_ACCEPTED,
        )


class ProcessingBatchStatusView(APIView):
    """
    GET /api/processing/batch/status/?job_ids=1,2,3

    Returns the current status of all jobs in a batch.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw_job_ids = request.query_params.get(
            "job_ids",
            "",
        ).strip()

        if not raw_job_ids:
            raise ValidationAPIError(
                "'job_ids' query parameter is required."
            )

        job_ids = []

        for value in raw_job_ids.split(","):
            value = value.strip()

            if not value:
                continue

            try:
                job_id = int(value)
            except ValueError:
                raise ValidationAPIError(
                    "job_ids must contain only integers."
                )

            if job_id <= 0:
                raise ValidationAPIError(
                    "job_ids must contain positive integers."
                )

            job_ids.append(job_id)

        if not job_ids:
            raise ValidationAPIError(
                "No valid job IDs provided."
            )

        with session_scope() as session:
            jobs = (
                session.query(ProcessingJob)
                .filter(
                    ProcessingJob.id.in_(job_ids)
                )
                .order_by(
                    ProcessingJob.id.asc()
                )
                .all()
            )

            results = []

            for job in jobs:
                data = to_dict(job)

                data["status"] = services.display_status(
                    data["status"]
                )

                results.append(data)

        completed = sum(
            job["status"] == "Completed"
            for job in results
        )

        failed = sum(
            job["status"] == "Failed"
            for job in results
        )

        running = sum(
            job["status"] == "Running"
            for job in results
        )

        queued = sum(
            job["status"] == "Queued"
            for job in results
        )

        if failed:
            batch_status = "Failed"
        elif completed == len(job_ids):
            batch_status = "Completed"
        elif running:
            batch_status = "Running"
        else:
            batch_status = "Queued"

        return Response(
            {
                "status": batch_status,
                "total": len(job_ids),
                "completed": completed,
                "failed": failed,
                "running": running,
                "queued": queued,
                "jobs": results,
            }
        )


class ProcessingDetailView(APIView):
    """
    GET /api/processing/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        return Response(
            services.get_job(job_id)
        )


class ProcessingListView(APIView):
    """
    GET /api/processing/
    """

    permission_classes = [IsAuthenticated]

    _REVERSE_STATUS = {
        value: key
        for key, value in services.STATUS_DISPLAY.items()
    }

    def get(self, request):
        page, page_size = parse_page(request)

        status_filter = request.query_params.get(
            "status"
        )

        upload_file_id = request.query_params.get(
            "upload_file_id"
        )

        with session_scope() as session:
            query = session.query(
                ProcessingJob
            )

            if status_filter:
                raw = self._REVERSE_STATUS.get(
                    status_filter,
                    status_filter.lower(),
                )

                try:
                    query = query.filter(
                        ProcessingJob.status
                        == JobStatus(raw)
                    )

                except ValueError:
                    raise ValidationAPIError(
                        f"Invalid 'status' filter: "
                        f"{status_filter!r}. "
                        f"Allowed: "
                        f"{list(services.STATUS_DISPLAY.values())}."
                    )

            if upload_file_id:
                try:
                    query = query.filter(
                        ProcessingJob.upload_file_id
                        == int(upload_file_id)
                    )
                except ValueError:
                    raise ValidationAPIError(
                        "'upload_file_id' must be an integer."
                    )

            total = query.count()

            rows = (
                query.order_by(
                    ProcessingJob.id.desc()
                )
                .offset(
                    (page - 1) * page_size
                )
                .limit(page_size)
                .all()
            )

            results = [
                to_dict(row)
                for row in rows
            ]

        for row in results:
            row["status"] = services.display_status(
                row["status"]
            )

        meta = paginate_list(
            range(total),
            page,
            page_size,
        )

        meta["results"] = results

        return Response(meta)


class ProcessingErrorsView(APIView):
    """
    GET /api/processing/{id}/errors/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        page, page_size = parse_page(request)

        with session_scope() as session:

            job = session.get(
                ProcessingJob,
                job_id,
            )

            if job is None:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            query = (
                session.query(ValidationError)
                .filter(
                    ValidationError.job_id
                    == job_id
                )
            )

            total = query.count()

            rows = (
                query.order_by(
                    ValidationError.id.asc()
                )
                .offset(
                    (page - 1) * page_size
                )
                .limit(page_size)
                .all()
            )

            results = [
                to_dict(row)
                for row in rows
            ]

        meta = paginate_list(
            range(total),
            page,
            page_size,
        )

        meta["results"] = results

        return Response(meta)