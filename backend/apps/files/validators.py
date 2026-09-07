"""
backend/apps/files/validators.py

Upload-time validation. Reuses Member 3's format registry
(data_processing.extractors.factory / config.settings) instead of
duplicating the list of supported formats — see PART 19 of the
project handoff ("Do NOT duplicate extraction logic").
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from django.conf import settings

from common.exceptions import UnsupportedFileTypeError, ValidationAPIError
from data_processing.extractors.factory import db_file_format

# django.core.files.uploadedfile.UploadedFile


def safe_original_name(raw_name: str) -> str:
    """Strip any path components / traversal attempts, keep just the basename."""
    name = os.path.basename(raw_name or "")
    name = name.replace("\x00", "").strip()
    if not name or name in (".", ".."):
        raise ValidationAPIError("Invalid or missing filename.")
    return name


def validate_extension(original_name: str) -> str:
    """
    Returns the DB-storable file_format ('csv'|'json'|'xlsx'|'xml'|'pdf')
    for a given filename, using Member 3's own format registry so the
    accepted set never drifts out of sync with what the pipeline can
    actually process.
    """
    try:
        return db_file_format(original_name)
    except ValueError as exc:
        raise UnsupportedFileTypeError(str(exc))


def validate_size(size_bytes: int) -> None:
    max_bytes = settings.MAX_UPLOAD_SIZE_BYTES
    if size_bytes <= 0:
        raise ValidationAPIError("Uploaded file is empty.")
    if size_bytes > max_bytes:
        raise ValidationAPIError(
            f"File too large ({size_bytes} bytes). Maximum allowed is {max_bytes} bytes."
        )


def build_storage_path(original_name: str) -> Path:
    """
    Build a safe, collision-free storage path under settings.UPLOAD_DIR.
    Uses a UUID prefix so two users uploading 'customers.csv' never collide,
    and so the stored filename never echoes user-controlled path segments.
    """
    ext = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    return Path(settings.UPLOAD_DIR) / stored_name