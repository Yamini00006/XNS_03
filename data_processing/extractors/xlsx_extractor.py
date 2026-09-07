"""
data_processing/extractors/xlsx_extractor.py

Extracts rows from Excel files (.xlsx, .xls).
Handles:
  - Multiple sheets (first sheet by default, or all if configured)
  - Empty rows skipped
  - Merged cells handled gracefully by openpyxl
  - Date cells converted to ISO strings
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from .base import BaseExtractor, ExtractionResult


def _cell_value(cell) -> Any:
    """Convert openpyxl cell value to a JSON-safe Python type."""
    v = cell.value
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return v


class XLSXExtractor(BaseExtractor):

    def __init__(self, all_sheets: bool = False):
        """
        all_sheets: if True, extract every sheet and prefix column names
                    with the sheet name. If False (default), use first sheet.
        """
        self.all_sheets = all_sheets

    def extract(self, file_path: str | Path) -> ExtractionResult:
        file_path = Path(file_path)
        errors: list[str] = []

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        except Exception as e:
            return ExtractionResult(
                rows=[], file_path=str(file_path), file_format="xlsx",
                errors=[f"Cannot open workbook: {e}"],
            )

        sheet_names = wb.sheetnames
        sheets_to_read = sheet_names if self.all_sheets else [sheet_names[0]]

        all_rows: list[dict[str, Any]] = []
        global_row_num = 0

        for sheet_name in sheets_to_read:
            ws = wb[sheet_name]
            rows_iter = ws.iter_rows()

            # First row = headers
            try:
                header_row = next(rows_iter)
            except StopIteration:
                errors.append(f"Sheet '{sheet_name}' is empty")
                continue

            headers = [
                (cell.value or f"col_{i}") for i, cell in enumerate(header_row)
            ]
            # Strip whitespace from headers
            headers = [str(h).strip() for h in headers]

            for sheet_row_num, row in enumerate(rows_iter, start=2):
                values = [_cell_value(c) for c in row]

                # Skip completely empty rows
                if all(v is None for v in values):
                    continue

                row_dict: dict[str, Any] = {}
                for i, h in enumerate(headers):
                    row_dict[h] = values[i] if i < len(values) else None

                global_row_num += 1
                row_dict["_source_row"]   = sheet_row_num
                row_dict["_source_sheet"] = sheet_name
                all_rows.append(row_dict)

        wb.close()

        return ExtractionResult(
            rows=all_rows,
            file_path=str(file_path),
            file_format="xlsx",
            total_rows=len(all_rows),
            errors=errors,
            metadata={"sheets": sheet_names, "sheets_read": sheets_to_read},
        )
