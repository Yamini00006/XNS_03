"""
backend/apps/files/views.py

File upload + metadata endpoints.

Single file:
    POST   /api/files/upload/

Multiple files:
    POST   /api/files/upload-batch/

Metadata:
    GET    /api/files/
    GET    /api/files/{id}/
    DELETE /api/files/{id}/
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError
from common.pagination import paginate_list
from common.permissions import IsOwnerOrStaff
from common.query_params import parse_page

from database.schema.models import FileFormat, UploadFile
from data_processing.extractors.factory import get_extractor
from data_processing.schemas.detector import detect_schema

from .validators import (
    build_storage_path,
    safe_original_name,
    validate_extension,
    validate_size,
)


_ALLOWED_SORT_FIELDS = {
    "uploaded_at",
    "original_name",
    "file_size_bytes",
    "file_format",
}

MAX_BATCH_FILES = 20


def _save_uploaded_file(upload, request_user_id: int) -> dict:
    """
    Validate and store one uploaded file.

    Returns:
        {
            "record": UploadFile,
            "data": serialized record,
            "path": stored Path
        }
    """

    original_name = safe_original_name(upload.name)

    db_format = validate_extension(original_name)
    validate_size(upload.size)

    dest_path = build_storage_path(original_name)

    md5 = hashlib.md5()

    with open(dest_path, "wb") as out:
        for chunk in upload.chunks():
            md5.update(chunk)
            out.write(chunk)

    try:
        with session_scope() as session:
            record = UploadFile(
                original_name=original_name,
                stored_path=str(dest_path),
                file_format=FileFormat(db_format),
                file_size_bytes=upload.size,
                uploaded_by=request_user_id,
                uploaded_at=datetime.utcnow(),
                checksum_md5=md5.hexdigest(),
            )

            session.add(record)
            session.flush()

            data = to_dict(record)

    except Exception:
        if dest_path.exists():
            os.remove(dest_path)

        raise

    return {
        "record": record,
        "data": data,
        "path": dest_path,
    }


class FileUploadView(APIView):
    """
    POST /api/files/upload/

    Existing single-file upload endpoint.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")

        if upload is None:
            raise ValidationAPIError(
                "No file provided. Use multipart field name 'file'."
            )

        result = _save_uploaded_file(
            upload,
            request.user.id,
        )

        return Response(
            result["data"],
            status=status.HTTP_201_CREATED,
        )


