"""
data_processing/extractors/xml_extractor.py

Extracts rows from XML files.
Strategy:
  - Finds the most repeated child element under the root
    (e.g. <customer>, <record>, <row>) and treats each as one row.
  - All child text nodes become dict fields.
  - Attributes are included prefixed with "@".
  - Nested children are flattened one level with "__" separator.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractionResult


def _element_to_dict(elem: ET.Element, prefix: str = "") -> dict[str, Any]:
    """Recursively convert an XML element to a flat dict."""
    result: dict[str, Any] = {}

    # Attributes (e.g. <customer id="1"> → "@id": "1")
    for attr_name, attr_val in elem.attrib.items():
        key = f"{prefix}@{attr_name}" if prefix else f"@{attr_name}"
        result[key] = attr_val

    # Direct text
    if elem.text and elem.text.strip():
        if prefix:
            result[prefix] = elem.text.strip()

    # Children
    for child in elem:
        tag = child.tag
        # Remove namespace if present: {ns}tag → tag
        if "}" in tag:
            tag = tag.split("}")[1]
        child_key = f"{prefix}__{tag}" if prefix else tag
        child_dict = _element_to_dict(child, prefix=child_key)
        result.update(child_dict)

        # If child has no sub-children and has text, just set the value
        if not list(child) and child.text:
            result[child_key] = child.text.strip()

    return result


def _detect_record_tag(root: ET.Element) -> str | None:
    """Find the most common direct child tag — that's likely the record element."""
    if not list(root):
        return None
    counts: Counter = Counter()
    for child in root:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}")[1]
        counts[tag] += 1
    return counts.most_common(1)[0][0]


class XMLExtractor(BaseExtractor):

    def __init__(self, record_tag: str | None = None):
        """
        record_tag: force a specific tag name to use as the row element.
                    If None, auto-detected from the file.
        """
        self.record_tag = record_tag

    def extract(self, file_path: str | Path) -> ExtractionResult:
        file_path = Path(file_path)
        errors: list[str] = []

        try:
            tree = ET.parse(file_path)
        except ET.ParseError as e:
            return ExtractionResult(
                rows=[], file_path=str(file_path), file_format="xml",
                errors=[f"XML parse error: {e}"],
            )

        root = tree.getroot()
        root_tag = root.tag
        if "}" in root_tag:
            root_tag = root_tag.split("}")[1]

        record_tag = self.record_tag or _detect_record_tag(root)
        if not record_tag:
            errors.append("Could not detect record element in XML")
            return ExtractionResult(
                rows=[], file_path=str(file_path), file_format="xml",
                errors=errors,
            )

        rows: list[dict[str, Any]] = []
        for i, elem in enumerate(root, start=1):
            tag = elem.tag
            if "}" in tag:
                tag = tag.split("}")[1]
            if tag != record_tag:
                continue
            row = _element_to_dict(elem)
            row["_source_row"] = i
            rows.append(row)

        return ExtractionResult(
            rows=rows,
            file_path=str(file_path),
            file_format="xml",
            total_rows=len(rows),
            errors=errors,
            metadata={"root_tag": root_tag, "record_tag": record_tag},
        )
