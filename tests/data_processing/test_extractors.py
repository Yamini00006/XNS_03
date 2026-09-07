"""
tests/data_processing/test_extractors.py

Unit tests for all format extractors.
Runs without a database — tests extraction only.
"""

import json
import sys
from pathlib import Path

import pytest

# Allow imports from project root
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data_processing.extractors.csv_extractor  import CSVExtractor
from data_processing.extractors.json_extractor import JSONExtractor
from data_processing.extractors.xlsx_extractor import XLSXExtractor
from data_processing.extractors.xml_extractor  import XMLExtractor
from data_processing.extractors.factory        import get_extractor


# ─── CSV tests ────────────────────────────────────────────────

class TestCSVExtractor:

    def test_basic_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name,email,phone\nAlice,alice@test.com,+1-555-0001\nBob,bob@test.com,+1-555-0002\n")
        result = CSVExtractor().extract(f)
        assert result.total_rows == 2
        assert result.rows[0]["name"] == "Alice"
        assert result.file_format == "csv"
        assert not result.errors or all("extra" in e.lower() for e in result.errors)

    def test_semicolon_delimiter(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name;email\nAlice;alice@test.com\n")
        result = CSVExtractor().extract(f)
        assert result.total_rows == 1
        assert result.rows[0]["email"] == "alice@test.com"

    def test_empty_rows_skipped(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name,email\nAlice,a@test.com\n,,\nBob,b@test.com\n")
        result = CSVExtractor().extract(f)
        assert result.total_rows == 2

    def test_whitespace_stripped_from_values(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name,email\n  Alice  ,  alice@test.com  \n")
        result = CSVExtractor().extract(f)
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[0]["email"] == "alice@test.com"

    def test_source_row_number(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name,email\nAlice,a@t.com\nBob,b@t.com\n")
        result = CSVExtractor().extract(f)
        assert result.rows[0]["_source_row"] == 2
        assert result.rows[1]["_source_row"] == 3

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("name,email\n")
        result = CSVExtractor().extract(f)
        assert result.total_rows == 0

    def test_seed_csv_readable(self):
        seed_file = ROOT / "datasets" / "input" / "customers_50.csv"
        if not seed_file.exists():
            pytest.skip("Seed data not generated yet")
        result = CSVExtractor().extract(seed_file)
        assert result.total_rows == 50
        assert "email" in result.rows[0]


# ─── JSON tests ───────────────────────────────────────────────

class TestJSONExtractor:

    def test_array_of_objects(self, tmp_path):
        data = [{"name": "Alice", "email": "a@test.com"}, {"name": "Bob", "email": "b@test.com"}]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        result = JSONExtractor().extract(f)
        assert result.total_rows == 2
        assert result.rows[0]["name"] == "Alice"

    def test_single_object(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text(json.dumps({"name": "Alice", "email": "a@test.com"}))
        result = JSONExtractor().extract(f)
        assert result.total_rows == 1

    def test_wrapped_object(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text(json.dumps({"customers": [{"name": "Alice"}, {"name": "Bob"}]}))
        result = JSONExtractor().extract(f)
        assert result.total_rows == 2

    def test_ndjson(self, tmp_path):
        f = tmp_path / "test.ndjson"
        f.write_text('{"name": "Alice"}\n{"name": "Bob"}\n')
        result = JSONExtractor().extract(f)
        assert result.total_rows == 2
        assert result.file_format == "ndjson"

    def test_nested_object_flattened(self, tmp_path):
        data = [{"name": "Alice", "address": {"city": "NY", "zip": "10001"}}]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        result = JSONExtractor().extract(f)
        assert "address__city" in result.rows[0]
        assert result.rows[0]["address__city"] == "NY"

    def test_invalid_json_logged(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("this is not json")
        result = JSONExtractor().extract(f)
        assert len(result.errors) > 0

    def test_seed_json_readable(self):
        seed_file = ROOT / "datasets" / "input" / "customers_50.json"
        if not seed_file.exists():
            pytest.skip("Seed data not generated yet")
        result = JSONExtractor().extract(seed_file)
        assert result.total_rows == 50


# ─── XLSX tests ───────────────────────────────────────────────

class TestXLSXExtractor:

    def _make_xlsx(self, tmp_path, rows: list[dict]) -> Path:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row[h] for h in headers])
        p = tmp_path / "test.xlsx"
        wb.save(p)
        return p

    def test_basic_xlsx(self, tmp_path):
        rows = [{"name": "Alice", "email": "a@test.com"}, {"name": "Bob", "email": "b@test.com"}]
        f = self._make_xlsx(tmp_path, rows)
        result = XLSXExtractor().extract(f)
        assert result.total_rows == 2
        assert result.rows[0]["name"] == "Alice"

    def test_seed_xlsx_readable(self):
        seed_file = ROOT / "datasets" / "input" / "customers_50.xlsx"
        if not seed_file.exists():
            pytest.skip("Seed data not generated yet")
        result = XLSXExtractor().extract(seed_file)
        assert result.total_rows == 50


# ─── XML tests ────────────────────────────────────────────────

class TestXMLExtractor:

    def test_basic_xml(self, tmp_path):
        xml = """<?xml version="1.0"?>
<customers>
  <customer><name>Alice</name><email>a@test.com</email></customer>
  <customer><name>Bob</name><email>b@test.com</email></customer>
</customers>"""
        f = tmp_path / "test.xml"
        f.write_text(xml)
        result = XMLExtractor().extract(f)
        assert result.total_rows == 2
        assert result.rows[0]["name"] == "Alice"

    def test_seed_xml_readable(self):
        seed_file = ROOT / "datasets" / "input" / "customers_20.xml"
        if not seed_file.exists():
            pytest.skip("Seed data not generated yet")
        result = XMLExtractor().extract(seed_file)
        assert result.total_rows == 20

    def test_malformed_xml(self, tmp_path):
        f = tmp_path / "bad.xml"
        f.write_text("<customers><customer><name>Alice</name>")
        result = XMLExtractor().extract(f)
        assert len(result.errors) > 0
        assert result.total_rows == 0


# ─── Factory tests ────────────────────────────────────────────

class TestExtractorFactory:

    def test_csv_factory(self, tmp_path):
        f = tmp_path / "file.csv"
        f.touch()
        ext = get_extractor(f)
        assert isinstance(ext, CSVExtractor)

    def test_json_factory(self, tmp_path):
        f = tmp_path / "file.json"
        f.touch()
        ext = get_extractor(f)
        assert isinstance(ext, JSONExtractor)

    def test_unsupported_raises(self, tmp_path):
        f = tmp_path / "file.txt"
        f.touch()
        with pytest.raises(ValueError, match="Unsupported"):
            get_extractor(f)


# ─── PDF tests ────────────────────────────────────────────────

from data_processing.extractors.pdf_extractor import PDFExtractor


class TestPDFExtractor:

    def test_scanned_pdf_detected(self):
        """A PDF with no text layer must be flagged as scanned, not crash."""
        scanned = ROOT / "datasets" / "invalid" / "scanned_no_text.pdf"
        if not scanned.exists():
            pytest.skip("Scanned test PDF not present")
        result = PDFExtractor().extract(scanned)
        assert result.total_rows == 0
        assert result.metadata.get("is_scanned") is True
        assert any("scanned" in e.lower() for e in result.errors)

    def test_scanned_pdf_returns_extraction_result(self):
        """Scanned PDF must return ExtractionResult (not raise)."""
        from data_processing.extractors.base import ExtractionResult
        scanned = ROOT / "datasets" / "invalid" / "scanned_no_text.pdf"
        if not scanned.exists():
            pytest.skip("Scanned test PDF not present")
        result = PDFExtractor().extract(scanned)
        assert isinstance(result, ExtractionResult)
        assert result.file_format == "pdf"

    def test_text_pdf_not_flagged_as_scanned(self):
        """A PDF with embedded text must NOT be flagged as scanned."""
        form_pdf = ROOT / "datasets" / "input" / "sample_form.pdf"
        if not form_pdf.exists():
            pytest.skip("sample_form.pdf not present")
        result = PDFExtractor().extract(form_pdf)
        assert result.metadata.get("is_scanned") is False

    def test_text_pdf_extracts_rows(self):
        """A text-based PDF with label:value content should produce at least one row."""
        form_pdf = ROOT / "datasets" / "input" / "sample_form.pdf"
        if not form_pdf.exists():
            pytest.skip("sample_form.pdf not present")
        result = PDFExtractor().extract(form_pdf)
        assert result.total_rows >= 1

    def test_missing_pdfplumber_handled(self, monkeypatch):
        """If pdfplumber is not available, return error result — do not raise."""
        import data_processing.extractors.pdf_extractor as pdf_mod
        monkeypatch.setattr(pdf_mod, "_PDF_AVAILABLE", False)
        result = PDFExtractor().extract("dummy.pdf")
        assert result.total_rows == 0
        assert len(result.errors) > 0


# ─── Factory / .xls rejection test ───────────────────────────

class TestXLSRejection:

    def test_xls_raises_not_supported(self, tmp_path):
        """Legacy .xls must raise ValueError — XLSX is the locked requirement."""
        f = tmp_path / "file.xls"
        f.touch()
        with pytest.raises(ValueError, match="xls"):
            get_extractor(f)

    def test_xlsx_still_works(self, tmp_path):
        """Removing .xls must not break .xlsx support."""
        import openpyxl
        rows = [{"name": "Alice", "email": "a@test.com"}]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(list(rows[0].keys()))
        ws.append(list(rows[0].values()))
        f = tmp_path / "file.xlsx"
        wb.save(f)
        from data_processing.extractors.xlsx_extractor import XLSXExtractor
        result = XLSXExtractor().extract(f)
        assert result.total_rows == 1


# ─── NDJSON / DB format consistency test ─────────────────────

class TestNDJSONDBFormat:

    def test_ndjson_extraction_format_is_ndjson(self, tmp_path):
        """Extractor labels NDJSON result as 'ndjson' for pipeline metadata.
        Two separate JSON objects on separate lines forces the NDJSON parse
        path (standard json.loads would fail on the combined string).
        """
        f = tmp_path / "test.ndjson"
        lines = [
            '{"name": "Alice", "email": "a@test.com"}',
            '{"name": "Bob",   "email": "b@test.com"}',
        ]
        f.write_text("\n".join(lines) + "\n")
        result = JSONExtractor().extract(f)
        assert result.file_format == "ndjson"

    def test_db_file_format_ndjson_maps_to_json(self, tmp_path):
        """db_file_format() must return 'json' for .ndjson files (DB enum value)."""
        from data_processing.extractors.factory import db_file_format
        f = tmp_path / "test.ndjson"
        f.touch()
        assert db_file_format(f) == "json"

    def test_db_file_format_csv_maps_to_csv(self, tmp_path):
        from data_processing.extractors.factory import db_file_format
        f = tmp_path / "test.csv"
        f.touch()
        assert db_file_format(f) == "csv"

    def test_db_file_format_xlsx_maps_to_xlsx(self, tmp_path):
        from data_processing.extractors.factory import db_file_format
        f = tmp_path / "test.xlsx"
        f.touch()
        assert db_file_format(f) == "xlsx"
