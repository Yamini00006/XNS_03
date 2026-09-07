"""
data_processing/config/settings.py

Central configuration for the ETL pipeline.
All tuneable constants live here — no magic numbers scattered in code.
"""

import os

# ─── Pipeline version ─────────────────────────────────────────
PIPELINE_VERSION = "1.0.0"

# ─── Supported file formats ───────────────────────────────────
# Locked requirement: CSV, JSON, XLSX, XML, PDF.
# NDJSON is accepted as a JSON-family input (stored as "json" in the DB).
# Legacy .xls is NOT supported (openpyxl handles .xlsx only).
SUPPORTED_FORMATS = {"csv", "json", "ndjson", "xlsx", "xml", "pdf"}

# ─── Field name aliases ───────────────────────────────────────
# Maps many possible source column names → one canonical field name.
# Add more aliases as new data sources are onboarded.
FIELD_ALIASES: dict[str, list[str]] = {
    "email": [
        "email", "email_address", "e_mail", "emailaddress",
        "Email", "EMAIL", "Email Address", "customer_email",
    ],
    "phone": [
        "phone", "phone_number", "mobile", "telephone", "tel",
        "Phone", "PHONE", "Phone Number", "mobile_number", "cell",
    ],
    "first_name": [
        "first_name", "firstname", "given_name", "fname",
        "First Name", "FIRST_NAME", "first", "given",
    ],
    "last_name": [
        "last_name", "lastname", "surname", "family_name", "lname",
        "Last Name", "LAST_NAME", "last", "family",
    ],
    "full_name": [
        "full_name", "fullname", "name", "customer_name",
        "Full Name", "NAME", "Name",
    ],
    "address_line1": [
        "address", "address_line1", "address_line_1", "street",
        "street_address", "Address", "ADDRESS",
    ],
    "address_line2": [
        "address_line2", "address_line_2", "apt", "suite",
    ],
    "city": ["city", "City", "CITY", "town", "Town"],
    "state": ["state", "State", "STATE", "province", "Province", "region"],
    "postal_code": [
        "postal_code", "zip", "zip_code", "postcode", "Zip",
        "ZIP", "Postal Code", "ZIP Code",
    ],
    "country": ["country", "Country", "COUNTRY", "nation"],
    "created_date": [
        "created_date", "date_created", "signup_date", "registration_date",
        "created_at", "join_date",
    ],
}

# Reverse lookup: source column name → canonical name
_ALIAS_LOOKUP: dict[str, str] = {}
for canonical, aliases in FIELD_ALIASES.items():
    for alias in aliases:
        _ALIAS_LOOKUP[alias] = canonical
        _ALIAS_LOOKUP[alias.lower()] = canonical


def canonical_field(name: str) -> str:
    """Return the canonical field name for a source column, or the original if unknown."""
    return _ALIAS_LOOKUP.get(name, _ALIAS_LOOKUP.get(name.lower(), name))


# ─── Validation rules ─────────────────────────────────────────

# Fields that must be present (non-null, non-empty) for a row to be valid
REQUIRED_FIELDS: list[str] = []   # intentionally loose — warn rather than reject

# Fields where we raise a WARNING if missing (not ERROR)
IMPORTANT_FIELDS: list[str] = ["email", "phone", "full_name"]

# Email regex (simple but covers common cases)
EMAIL_REGEX = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"

# Phone: digits, spaces, dashes, dots, parens, leading +
PHONE_REGEX = r"^\+?[\d\s\-().]{7,20}$"

# Max length per field (for DB safety)
FIELD_MAX_LENGTHS: dict[str, int] = {
    "email":        255,
    "phone":        30,
    "first_name":   100,
    "last_name":    100,
    "full_name":    255,
    "address_line1": 255,
    "address_line2": 255,
    "city":         100,
    "state":        100,
    "postal_code":  20,
    "country":      100,
}

# ─── Deduplication ────────────────────────────────────────────

# Fields used to identify duplicate customers (in priority order)
# Two rows are considered duplicates if ALL present keys match
DEDUP_KEYS: list[list[str]] = [
    ["email"],                          # same email → same person
    ["phone", "full_name"],             # same phone + name
    ["first_name", "last_name", "postal_code"],  # same name + postal
]

# ─── PDF extraction ───────────────────────────────────────────
PDF_MAX_PAGES = 50          # ignore PDFs larger than this (safety limit)

# ─── Batch / performance ──────────────────────────────────────
LOADER_BATCH_SIZE = 500     # rows per DB insert batch

# ─── Paths ────────────────────────────────────────────────────
from pathlib import Path

ROOT_DIR       = Path(__file__).resolve().parents[2]
DATASETS_INPUT = ROOT_DIR / "datasets" / "input"
DATASETS_PROC  = ROOT_DIR / "datasets" / "processed"
DATASETS_BAD   = ROOT_DIR / "datasets" / "invalid"
