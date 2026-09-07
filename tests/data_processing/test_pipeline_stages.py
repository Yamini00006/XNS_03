"""
tests/data_processing/test_pipeline_stages.py

Unit tests for transformer, validator, and merger stages.
No database required.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data_processing.schemas.detector import detect_schema, SchemaMapping
from data_processing.transformers.transformer import Transformer
from data_processing.validators.validator import Validator
from data_processing.merger.merger import Merger


# ─── Schema detection ─────────────────────────────────────────

class TestSchemaDetector:

    def test_maps_known_aliases(self):
        rows = [{"Email Address": "a@test.com", "Phone Number": "+1-555-0001", "First Name": "Alice"}]
        mapping = detect_schema(rows)
        assert mapping.column_map["Email Address"] == "email"
        assert mapping.column_map["Phone Number"] == "phone"
        assert mapping.column_map["First Name"] == "first_name"

    def test_unknown_columns_tracked(self):
        rows = [{"mystery_col": "value", "email": "a@test.com"}]
        mapping = detect_schema(rows)
        assert "mystery_col" in mapping.unknown_cols

    def test_apply_renames_row(self):
        rows = [{"Email Address": "a@test.com", "First Name": "Alice"}]
        mapping = detect_schema(rows)
        result = mapping.apply(rows[0])
        assert "email" in result
        assert "first_name" in result

    def test_empty_rows_returns_empty_mapping(self):
        mapping = detect_schema([])
        assert mapping.column_map == {}


# ─── Transformer ─────────────────────────────────────────────

class TestTransformer:

    def _make_mapping(self, rows):
        return detect_schema(rows)

    def test_email_lowercased(self):
        rows = [{"email": "ALICE@TEST.COM", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        assert result.rows[0]["email"] == "alice@test.com"

    def test_phone_stripped_of_symbols(self):
        rows = [{"phone": "(555) 123-4567", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        # Should keep only digits and +
        phone = result.rows[0]["phone"]
        assert all(c.isdigit() or c == "+" for c in phone)

    def test_name_title_cased(self):
        rows = [{"first_name": "ALICE", "last_name": "SMITH", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        assert result.rows[0]["first_name"] == "Alice"
        assert result.rows[0]["last_name"] == "Smith"

    def test_full_name_synthesized_from_parts(self):
        rows = [{"first_name": "Alice", "last_name": "Smith", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        assert result.rows[0]["full_name"] == "Alice Smith"

    def test_empty_string_becomes_none(self):
        rows = [{"email": "", "phone": "   ", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        assert result.rows[0]["email"] is None
        assert result.rows[0]["phone"] is None

    def test_country_normalized(self):
        rows = [{"country": "united states", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        assert result.rows[0]["country"] == "US"

    def test_unknown_columns_preserved(self):
        rows = [{"email": "a@test.com", "loyalty_tier": "gold", "_source_row": 1}]
        mapping = self._make_mapping(rows)
        result = Transformer().transform(rows, mapping)
        assert result.rows[0].get("loyalty_tier") == "gold"

    def test_alias_mapped_correctly(self):
        rows = [{"Email Address": "alice@test.com", "_source_row": 1}]
        mapping = detect_schema(rows)
        result = Transformer().transform(rows, mapping)
        # After mapping, key should be "email"
        assert result.rows[0].get("email") == "alice@test.com"


# ─── Validator ────────────────────────────────────────────────

class TestValidator:

    def _row(self, **kwargs):
        base = {"_source_row": 1, "email": "alice@test.com", "first_name": "Alice", "last_name": "Smith"}
        base.update(kwargs)
        return base

    def test_valid_row_passes(self):
        result = Validator().validate([self._row()])
        assert len(result.valid_rows) == 1
        assert len(result.invalid_rows) == 0

    def test_invalid_email_rejected(self):
        result = Validator().validate([self._row(email="not-an-email")])
        assert len(result.invalid_rows) == 1
        codes = [i.error_code for i in result.issues]
        assert "INVALID_EMAIL" in codes

    def test_empty_row_rejected(self):
        result = Validator().validate([{"_source_row": 1}])
        assert len(result.invalid_rows) == 1
        codes = [i.error_code for i in result.issues]
        assert "EMPTY_ROW" in codes

    def test_missing_phone_warning_not_error(self):
        result = Validator().validate([self._row(phone=None)])
        # Missing phone is a warning → row still valid
        assert len(result.valid_rows) == 1
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert any(i.field_name == "phone" for i in warnings)

    def test_multiple_rows_counted_correctly(self):
        rows = [
            self._row(_source_row=1),
            self._row(_source_row=2, email="bad-email"),
            self._row(_source_row=3),
        ]
        result = Validator().validate(rows)
        assert result.total_rows == 3
        assert len(result.valid_rows) == 2
        assert len(result.invalid_rows) == 1

    def test_error_count_and_warning_count(self):
        rows = [
            self._row(_source_row=1, email="bad"),   # error
            self._row(_source_row=2, phone=None),    # warning
        ]
        result = Validator().validate(rows)
        assert result.error_count >= 1
        assert result.warning_count >= 1


# ─── Merger ───────────────────────────────────────────────────

class TestMerger:

    def _row(self, email, phone=None, first_name="Alice", last_name="Smith", postal_code="10001", **kwargs):
        row = {
            "email": email, "phone": phone,
            "first_name": first_name, "last_name": last_name,
            "postal_code": postal_code,
        }
        row.update(kwargs)
        return row

    def test_no_duplicates_unchanged(self):
        # Two rows with different emails AND different names/postcodes.
        # None of the three dedup key-sets should match:
        #   ["email"]                              -> different emails
        #   ["phone", "full_name"]               -> both phone=None, skipped (None not matched)
        #   ["first_name", "last_name", "postal_code"] -> different names and postal codes
        row1 = self._row("a@test.com", first_name="Alice", last_name="Smith",  postal_code="10001")
        row2 = self._row("b@test.com", first_name="Bob",   last_name="Taylor", postal_code="20002")
        result = Merger().merge([row1, row2])
        assert result.unique_count == 2
        assert result.duplicate_count == 0

    def test_exact_email_duplicate_removed(self):
        rows = [self._row("a@test.com"), self._row("a@test.com")]
        result = Merger().merge(rows)
        assert result.unique_count == 1
        assert result.duplicate_count == 1

    def test_more_complete_record_wins(self):
        primary   = self._row("a@test.com", phone=None, first_name="Alice")
        secondary = self._row("a@test.com", phone="+1-555-1234", first_name="Alice")
        result = Merger().merge([primary, secondary])
        assert result.unique_count == 1
        # Phone from secondary should fill the gap
        assert result.merged_rows[0]["phone"] == "+1-555-1234"

    def test_source_count_incremented(self):
        rows = [self._row("a@test.com"), self._row("a@test.com")]
        result = Merger().merge(rows)
        assert result.merged_rows[0]["source_count"] == 2

    def test_name_plus_postal_dedup(self):
        rows = [
            self._row("a@test.com",   first_name="Alice", last_name="Smith", postal_code="10001"),
            self._row(None,            first_name="Alice", last_name="Smith", postal_code="10001"),
        ]
        result = Merger().merge(rows)
        assert result.unique_count == 1

    def test_empty_list(self):
        result = Merger().merge([])
        assert result.unique_count == 0
        assert result.duplicate_count == 0

    def test_duplicate_csv_has_duplicates(self):
        """Integration-ish: run merger on the seed duplicate file."""
        import csv
        dup_file = ROOT / "datasets" / "invalid" / "with_duplicates.csv"
        if not dup_file.exists():
            pytest.skip("Seed data not generated yet")
        with open(dup_file, newline="") as f:
            rows = list(csv.DictReader(f))
        result = Merger().merge(rows)
        # We seeded 25 rows with ~5 duplicates → should have fewer unique
        assert result.unique_count < 25
        assert result.duplicate_count >= 1
