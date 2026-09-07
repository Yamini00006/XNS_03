"""
data_processing/transformers/transformer.py

Transforms raw extracted rows into standardized customer dicts.

Steps per row:
  1. Apply schema mapping (source column → canonical name)
  2. Trim whitespace from all string values
  3. Normalize email (lowercase, strip)
  4. Normalize phone (digits + + only)
  5. Normalize name (title-case, unicode normalization)
  6. Normalize country codes
  7. Truncate oversized fields
  8. Null-out empty strings

Returns TransformResult with clean rows and any per-row warnings.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from ..config.settings import FIELD_MAX_LENGTHS, canonical_field
from ..schemas.detector import SchemaMapping


# ─── Result types ─────────────────────────────────────────────

@dataclass
class RowWarning:
    row_number: int
    field_name: str
    message:    str


@dataclass
class TransformResult:
    rows:     list[dict[str, Any]]
    warnings: list[RowWarning] = field(default_factory=list)


# ─── Field-level normalizers ──────────────────────────────────

def _normalize_email(val: str) -> str:
    return val.strip().lower()


_NON_DIGIT = re.compile(r"[^\d+]")

def _normalize_phone(val: str) -> str:
    """Keep only digits and leading +."""
    cleaned = _NON_DIGIT.sub("", val.strip())
    if val.strip().startswith("+") and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


_UNICODE_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

def _normalize_name(val: str) -> str:
    """Unicode normalize, strip control chars, title-case."""
    val = unicodedata.normalize("NFC", val)
    val = _UNICODE_CONTROL.sub("", val).strip()
    # Title-case only if all-upper or all-lower
    if val.isupper() or val.islower():
        val = val.title()
    return val


# Common country name → ISO 3166-1 alpha-2
_COUNTRY_MAP: dict[str, str] = {
    "united states": "US", "usa": "US", "u.s.a.": "US", "us": "US",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB",
    "canada": "CA", "ca": "CA",
    "australia": "AU", "au": "AU",
    "india": "IN", "in": "IN",
    "germany": "DE", "de": "DE",
    "france": "FR", "fr": "FR",
}

def _normalize_country(val: str) -> str:
    return _COUNTRY_MAP.get(val.strip().lower(), val.strip().upper())


def _truncate(val: str, field_name: str, warnings: list[RowWarning], row_num: int) -> str:
    max_len = FIELD_MAX_LENGTHS.get(field_name)
    if max_len and len(val) > max_len:
        warnings.append(RowWarning(row_num, field_name, f"Truncated to {max_len} chars"))
        return val[:max_len]
    return val


# ─── Main transformer ─────────────────────────────────────────

# Internal tracking keys added by extractors — not customer fields
_META_KEYS = {"_source_row", "_source_sheet", "_source_page", "_raw_text"}


class Transformer:
    """
    Transforms raw extraction rows into standardized customer dicts.

    Usage:
        mapping = detect_schema(rows)
        result  = Transformer().transform(rows, mapping)
    """

    def transform(
        self,
        rows: list[dict[str, Any]],
        mapping: SchemaMapping,
    ) -> TransformResult:
        cleaned_rows: list[dict[str, Any]] = []
        warnings: list[RowWarning] = []

        for row in rows:
            row_num = row.get("_source_row", 0)
            try:
                out = self._transform_row(row, mapping, warnings, row_num)
                cleaned_rows.append(out)
            except Exception as e:
                warnings.append(RowWarning(row_num, "*", f"Transform error: {e}"))
                cleaned_rows.append({"_source_row": row_num, "_transform_failed": True})

        return TransformResult(rows=cleaned_rows, warnings=warnings)

    def _transform_row(
        self,
        row: dict[str, Any],
        mapping: SchemaMapping,
        warnings: list[RowWarning],
        row_num: int,
    ) -> dict[str, Any]:

        # 1. Apply schema mapping
        mapped = mapping.apply(row)

        out: dict[str, Any] = {}

        for key, value in mapped.items():
            # Preserve internal meta keys as-is
            if key in _META_KEYS:
                out[key] = value
                continue

            # 2. Null-out empty strings
            if value is None or (isinstance(value, str) and value.strip() == ""):
                out[key] = None
                continue

            # 3. Convert to string for text fields (numbers might slip through)
            if not isinstance(value, str):
                value = str(value)

            # 4. Field-specific normalization
            if key == "email":
                value = _normalize_email(value)
            elif key == "phone":
                value = _normalize_phone(value)
            elif key in ("first_name", "last_name", "full_name"):
                value = _normalize_name(value)
            elif key == "country":
                value = _normalize_country(value)
            else:
                # Generic: strip whitespace + remove control chars
                value = _UNICODE_CONTROL.sub("", value.strip())

            # 5. Truncate oversized values
            value = _truncate(value, key, warnings, row_num)

            out[key] = value if value else None  # re-null if empty after processing

        # 6. Synthesize full_name if missing but first+last present
        if not out.get("full_name") and out.get("first_name") and out.get("last_name"):
            out["full_name"] = f"{out['first_name']} {out['last_name']}"

        return out