class FileBatchUploadView(APIView):
    """
    POST /api/files/upload-batch/

    Multipart field:
        files

    Example:
        files=customers.csv
        files=customers.json
        files=customers.xlsx

    All files are uploaded as one customer-data batch.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploads = request.FILES.getlist("files")

        if not uploads:
            raise ValidationAPIError(
                "No files provided. Use multipart field name 'files'."
            )

        if len(uploads) > MAX_BATCH_FILES:
            raise ValidationAPIError(
                f"You can upload at most {MAX_BATCH_FILES} files in one batch."
            )

        uploaded_records = []
        stored_paths = []

        try:
            for upload in uploads:
                result = _save_uploaded_file(
                    upload,
                    request.user.id,
                )

                uploaded_records.append(result["data"])
                stored_paths.append(result["path"])

        except Exception:
            # Clean up files already written if a later file fails.
            for path in stored_paths:
                try:
                    if path.exists():
                        os.remove(path)
                except OSError:
                    pass

            raise

        return Response(
            {
                "message": f"{len(uploaded_records)} files uploaded successfully.",
                "count": len(uploaded_records),
                "files": uploaded_records,
            },
            status=status.HTTP_201_CREATED,
        )
class FileAttributeDiscoveryView(APIView):
    """
    POST /api/files/discover-attributes/

    Request:
    {
        "file_ids": [1, 2, 3]
    }

    Discovers the standardized attributes available across the
    uploaded files without starting processing.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get("file_ids")

        if not isinstance(file_ids, list) or not file_ids:
            raise ValidationAPIError(
                "'file_ids' must be a non-empty list."
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

        normalized_ids = list(dict.fromkeys(normalized_ids))

        with session_scope() as session:
            files = (
                session.query(UploadFile)
                .filter(
                    UploadFile.id.in_(normalized_ids),
                    UploadFile.uploaded_by == request.user.id,
                )
                .all()
            )

            files_by_id = {
                file.id: file
                for file in files
            }

            missing_ids = [
                file_id
                for file_id in normalized_ids
                if file_id not in files_by_id
            ]

            if missing_ids:
                raise NotFoundError(
                    f"Files not found: {missing_ids}"
                )

            discovered = {}

            for file_id in normalized_ids:
                file = files_by_id[file_id]

                try:
                    extractor = get_extractor(
                        file.stored_path
                    )

                    extraction = extractor.extract(
                        file.stored_path
                    )

                    if not extraction.rows:
                        continue

                    schema_mapping = detect_schema(
                        extraction.rows
                    )

                    for source_name, canonical_name in (
                        schema_mapping.column_map.items()
                    ):
                        if source_name.startswith("_"):
                            continue

                        key = canonical_name

                        if key not in discovered:
                            discovered[key] = {
                                "name": key,
                                "label": key.replace(
                                    "_", " "
                                ).title(),
                                "source_names": [],
                                "file_ids": [],
                            }

                        if (
                            source_name
                            not in discovered[key]["source_names"]
                        ):
                            discovered[key]["source_names"].append(
                                source_name
                            )

                        if (
                            file_id
                            not in discovered[key]["file_ids"]
                        ):
                            discovered[key]["file_ids"].append(
                                file_id
                            )

                except Exception as exc:
                    raise ValidationAPIError(
                        f"Unable to inspect "
                        f"{file.original_name}: {exc}"
                    )

        attributes = sorted(
            discovered.values(),
            key=lambda item: item["label"].lower(),
        )

        return Response(
            {
                "file_ids": normalized_ids,
                "count": len(attributes),
                "attributes": attributes,
            }
        )

class FileListView(APIView):
    """
    GET /api/files/

    Paginated list of uploaded files.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        page, page_size = parse_page(request)

        fmt_filter = request.query_params.get("format")

        mine_only = (
            request.query_params.get("mine", "").lower()
            in ("1", "true", "yes")
        )

        with session_scope() as session:
            query = session.query(UploadFile)

            if fmt_filter:
                try:
                    query = query.filter(
                        UploadFile.file_format == FileFormat(fmt_filter)
                    )
                except ValueError:
                    raise ValidationAPIError(
                        f"Invalid 'format' filter: {fmt_filter!r}."
                    )

            if mine_only:
                query = query.filter(
                    UploadFile.uploaded_by == request.user.id
                )

            total = query.count()

            rows = (
                query.order_by(
                    UploadFile.uploaded_at.desc()
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            results = [to_dict(row) for row in rows]

        meta = paginate_list(
            range(total),
            page,
            page_size,
        )

        meta["results"] = results

        return Response(meta)


class FileDetailView(APIView):
    """
    GET/DELETE /api/files/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id: int):
        with session_scope() as session:
            record = session.get(
                UploadFile,
                file_id,
            )

            if record is None:
                raise NotFoundError(
                    f"File {file_id} not found."
                )

            data = to_dict(record)

        return Response(data)

    def delete(self, request, file_id: int):
        permission = IsOwnerOrStaff()

        with session_scope() as session:
            record = session.get(
                UploadFile,
                file_id,
            )

            if record is None:
                raise NotFoundError(
                    f"File {file_id} not found."
                )

            if not permission.has_object_permission(
                request,
                self,
                record.uploaded_by,
            ):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    permission.message
                )

            stored_path = record.stored_path

            session.delete(record)

        if stored_path and os.path.exists(stored_path):
            try:
                os.remove(stored_path)
            except OSError:
                pass

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )