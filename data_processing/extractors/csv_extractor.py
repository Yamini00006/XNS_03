"""
data_processing/extractors/csv_extractor.py

Extracts rows from CSV files.
Handles:
  - auto-detection of delimiter (, ; \t |)
  - encoding detection (UTF-8, Latin-1, Windows-1252)
  - BOM stripping
  - blank / all-null rows skipped
  - extra/missing columns tolerated (logged as metadata)
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import chardet

from .base import BaseExtractor, ExtractionResult


class CSVExtractor(BaseExtractor):

    DELIMITERS = [",", ";", "\t", "|"]

    def extract(self, file_path: str | Path) -> ExtractionResult:
        file_path = Path(file_path)
        errors: list[str] = []

        # ── Detect encoding ──────────────────────────────────
        raw_bytes = file_path.read_bytes()
        detected  = chardet.detect(raw_bytes)
        encoding  = detected.get("encoding") or "utf-8"

        try:
            text = raw_bytes.decode(encoding, errors="replace")
        except Exception as e:
            errors.append(f"Encoding error: {e}")
            text = raw_bytes.decode("utf-8", errors="replace")

        # Strip BOM if present
        text = text.lstrip("\ufeff")

        # ── Detect delimiter ─────────────────────────────────
        delimiter = self._detect_delimiter(text)

        # ── Parse CSV ────────────────────────────────────────
        rows: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

        # Normalise headers — strip whitespace
        if reader.fieldnames:
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

        expected_cols = set(reader.fieldnames or [])
        extra_col_rows = 0

        for line_num, raw_row in enumerate(reader, start=2):   # row 1 is header
            # DictReader puts overflow values in key None
            if None in raw_row:
                extra_col_rows += 1
                raw_row.pop(None)

            # Skip completely empty rows
            if all(v is None or str(v).strip() == "" for v in raw_row.values()):
                continue

            # Strip whitespace from every value
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v)
                       for k, v in raw_row.items()}
            cleaned["_source_row"] = line_num
            rows.append(cleaned)

        if extra_col_rows:
            errors.append(
                f"{extra_col_rows} row(s) had more columns than the header — extras dropped"
            )

        return ExtractionResult(
            rows=rows,
            file_path=str(file_path),
            file_format="csv",
            total_rows=len(rows),
            errors=errors,
            metadata={
                "encoding":  encoding,
                "delimiter": delimiter,
                "columns":   list(expected_cols),
            },
        )

    def _detect_delimiter(self, text: str) -> str:
        """Use csv.Sniffer or fall back to counting occurrences in the first line."""
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters="".join(self.DELIMITERS))
            return dialect.delimiter
        except csv.Error:
            first_line = text.split("\n")[0]
            counts = {d: first_line.count(d) for d in self.DELIMITERS}
            return max(counts, key=counts.get)
