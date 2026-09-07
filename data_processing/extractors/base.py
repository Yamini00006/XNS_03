"""
data_processing/extractors/base.py

Abstract base class for all format-specific extractors.
Every extractor returns a list of raw dicts + metadata.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractionResult:
    """
    What every extractor must return.

    rows        : list of raw dicts, one per record
    file_path   : path of the source file
    file_format : 'csv' | 'json' | 'xlsx' | 'xml' | 'pdf'
    total_rows  : total rows found (before any filtering)
    errors      : list of extraction-level problems (not row validation)
    metadata    : format-specific info (sheet name, encoding, page count, …)
    """
    rows:        list[dict[str, Any]]
    file_path:   str
    file_format: str
    total_rows:  int              = 0
    errors:      list[str]        = field(default_factory=list)
    metadata:    dict[str, Any]   = field(default_factory=dict)


class BaseExtractor(ABC):
    """
    Every concrete extractor must implement extract().
    Subclasses should NOT write to the database — that is the loader's job.
    """

    @abstractmethod
    def extract(self, file_path: str | Path) -> ExtractionResult:
        """
        Read the file and return raw rows as dicts.
        Must not raise on recoverable errors — add them to result.errors instead.
        """

    @staticmethod
    def file_checksum(file_path: str | Path) -> str:
        """MD5 checksum of the file for dedup / lineage tracking."""
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
