"""
backend/apps/files/views.py

File upload + metadata endpoints.

    POST   /api/files/upload/   — upload a CSV/JSON/NDJSON/XLSX/XML/PDF file
    GET    /api/files/          — list uploaded files (paginated)
    GET    /api/files/{id}/     — file metadata
    DELETE /api/files/{id}/     — delete a file record (+ its stored copy)

This app never runs extraction/parsing itself — it only stores the file
and a metadata row. Processing is started explicitly via
POST /api/processing/{file_id}/start/ (see apps/processing).
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

from .validators import (
    build_storage_path,
    safe_original_name,
    validate_extension,
    validate_size,
)

_ALLOWED_SORT_FIELDS = {"uploaded_at", "original_name", "file_size_bytes", "file_format"}


class FileUploadView(APIView):
    """POST /api/files/upload/ — multipart/form-data, field name 'file'."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationAPIError("No file provided. Use multipart field name 'file'.")

        original_name = safe_original_name(upload.name)
        db_format = validate_extension(original_name)   # raises UnsupportedFileTypeError
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
                    uploaded_by=request.user.id,
                    uploaded_at=datetime.utcnow(),
                    checksum_md5=md5.hexdigest(),
                )
                session.add(record)
                session.flush()
                data = to_dict(record)
        except Exception:
            # Roll back the file we already wrote to disk if the DB insert failed.
            if dest_path.exists():
                os.remove(dest_path)
            raise

        return Response(data, status=status.HTTP_201_CREATED)


class FileListView(APIView):
    """GET /api/files/ — paginated list, newest first. Optional ?format=csv&mine=true"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page, page_size = parse_page(request)
        fmt_filter = request.query_params.get("format")
        mine_only = request.query_params.get("mine", "").lower() in ("1", "true", "yes")

        with session_scope() as session:
            query = session.query(UploadFile)
            if fmt_filter:
                try:
                    query = query.filter(UploadFile.file_format == FileFormat(fmt_filter))
                except ValueError:
                    raise ValidationAPIError(f"Invalid 'format' filter: {fmt_filter!r}.")
            if mine_only:
                query = query.filter(UploadFile.uploaded_by == request.user.id)

            total = query.count()
            rows = (
                query.order_by(UploadFile.uploaded_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            results = [to_dict(r) for r in rows]

        meta = paginate_list(range(total), page, page_size)
        meta["results"] = results
        return Response(meta)


class FileDetailView(APIView):
    """GET/DELETE /api/files/{id}/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id: int):
        with session_scope() as session:
            record = session.get(UploadFile, file_id)
            if record is None:
                raise NotFoundError(f"File {file_id} not found.")
            data = to_dict(record)
        return Response(data)

    def delete(self, request, file_id: int):
        permission = IsOwnerOrStaff()
        with session_scope() as session:
            record = session.get(UploadFile, file_id)
            if record is None:
                raise NotFoundError(f"File {file_id} not found.")

            if not permission.has_object_permission(request, self, record.uploaded_by):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(permission.message)

            stored_path = record.stored_path
            session.delete(record)

        if stored_path and os.path.exists(stored_path):
            try:
                os.remove(stored_path)
            except OSError:
                pass  # best-effort cleanup; DB record is already gone

        return Response(status=status.HTTP_204_NO_CONTENT)