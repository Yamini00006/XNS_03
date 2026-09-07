"""
database/seed/seed.py

Generates realistic sample customer data and writes it to:
  datasets/input/   — valid files for normal processing
  datasets/invalid/ — files with intentional errors to test validation

Run:
  python database/seed/seed.py
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR   = ROOT / "datasets" / "input"
INVALID_DIR = ROOT / "datasets" / "invalid"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
INVALID_DIR.mkdir(parents=True, exist_ok=True)

# ─── Sample data pools ────────────────────────────────────────
FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank",
               "Grace", "Henry", "Iris", "Jack", "Karen", "Leo",
               "Mia", "Noah", "Olivia", "Paul", "Quinn", "Rachel"]
LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones",
               "Garcia", "Miller", "Davis", "Wilson", "Taylor",
               "Anderson", "Thomas", "Jackson", "White", "Harris"]
DOMAINS     = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "example.com"]
CITIES      = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
               "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin"]
STATES      = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "TX"]
COUNTRIES   = ["US", "US", "US", "UK", "CA", "AU"]


def rand_phone() -> str:
    return f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"


def rand_email(first: str, last: str) -> str:
    sep = random.choice([".", "_", ""])
    domain = random.choice(DOMAINS)
    return f"{first.lower()}{sep}{last.lower()}{random.randint(1,99)}@{domain}"


def rand_date(start_year=2020) -> str:
    start = datetime(start_year, 1, 1)
    delta = timedelta(days=random.randint(0, 1500))
    return (start + delta).strftime("%Y-%m-%d")


def make_customer(i: int) -> dict:
    first = random.choice(FIRST_NAMES)
    last  = random.choice(LAST_NAMES)
    idx   = random.randint(0, len(CITIES) - 1)
    return {
        "id":           i + 1,
        "first_name":   first,
        "last_name":    last,
        "email":        rand_email(first, last),
        "phone":        rand_phone(),
        "address":      f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Pine'])} St",
        "city":         CITIES[idx],
        "state":        STATES[idx],
        "postal_code":  f"{random.randint(10000, 99999)}",
        "country":      "US",
        "created_date": rand_date(),
    }


def generate_customers(n: int = 50) -> list[dict]:
    return [make_customer(i) for i in range(n)]


# ─── Write valid files ────────────────────────────────────────

def write_csv(customers: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=customers[0].keys())
        writer.writeheader()
        writer.writerows(customers)
    print(f"  ✓ {path.name}  ({len(customers)} rows)")


def write_json(customers: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=2)
    print(f"  ✓ {path.name}  ({len(customers)} records)")


def write_json_lines(customers: list[dict], path: Path) -> None:
    """Also support newline-delimited JSON."""
    with open(path, "w", encoding="utf-8") as f:
        for row in customers:
            f.write(json.dumps(row) + "\n")
    print(f"  ✓ {path.name}  ({len(customers)} records, NDJSON)")


def write_xml(customers: list[dict], path: Path) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<customers>"]
    for c in customers:
        lines.append("  <customer>")
        for k, v in c.items():
            lines.append(f"    <{k}>{v}</{k}>")
        lines.append("  </customer>")
    lines.append("</customers>")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {path.name}  ({len(customers)} records)")


def write_xlsx(customers: list[dict], path: Path) -> None:
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Customers"
        headers = list(customers[0].keys())
        ws.append(headers)
        for c in customers:
            ws.append([c[h] for h in headers])
        wb.save(path)
        print(f"  ✓ {path.name}  ({len(customers)} rows)")
    except ImportError:
        print("  ⚠  openpyxl not installed — skipping XLSX seed")


# ─── Write intentionally broken files for validation testing ──

def write_invalid_csv(path: Path) -> None:
    """CSV with missing fields, bad emails, duplicate rows."""
    rows = [
        # header
        "first_name,last_name,email,phone,city,country",
        # bad email
        "John,Doe,not-an-email,+1-555-0001,Boston,US",
        # missing email
        "Jane,Smith,,+1-555-0002,Seattle,US",
        # duplicate of row above
        "Jane,Smith,,+1-555-0002,Seattle,US",
        # missing phone
        "Bob,Brown,bob@example.com,,Denver,US",
        # completely empty row
        ",,,,,",
        # extra columns (schema drift)
        "Alice,Walker,alice@test.com,+1-555-0003,Miami,US,unexpected_extra_col",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")
    print(f"  ✓ {path.name}  (intentionally invalid)")


def write_invalid_json(path: Path) -> None:
    """JSON with wrong types and missing required fields."""
    data = [
        {"first_name": "Tom",  "last_name": "Hardy", "email": 12345,       "phone": "+1-555-1111", "city": "LA"},
        {"first_name": "Lucy", "last_name": None,     "email": "lucy@x.com","phone": None,           "city": "NY"},
        {"first_name": "Zara",                         "email": "zara@x.com","phone": "+1-555-2222"},  # missing last_name/city
    ]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  ✓ {path.name}  (intentionally invalid)")


def write_duplicate_csv(path: Path, base: list[dict]) -> None:
    """Subset of valid CSV but with 20% rows duplicated to test dedup."""
    duped = list(base[:20])
    duped += random.sample(base[:20], k=5)   # 5 duplicates
    random.shuffle(duped)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=base[0].keys())
        writer.writeheader()
        writer.writerows(duped)
    print(f"  ✓ {path.name}  ({len(duped)} rows, ~5 duplicates)")


# ─── Main ─────────────────────────────────────────────────────

def run() -> None:
    print("\n=== Generating seed datasets ===\n")

    customers_50 = generate_customers(50)
    customers_20 = generate_customers(20)

    print("Valid files → datasets/input/")
    write_csv(customers_50,  INPUT_DIR / "customers_50.csv")
    write_json(customers_50, INPUT_DIR / "customers_50.json")
    write_json_lines(customers_20, INPUT_DIR / "customers_20.ndjson")
    write_xml(customers_20,  INPUT_DIR / "customers_20.xml")
    write_xlsx(customers_50, INPUT_DIR / "customers_50.xlsx")

    print("\nInvalid files → datasets/invalid/")
    write_invalid_csv(INVALID_DIR / "bad_emails_missing_fields.csv")
    write_invalid_json(INVALID_DIR / "wrong_types.json")
    write_duplicate_csv(INVALID_DIR / "with_duplicates.csv", customers_50)

    print("\n✅ Seed complete.\n")


if __name__ == "__main__":
    run()
