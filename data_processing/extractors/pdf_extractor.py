"""
data_processing/extractors/pdf_extractor.py

Extracts structured data from PDF files using pdfplumber.

Strategy:
  1. Try to extract tables from each page first (structured PDFs).
  2. Fall back to text extraction + regex pattern matching for
     semi-structured / form-style PDFs (e.g. filled forms).

Scanned / image-only PDFs:
  When a PDF contains only scanned images (no embedded text layer),
  pdfplumber returns empty text for every page and finds no tables.
  In this case the extractor returns zero rows and sets:
      metadata["is_scanned"] = True
  This is the correct behaviour for the locked requirement — the
  pipeline records the file as processed with zero extractable rows
  and logs it as a scanned document. Full OCR is outside the locked
  project scope and would require Tesseract or a cloud OCR service.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractionResult
from ..config.settings import PDF_MAX_PAGES

try:
    import pdfplumber
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False


# Regex patterns for extracting common fields from raw PDF text
_FIELD_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email",       re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")),
    ("phone",       re.compile(r"\+?[\d][\d\s\-().]{6,18}[\d]")),
    ("postal_code", re.compile(r"\b\d{5}(?:-\d{4})?\b")),
]

# "Label: Value" patterns (e.g. "Name: John Doe")
_LABEL_VALUE = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z _/\-]{0,30}?)\s*[:=]\s*(?P<value>.+)"
)


def _extract_from_text(text: str) -> dict[str, Any]:
    """Parse a blob of text into a best-effort field dict."""
    row: dict[str, Any] = {}

    # Label: Value pairs
    for match in _LABEL_VALUE.finditer(text):
        label = match.group("label").strip().lower().replace(" ", "_")
        value = match.group("value").strip()
        if label and value and len(label) < 40:
            row[label] = value

    # Regex-extracted fields (override label-value if found)
    for field_name, pattern in _FIELD_PATTERNS:
        m = pattern.search(text)
        if m:
            row[field_name] = m.group(0).strip()

    return row


def _table_to_rows(table: list[list]) -> list[dict[str, Any]]:
    """Convert a pdfplumber table (list of lists) to list of dicts."""
    if not table or len(table) < 2:
        return []
    headers = [str(h).strip() if h else f"col_{i}"
               for i, h in enumerate(table[0])]
    rows = []
    for raw_row in table[1:]:
        if all(c is None or str(c).strip() == "" for c in raw_row):
            continue
        row = {headers[i]: (raw_row[i] if i < len(raw_row) else None)
               for i in range(len(headers))}
        rows.append(row)
    return rows


class PDFExtractor(BaseExtractor):

    def extract(self, file_path: str | Path) -> ExtractionResult:
        file_path = Path(file_path)
        errors: list[str] = []

        if not _PDF_AVAILABLE:
            return ExtractionResult(
                rows=[], file_path=str(file_path), file_format="pdf",
                errors=["pdfplumber not installed — cannot extract PDF"],
            )

        rows: list[dict[str, Any]] = []
        pages_read  = 0
        table_pages = 0
        text_pages  = 0
        # Track pages that produced no text and no tables (scanned indicator)
        empty_pages = 0

        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                if total_pages > PDF_MAX_PAGES:
                    errors.append(
                        f"PDF has {total_pages} pages; only first {PDF_MAX_PAGES} processed"
                    )

                for page_num, page in enumerate(pdf.pages[:PDF_MAX_PAGES], start=1):
                    pages_read += 1

                    # Try tables first
                    tables = page.extract_tables()
                    if tables:
                        table_pages += 1
                        for table in tables:
                            table_rows = _table_to_rows(table)
                            for r in table_rows:
                                r["_source_row"]  = len(rows) + 1
                                r["_source_page"] = page_num
                            rows.extend(table_rows)
                    else:
                        # Fall back to text extraction
                        text = page.extract_text() or ""
                        if text.strip():
                            text_pages += 1
                            row = _extract_from_text(text)
                            if row:
                                row["_source_row"]  = len(rows) + 1
                                row["_source_page"] = page_num
                                row["_raw_text"]    = text[:500]   # keep first 500 chars
                                rows.append(row)
                        else:
                            # Page has no extractable text and no tables.
                            # This is the signature of a scanned/image-only page.
                            empty_pages += 1

        except Exception as e:
            errors.append(f"PDF extraction error: {e}")

        # Determine whether this looks like a scanned document:
        # all pages were empty (no text layer, no tables).
        is_scanned = (pages_read > 0) and (empty_pages == pages_read)

        if not rows:
            if is_scanned:
                errors.append(
                    "PDF appears to be a scanned/image-only document — "
                    "no embedded text layer was found. "
                    "OCR processing is outside the current pipeline scope."
                )
            else:
                errors.append(
                    "No structured data could be extracted from this PDF."
                )

        return ExtractionResult(
            rows=rows,
            file_path=str(file_path),
            file_format="pdf",
            total_rows=len(rows),
            errors=errors,
            metadata={
                "pages_total": pages_read,
                "table_pages": table_pages,
                "text_pages":  text_pages,
                "empty_pages": empty_pages,
                "is_scanned":  is_scanned,
            },
        )
