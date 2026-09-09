"""
backend/apps/processing/views.py

Processing APIs.

    POST /api/processing/<job_id>/start/
    GET  /api/processing/<job_id>/
    GET  /api/processing/<job_id>/errors/

    POST /api/processing/batch/start/
    GET  /api/processing/batch/status/

    GET  /api/processing/history/
    GET  /api/processing/history/<batch_id>/
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError
from common.pagination import paginate_list
from common.query_params import parse_page

from database.schema.models import (
    ProcessingBatch,
    ProcessingJob,
    UploadFile,
)

from . import services


class StartProcessingView(APIView):
    """
    POST /api/processing/<job_id>/start/

    Starts processing for a single existing processing job.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id: int):
        with session_scope() as session:
            job = session.get(
                ProcessingJob,
                job_id,
            )

            if job is None:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            upload_file = session.get(
                UploadFile,
                job.upload_file_id,
            )

            if upload_file is None:
                raise NotFoundError(
                    f"Upload file "
                    f"{job.upload_file_id} not found."
                )

            if upload_file.uploaded_by != request.user.id:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

        result = services.start_job(job_id)

        return Response(
            result,
            status=202,
        )


class ProcessingDetailView(APIView):
    """
    GET /api/processing/<job_id>/

    Returns processing-job details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        with session_scope() as session:
            job = session.get(
                ProcessingJob,
                job_id,
            )

            if job is None:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            upload_file = session.get(
                UploadFile,
                job.upload_file_id,
            )

            if upload_file is None:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            if upload_file.uploaded_by != request.user.id:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            data = to_dict(job)

        data["status"] = services.display_status(
            data.get("status")
        )

        return Response(data)


class ProcessingListView(APIView):
    """
    GET /api/processing/

    Lists processing jobs belonging to the authenticated user.

    Query parameters:
      page
      page_size
      status
      upload_file_id
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        page, page_size = parse_page(request)

        status = request.query_params.get(
            "status"
        )

        upload_file_id = request.query_params.get(
            "upload_file_id"
        )

        with session_scope() as session:
            query = (
                session.query(ProcessingJob)
                .join(
                    UploadFile,
                    UploadFile.id
                    == ProcessingJob.upload_file_id,
                )
                .filter(
                    UploadFile.uploaded_by
                    == request.user.id
                )
            )

            if status:
                status_value = status.strip().lower()

                allowed_statuses = {
                    "queued",
                    "running",
                    "completed",
                    "failed",
                }

                if status_value not in allowed_statuses:
                    raise ValidationAPIError(
                        "Invalid processing status."
                    )

                query = query.filter(
                    ProcessingJob.status
                    == status_value
                )

            if upload_file_id:
                try:
                    upload_file_id_value = int(
                        upload_file_id
                    )
                except ValueError:
                    raise ValidationAPIError(
                        "'upload_file_id' must be an integer."
                    )

                if upload_file_id_value <= 0:
                    raise ValidationAPIError(
                        "'upload_file_id' must be greater than zero."
                    )

                query = query.filter(
                    ProcessingJob.upload_file_id
                    == upload_file_id_value
                )

            total = query.count()

            rows = (
                query
                .order_by(
                    ProcessingJob.id.desc()
                )
                .offset(
                    (page - 1) * page_size
                )
                .limit(page_size)
                .all()
            )

            results = []

            for job in rows:
                item = to_dict(job)
                item["status"] = (
                    services.display_status(
                        item.get("status")
                    )
                )
                results.append(item)

        response = paginate_list(
            range(total),
            page,
            page_size,
        )

        response["results"] = results

        return Response(response)


