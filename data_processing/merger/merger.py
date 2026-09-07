"""
data_processing/merger/merger.py

Detects and merges duplicate customer records.

Dedup strategy (configured in settings.DEDUP_KEYS):
  - Two rows are duplicates if any key-set matches:
      ["email"]
      ["phone", "full_name"]
      ["first_name", "last_name", "postal_code"]

Merge strategy — "most complete wins":
  - The record with the fewest null fields is the primary.
  - Fields from secondary records fill in null gaps on the primary.
  - source_count tracks how many source rows contributed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config.settings import DEDUP_KEYS


@dataclass
class MergeResult:
    merged_rows:  list[dict[str, Any]]   # deduplicated golden records
    duplicate_pairs: list[tuple[int, int]]  # (primary_idx, duplicate_idx) in original list
    duplicate_count: int = 0

    @property
    def unique_count(self) -> int:
        return len(self.merged_rows)


def _row_key(row: dict, keys: list[str]) -> tuple | None:
    """
    Build a dedup key tuple from a row.
    Returns None if any key field is null/empty (can't dedup on missing data).
    """
    values = []
    for k in keys:
        val = row.get(k)
        if val is None or str(val).strip() == "":
            return None
        values.append(str(val).strip().lower())
    return tuple(values)


def _null_count(row: dict) -> int:
    """Count how many meaningful fields are null."""
    skip = {"_source_row", "_source_sheet", "_source_page", "_raw_text",
            "_transform_failed", "_validation_errors", "source_count"}
    return sum(1 for k, v in row.items() if k not in skip and v is None)


def _merge_two(primary: dict, secondary: dict) -> dict:
    """
    Merge secondary into primary: fill null fields on primary with secondary values.
    primary is modified in place and returned.
    """
    skip = {"_source_row", "_source_sheet", "_source_page", "_raw_text",
            "_transform_failed", "_validation_errors"}
    for k, v in secondary.items():
        if k in skip:
            continue
        if primary.get(k) is None and v is not None:
            primary[k] = v
    primary["source_count"] = primary.get("source_count", 1) + 1
    return primary


class Merger:
    """
    Deduplicates a list of validated rows.

    Works purely in memory — does NOT touch the database.
    The loader will handle matching against existing DB records separately
    (cross-file dedup) but that is a phase-2 concern; for now we dedup
    within each file's batch.
    """

    def merge(self, rows: list[dict[str, Any]]) -> MergeResult:
        if not rows:
            return MergeResult(merged_rows=[], duplicate_pairs=[])

        # Map from dedup-key → index in `unique` list
        seen: dict[tuple, int] = {}   # key → index in unique_rows
        unique_rows: list[dict] = []
        duplicate_pairs: list[tuple[int, int]] = []

        for i, row in enumerate(rows):
            row.setdefault("source_count", 1)
            matched_idx: int | None = None

            # Try each dedup key-set in order
            for key_set in DEDUP_KEYS:
                k = _row_key(row, key_set)
                if k is not None and k in seen:
                    matched_idx = seen[k]
                    break

            if matched_idx is None:
                # New unique record
                idx = len(unique_rows)
                unique_rows.append(dict(row))

                # Register all applicable keys for this row
                for key_set in DEDUP_KEYS:
                    k = _row_key(row, key_set)
                    if k is not None:
                        seen.setdefault(k, idx)
            else:
                # Duplicate — merge into existing primary
                primary = unique_rows[matched_idx]
                # Pick the "more complete" record as primary
                if _null_count(row) < _null_count(primary):
                    # incoming row is more complete — swap
                    row_copy = dict(row)
                    row_copy = _merge_two(row_copy, primary)
                    unique_rows[matched_idx] = row_copy
                else:
                    _merge_two(primary, row)

                duplicate_pairs.append((matched_idx, i))

        return MergeResult(
            merged_rows=unique_rows,
            duplicate_pairs=duplicate_pairs,
            duplicate_count=len(duplicate_pairs),
        )
