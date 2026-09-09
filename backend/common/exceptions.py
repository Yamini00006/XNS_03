"""
backend/common/exceptions.py

Consistent JSON error envelope for every API error, and a custom DRF
exception handler that also catches errors raised by the SQLAlchemy /
Member-3 pipeline layer so nothing leaks a stack trace to the client.

Response shape (always):
    {"error": {"code": "<SHORT_CODE>", "message": "<human readable>"}}
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class APIError(APIException):
    """Base class for Member-2 API errors with a stable machine-readable code."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=message, code=self.code)


class NotFoundError(APIError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "NOT_FOUND"


class ValidationAPIError(APIError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "VALIDATION_ERROR"


class UnsupportedFileTypeError(APIError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "UNSUPPORTED_FILE_TYPE"


class ProcessingError(APIError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "PROCESSING_FAILED"


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def api_exception_handler(exc, context):
    """
    Central DRF exception handler.

    - APIError (and subclasses) -> their own status code + machine code.
    - Standard DRF/Django exceptions -> handled by DRF, reshaped to our envelope.
    - Anything else (DB errors, SQLAlchemy errors, unexpected bugs) -> logged
      server-side, 500 returned to the client with NO internal detail/stack trace.
    """
    if isinstance(exc, APIError):
        return Response(_error_body(exc.code, str(exc.detail)), status=exc.status_code)

    response = drf_exception_handler(exc, context)

    if response is not None:
        code = getattr(exc, "default_code", None) or exc.__class__.__name__.upper()
        # DRF puts validation errors in response.data (dict/list) — flatten to a message.
        message = _flatten_detail(response.data)
        response.data = _error_body(code, message)
        return response

    # Unhandled exception: never expose internals to the client.
    logger.exception("Unhandled exception in API view", exc_info=exc)
    return Response(
        _error_body("INTERNAL_ERROR", "An unexpected error occurred."),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _flatten_detail(data) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        parts = []
        for field, errors in data.items():
            if isinstance(errors, (list, tuple)):
                parts.append(f"{field}: {'; '.join(str(e) for e in errors)}")
            else:
                parts.append(f"{field}: {errors}")
        return " | ".join(parts) if parts else "Invalid request."
    if isinstance(data, (list, tuple)):
        return "; ".join(str(e) for e in data)
    return str(data)