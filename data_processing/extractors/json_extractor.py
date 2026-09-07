"""
data_processing/extractors/json_extractor.py

Extracts rows from JSON files.
Supports:
  - Array of objects:  [{"name": "Alice"}, ...]
  - Single object:     {"name": "Alice"}  → wrapped in list
  - Newline-delimited JSON (NDJSON / JSON Lines): one object per line
  - Nested objects: flattened one level deep

DB format note:
  ExtractionResult.file_format is set to "ndjson" for NDJSON files so the
  pipeline metadata accurately reflects the source variant. However, when
  recording the format in the database (upload_files.file_format), the
  factory's db_file_format() function maps "ndjson" → "json" because the
  FileFormat enum treats both as the same JSON family.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractionResult


def _flatten(obj: dict, prefix: str = "", sep: str = "__") -> dict:
    """Flatten one level of nested dicts. Lists are kept as-is."""
    out: dict = {}
    for k, v in obj.items():
        new_key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, new_key, sep))
        else:
            out[new_key] = v
    return out


class JSONExtractor(BaseExtractor):

    def extract(self, file_path: str | Path) -> ExtractionResult:
        file_path = Path(file_path)
        errors: list[str] = []
        text = file_path.read_text(encoding="utf-8", errors="replace")
        fmt  = "json"

        rows: list[dict[str, Any]] = []

        # ── Try standard JSON first ──────────────────────────
        try:
            data = json.loads(text)
            if isinstance(data, list):
                raw_rows = data
            elif isinstance(data, dict):
                # Could be {"data": [...]} or {"customers": [...]} wrapper
                list_keys = [k for k, v in data.items() if isinstance(v, list)]
                if list_keys:
                    raw_rows = data[list_keys[0]]
                else:
                    raw_rows = [data]
            else:
                errors.append(f"Unexpected top-level JSON type: {type(data).__name__}")
                raw_rows = []

        except json.JSONDecodeError:
            # ── Try NDJSON ───────────────────────────────────
            fmt = "ndjson"
            raw_rows = []
            for line_num, line in enumerate(text.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw_rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: JSON parse error — {e}")

        # ── Normalise each row ───────────────────────────────
        for i, item in enumerate(raw_rows, start=1):
            if not isinstance(item, dict):
                errors.append(f"Row {i}: expected object, got {type(item).__name__} — skipped")
                continue
            flat = _flatten(item)
            flat["_source_row"] = i
            rows.append(flat)

        return ExtractionResult(
            rows=rows,
            file_path=str(file_path),
            file_format=fmt,
            total_rows=len(rows),
            errors=errors,
            metadata={"json_variant": fmt},
        )
