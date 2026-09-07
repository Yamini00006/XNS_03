"""
data_processing/validators/validator.py

Validates transformed rows against business rules.

Produces:
  - valid_rows   : rows that pass all checks
  - invalid_rows : rows with at least one ERROR-severity failure
  - errors       : list of ValidationIssue (one per field/row problem)

Severity:
  ERROR   — row is rejected (won't be loaded into customers table)
  WARNING — row is kept but issue is recorded
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..config.settings import (
    EMAIL_REGEX, PHONE_REGEX,
    REQUIRED_FIELDS, IMPORTANT_FIELDS,
    FIELD_MAX_LENGTHS,
)


# ─── Issue type ───────────────────────────────────────────────

@dataclass
class ValidationIssue:
    row_number:    int
    field_name:    str | None
    error_code:    str
    error_message: str
    severity:      str          # "error" | "warning"
    raw_value:     str | None = None


@dataclass
class ValidationResult:
    valid_rows:   list[dict[str, Any]]
    invalid_rows: list[dict[str, Any]]
    issues:       list[ValidationIssue] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.valid_rows) + len(self.invalid_rows)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# ─── Compiled regexes ─────────────────────────────────────────

_EMAIL_RE = re.compile(EMAIL_REGEX)
_PHONE_RE = re.compile(PHONE_REGEX)


# ─── Individual checks ────────────────────────────────────────

def _check_required(row: dict, row_num: int) -> list[ValidationIssue]:
    issues = []
    for f in REQUIRED_FIELDS:
        val = row.get(f)
        if val is None or str(val).strip() == "":
            issues.append(ValidationIssue(
                row_number=row_num, field_name=f,
                error_code="REQUIRED_FIELD_MISSING",
                error_message=f"Required field '{f}' is missing or empty",
                severity="error",
            ))
    return issues


def _check_important(row: dict, row_num: int) -> list[ValidationIssue]:
    """Warn if important fields (email/phone/name) are all absent."""
    issues = []
    for f in IMPORTANT_FIELDS:
        val = row.get(f)
        if val is None or str(val).strip() == "":
            issues.append(ValidationIssue(
                row_number=row_num, field_name=f,
                error_code="IMPORTANT_FIELD_MISSING",
                error_message=f"Important field '{f}' is missing — row has reduced quality",
                severity="warning",
            ))
    return issues


def _check_email(row: dict, row_num: int) -> list[ValidationIssue]:
    issues = []
    email = row.get("email")
    if email and not _EMAIL_RE.match(str(email)):
        issues.append(ValidationIssue(
            row_number=row_num, field_name="email",
            error_code="INVALID_EMAIL",
            error_message=f"'{email}' is not a valid email address",
            severity="error",
            raw_value=str(email),
        ))
    return issues


def _check_phone(row: dict, row_num: int) -> list[ValidationIssue]:
    issues = []
    phone = row.get("phone")
    if phone and not _PHONE_RE.match(str(phone)):
        issues.append(ValidationIssue(
            row_number=row_num, field_name="phone",
            error_code="INVALID_PHONE",
            error_message=f"'{phone}' does not look like a valid phone number",
            severity="warning",
            raw_value=str(phone),
        ))
    return issues


def _check_completely_empty(row: dict, row_num: int) -> list[ValidationIssue]:
    """A row where every non-meta field is null is useless."""
    meta = {"_source_row", "_source_sheet", "_source_page", "_raw_text", "_transform_failed"}
    values = [v for k, v in row.items() if k not in meta]
    if all(v is None for v in values):
        return [ValidationIssue(
            row_number=row_num, field_name=None,
            error_code="EMPTY_ROW",
            error_message="Row has no usable data in any field",
            severity="error",
        )]
    return []


def _check_lengths(row: dict, row_num: int) -> list[ValidationIssue]:
    """Catch values that exceed DB column limits (should have been truncated, but be safe)."""
    issues = []
    for field_name, max_len in FIELD_MAX_LENGTHS.items():
        val = row.get(field_name)
        if val and len(str(val)) > max_len:
            issues.append(ValidationIssue(
                row_number=row_num, field_name=field_name,
                error_code="VALUE_TOO_LONG",
                error_message=f"Value exceeds max length {max_len} for '{field_name}'",
                severity="warning",
                raw_value=str(val)[:100],
            ))
    return issues


# ─── Validator class ──────────────────────────────────────────

class Validator:
    """
    Applies all validation rules to a list of transformed rows.

    A row with any ERROR issue is placed in invalid_rows.
    A row with only WARNING issues stays in valid_rows.
    """

    def validate(self, rows: list[dict[str, Any]]) -> ValidationResult:
        valid_rows:   list[dict] = []
        invalid_rows: list[dict] = []
        all_issues:   list[ValidationIssue] = []

        for row in rows:
            row_num = row.get("_source_row", 0)

            # Fail-fast: rows that errored during transform
            if row.get("_transform_failed"):
                invalid_rows.append(row)
                all_issues.append(ValidationIssue(
                    row_number=row_num, field_name=None,
                    error_code="TRANSFORM_FAILED",
                    error_message="Row could not be transformed",
                    severity="error",
                ))
                continue

            row_issues: list[ValidationIssue] = []
            row_issues += _check_completely_empty(row, row_num)
            row_issues += _check_required(row, row_num)
            row_issues += _check_important(row, row_num)
            row_issues += _check_email(row, row_num)
            row_issues += _check_phone(row, row_num)
            row_issues += _check_lengths(row, row_num)

            all_issues.extend(row_issues)

            has_error = any(i.severity == "error" for i in row_issues)
            if has_error:
                row["_validation_errors"] = [i.error_code for i in row_issues if i.severity == "error"]
                invalid_rows.append(row)
            else:
                valid_rows.append(row)

        return ValidationResult(
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            issues=all_issues,
        )
