"""
data_processing/extractors/factory.py

Returns the correct extractor instance for a given file path or format string.
Used by the pipeline so it doesn't need to know about individual extractor classes.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseExtractor
from .csv_extractor  import CSVExtractor
from .json_extractor import JSONExtractor
from .xlsx_extractor import XLSXExtractor
from .xml_extractor  import XMLExtractor
from .pdf_extractor  import PDFExtractor


_FORMAT_MAP: dict[str, type[BaseExtractor]] = {
    "csv":    CSVExtractor,
    "json":   JSONExtractor,
    "ndjson": JSONExtractor,   # treated as JSON-family; stored as "json" in DB
    "xlsx":   XLSXExtractor,
    "xml":    XMLExtractor,
    "pdf":    PDFExtractor,
    # NOTE: legacy .xls is NOT supported — openpyxl only handles .xlsx.
    # The locked requirement specifies XLSX. Reject .xls cleanly below.
}


def get_extractor(file_path: str | Path) -> BaseExtractor:
    """
    Return the appropriate extractor for the given file based on its extension.
    Raises ValueError for unsupported formats.
    """
    ext = Path(file_path).suffix.lstrip(".").lower()
    cls = _FORMAT_MAP.get(ext)
    if cls is None:
        hint = ""
        if ext == "xls":
            hint = " (legacy .xls is not supported; convert to .xlsx first)"
        raise ValueError(
            f"Unsupported file format: '.{ext}'{hint}. "
            f"Supported: {sorted(_FORMAT_MAP.keys())}"
        )
    return cls()


def get_extractor_by_format(fmt: str) -> BaseExtractor:
    """Return extractor by explicit format string (e.g. 'csv', 'json')."""
    fmt = fmt.lower()
    cls = _FORMAT_MAP.get(fmt)
    if cls is None:
        raise ValueError(f"Unknown format: '{fmt}'")
    return cls()


def db_file_format(file_path: str | Path) -> str:
    """
    Return the FileFormat enum value to store in the database for a given file.

    NDJSON is treated as 'json' at the database level — it is a JSON-family
    input format and the FileFormat enum does not have a separate NDJSON value.

    Raises ValueError for unsupported formats (consistent with get_extractor).
    """
    ext = Path(file_path).suffix.lstrip(".").lower()
    if ext not in _FORMAT_MAP:
        raise ValueError(f"Unsupported file format: '.{ext}'")
    # ndjson → stored as "json" in DB; all others map 1-to-1
    return "json" if ext == "ndjson" else ext
