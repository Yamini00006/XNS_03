"""
data_processing/schemas/detector.py

Detects and maps source column names to canonical field names.
Also infers column data types from sample values.

Used by: transformers (before cleaning)
"""

from __future__ import annotations

import re
from typing import Any

from ..config.settings import canonical_field, FIELD_ALIASES


# ─── Type inference ───────────────────────────────────────────

def infer_type(values: list[Any]) -> str:
    """
    Infer the predominant Python type from a sample of values.
    Returns one of: 'string', 'integer', 'float', 'boolean', 'date', 'unknown'
    """
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return "unknown"

    type_counts = {"integer": 0, "float": 0, "boolean": 0, "date": 0, "string": 0}
    date_pattern = re.compile(
        r"^\d{4}[-/]\d{2}[-/]\d{2}$|^\d{2}[-/]\d{2}[-/]\d{4}$"
    )

    for v in non_null:
        s = str(v).strip()
        if s.lower() in ("true", "false", "yes", "no", "1", "0"):
            type_counts["boolean"] += 1
        elif date_pattern.match(s):
            type_counts["date"] += 1
        else:
            try:
                int(s)
                type_counts["integer"] += 1
                continue
            except ValueError:
                pass
            try:
                float(s)
                type_counts["float"] += 1
                continue
            except ValueError:
                pass
            type_counts["string"] += 1

    return max(type_counts, key=type_counts.get)


# ─── Schema mapping ───────────────────────────────────────────

class SchemaMapping:
    """
    Result of schema detection for one file/source.

    Attributes:
        column_map   : {source_col: canonical_col}
        unknown_cols : source columns that could not be mapped
        type_map     : {canonical_col: inferred_type}
    """

    def __init__(
        self,
        column_map: dict[str, str],
        unknown_cols: list[str],
        type_map: dict[str, str],
    ):
        self.column_map   = column_map
        self.unknown_cols = unknown_cols
        self.type_map     = type_map

    def apply(self, row: dict[str, Any]) -> dict[str, Any]:
        """
        Apply the mapping to a single source row.
        Returns a new dict with canonical keys.
        Unknown source columns are preserved under their original names.
        """
        mapped: dict[str, Any] = {}
        for src_col, value in row.items():
            target = self.column_map.get(src_col, src_col)
            mapped[target] = value
        return mapped

    def summary(self) -> dict:
        return {
            "mapped_columns": len(self.column_map),
            "unknown_columns": self.unknown_cols,
            "type_map": self.type_map,
        }


def detect_schema(
    rows: list[dict[str, Any]],
    sample_size: int = 20,
) -> SchemaMapping:
    """
    Detect schema from a list of dicts (already extracted rows).

    Steps:
    1. Collect all source column names from the first N rows.
    2. Map each to a canonical name via settings.canonical_field().
    3. Infer the data type of each canonical column from sample values.
    4. Return a SchemaMapping.

    Args:
        rows        : list of raw extracted rows (dicts)
        sample_size : how many rows to sample for type inference

    Returns:
        SchemaMapping
    """
    if not rows:
        return SchemaMapping({}, [], {})

    # 1. Collect all column names (union across all rows to handle sparse JSON)
    all_cols: set[str] = set()
    for row in rows[:sample_size]:
        all_cols.update(row.keys())

    # 2. Map to canonical names
    column_map: dict[str, str] = {}
    unknown_cols: list[str] = []
    canonical_set: set[str] = set(FIELD_ALIASES.keys())

    for col in sorted(all_cols):
        canon = canonical_field(col)
        column_map[col] = canon
        if canon not in canonical_set and canon == col:
            unknown_cols.append(col)

    # 3. Infer types per canonical column
    sample = rows[:sample_size]
    type_map: dict[str, str] = {}
    for src_col, canon_col in column_map.items():
        values = [row.get(src_col) for row in sample]
        type_map[canon_col] = infer_type(values)

    return SchemaMapping(column_map, unknown_cols, type_map)