class ProcessingErrorsView(APIView):
    """
    GET /api/processing/<job_id>/errors/

    Returns validation errors for a processing job.
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

            upload_file = session.get(
                UploadFile,
                job.upload_file_id,
            )

            if upload_file is None:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            if upload_file.uploaded_by != request.user.id:
                raise NotFoundError(
                    f"Processing job {job_id} not found."
                )

            errors = list(
                job.validation_errors
            )

            errors.sort(
                key=lambda item: item.id
            )

            total = len(errors)

            start = (
                page - 1
            ) * page_size

            end = start + page_size

            rows = errors[start:end]

            results = [
                to_dict(error)
                for error in rows
            ]

        response = paginate_list(
            range(total),
            page,
            page_size,
        )

        response["results"] = results

        return Response(response)


class StartBatchProcessingView(APIView):
    """
    POST /api/processing/batch/start/

    Starts processing for multiple uploaded files.

    Request:
    {
        "file_ids": [1, 2, 3],
        "requested_attributes": [
            "email",
            "full_name",
            "phone"
        ]
    }

    requested_attributes is optional.

    If it is omitted or empty, the existing pipeline processes
    all available attributes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get(
            "file_ids"
        )

        requested_attributes = request.data.get(
            "requested_attributes"
        )

        if not isinstance(
            file_ids,
            list,
        ) or not file_ids:
            raise ValidationAPIError(
                "'file_ids' must be a non-empty list."
            )

        if len(file_ids) > services.MAX_BATCH_FILES:
            raise ValidationAPIError(
                f"A maximum of "
                f"{services.MAX_BATCH_FILES} "
                f"files can be processed in one batch."
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

        normalized_ids = list(
            dict.fromkeys(
                normalized_ids
            )
        )

        if not normalized_ids:
            raise ValidationAPIError(
                "'file_ids' must contain at least one valid file."
            )

        if requested_attributes is not None:
            if not isinstance(
                requested_attributes,
                list,
            ):
                raise ValidationAPIError(
                    "'requested_attributes' must be a list."
                )

            if len(requested_attributes) > 50:
                raise ValidationAPIError(
                    "A maximum of 50 requested attributes "
                    "can be selected."
                )

            normalized_attributes = []

            for attribute in requested_attributes:
                if not isinstance(
                    attribute,
                    str,
                ):
                    raise ValidationAPIError(
                        "Every requested attribute "
                        "must be a string."
                    )

                attribute = attribute.strip()

                if not attribute:
                    continue

                normalized_attributes.append(
                    attribute
                )

            requested_attributes = list(
                dict.fromkeys(
                    normalized_attributes
                )
            )

        with session_scope() as session:
            files = (
                session.query(UploadFile)
                .filter(
                    UploadFile.id.in_(
                        normalized_ids
                    ),
                    UploadFile.uploaded_by
                    == request.user.id,
                )
                .all()
            )

            found_ids = {
                file.id
                for file in files
            }

            missing_ids = [
                file_id
                for file_id in normalized_ids
                if file_id not in found_ids
            ]

            if missing_ids:
                raise NotFoundError(
                    f"Files not found: {missing_ids}"
                )

        result = services.create_batch_jobs(
            normalized_ids,
            request.user.id,
            requested_attributes=requested_attributes,
        )

        return Response(
            result,
            status=202,
        )


class ProcessingBatchStatusView(APIView):
    """
    GET /api/processing/batch/status/?job_ids=1,2,3

    Returns the status of all jobs in a batch-processing workflow.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw_job_ids = request.query_params.get(
            "job_ids",
            "",
        ).strip()

        if not raw_job_ids:
            raise ValidationAPIError(
                "'job_ids' is required."
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
                    "'job_ids' must contain only integers."
                )

            if job_id <= 0:
                raise ValidationAPIError(
                    "Every job_id must be greater than zero."
                )

            job_ids.append(job_id)

        job_ids = list(
            dict.fromkeys(job_ids)
        )

        if not job_ids:
            raise ValidationAPIError(
                "'job_ids' must contain at least one job ID."
            )

        with session_scope() as session:
            rows = (
                session.query(ProcessingJob)
                .join(
                    UploadFile,
                    UploadFile.id
                    == ProcessingJob.upload_file_id,
                )
                .filter(
                    ProcessingJob.id.in_(job_ids),
                    UploadFile.uploaded_by
                    == request.user.id,
                )
                .all()
            )

            found_ids = {
                job.id
                for job in rows
            }

            missing_ids = [
                job_id
                for job_id in job_ids
                if job_id not in found_ids
            ]

            if missing_ids:
                raise NotFoundError(
                    f"Processing jobs not found: "
                    f"{missing_ids}"
                )

            results = []

            for job in rows:
                item = to_dict(job)

                item["status"] = (
                    services.display_status(
                        item.get("status")
                    )
                )

                results.append(item)

        results.sort(
            key=lambda item: job_ids.index(
                item["id"]
            )
        )

        completed = sum(
            1
            for item in results
            if item["status"]
            == "Completed"
        )

        failed = sum(
            1
            for item in results
            if item["status"]
            == "Failed"
        )

        running = sum(
            1
            for item in results
            if item["status"]
            == "Running"
        )

        queued = sum(
            1
            for item in results
            if item["status"]
            == "Queued"
        )

        return Response(
            {
                "total": len(results),
                "completed": completed,
                "failed": failed,
                "running": running,
                "queued": queued,
                "results": results,
            }
        )


class ProcessingBatchListView(APIView):
    """
    GET /api/processing/history/

    Returns processing history for the authenticated user.

    Each ProcessingBatch represents one isolated processing
    operation/dataset.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        page, page_size = parse_page(request)

        with session_scope() as session:
            query = (
                session.query(ProcessingBatch)
                .join(
                    UploadFile,
                    UploadFile.batch_id
                    == ProcessingBatch.id,
                )
                .filter(
                    UploadFile.uploaded_by
                    == request.user.id
                )
                .distinct()
            )

            total = query.count()

            batches = (
                query
                .order_by(
                    ProcessingBatch.created_at.desc()
                )
                .offset(
                    (page - 1) * page_size
                )
                .limit(page_size)
                .all()
            )

            results = []

            for batch in batches:
                item = to_dict(batch)

                item["status"] = (
                    services.display_batch_status(
                        item.get("status")
                    )
                )

                item["file_count"] = (
                    session.query(UploadFile)
                    .filter(
                        UploadFile.batch_id
                        == batch.id
                    )
                    .count()
                )

                item["job_count"] = (
                    session.query(ProcessingJob)
                    .filter(
                        ProcessingJob.batch_id
                        == batch.id
                    )
                    .count()
                )

                results.append(item)

        response = paginate_list(
            range(total),
            page,
            page_size,
        )

        response["results"] = results

        return Response(response)


class ProcessingBatchDetailView(APIView):
    """
    GET /api/processing/history/<batch_id>/

    Returns details of one isolated processing batch.
    """

    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        batch_id: int,
    ):
        with session_scope() as session:
            batch = (
                session.query(ProcessingBatch)
                .join(
                    UploadFile,
                    UploadFile.batch_id
                    == ProcessingBatch.id,
                )
                .filter(
                    ProcessingBatch.id
                    == batch_id,
                    UploadFile.uploaded_by
                    == request.user.id,
                )
                .first()
            )

            if batch is None:
                raise NotFoundError(
                    f"Processing batch "
                    f"{batch_id} not found."
                )

            data = to_dict(batch)

            data["status"] = (
                services.display_batch_status(
                    data.get("status")
                )
            )

            files = (
                session.query(UploadFile)
                .filter(
                    UploadFile.batch_id
                    == batch.id
                )
                .order_by(
                    UploadFile.id.asc()
                )
                .all()
            )

            jobs = (
                session.query(ProcessingJob)
                .filter(
                    ProcessingJob.batch_id
                    == batch.id
                )
                .order_by(
                    ProcessingJob.id.asc()
                )
                .all()
            )

            data["file_count"] = len(files)
            data["job_count"] = len(jobs)

            data["files"] = [
                to_dict(file)
                for file in files
            ]

            data["jobs"] = []

            for job in jobs:
                job_data = to_dict(job)

                job_data["status"] = (
                    services.display_status(
                        job_data.get("status")
                    )
                )

                data["jobs"].append(
                    job_data
                )

        return Response(data)