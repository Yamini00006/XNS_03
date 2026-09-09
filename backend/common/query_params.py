"""
backend/common/query_params.py

Small helpers for validating and parsing common list-endpoint query
parameters (page, page_size, sort, filters) so every app doesn't have
to reimplement the same guard clauses.
"""

from __future__ import annotations

from common.exceptions import ValidationAPIError


def parse_page(request, default_page_size: int = 20, max_page_size: int = 200) -> tuple[int, int]:
    """Parse & validate ?page= and ?page_size=. Returns (page, page_size)."""
    raw_page = request.query_params.get("page", "1")
    raw_size = request.query_params.get("page_size", str(default_page_size))

    try:
        page = int(raw_page)
    except (TypeError, ValueError):
        raise ValidationAPIError(f"Invalid 'page' value: {raw_page!r}. Must be a positive integer.")
    if page < 1:
        raise ValidationAPIError("'page' must be >= 1.")

    try:
        page_size = int(raw_size)
    except (TypeError, ValueError):
        raise ValidationAPIError(f"Invalid 'page_size' value: {raw_size!r}. Must be a positive integer.")
    if page_size < 1 or page_size > max_page_size:
        raise ValidationAPIError(f"'page_size' must be between 1 and {max_page_size}.")

    return page, page_size


def parse_sort(request, allowed_fields: set[str], default: str = "-created_at") -> tuple[str, bool]:
    """
    Parse ?sort=field or ?sort=-field. Returns (field_name, descending).
    Raises ValidationAPIError for a field not in allowed_fields.
    """
    raw = request.query_params.get("sort", default)
    descending = raw.startswith("-")
    field = raw.lstrip("-") or default.lstrip("-")

    if field not in allowed_fields:
        raise ValidationAPIError(
            f"Invalid 'sort' field: {field!r}. Allowed: {sorted(allowed_fields)}."
        )
    return field, descending