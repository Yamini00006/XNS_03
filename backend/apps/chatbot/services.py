from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_

from common.db import session_scope
from database.schema.models import Customer


SEARCHABLE_FIELDS = (
    "email",
    "full_name",
    "first_name",
    "last_name",
    "phone",
    "city",
    "state",
    "country",
)


def _serialize_customer(customer: Customer) -> dict[str, Any]:
    return {
        "id": customer.id,
        "email": customer.email,
        "phone": customer.phone,
        "full_name": customer.full_name,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "city": customer.city,
        "state": customer.state,
        "postal_code": customer.postal_code,
        "country": customer.country,
        "source_count": customer.source_count,
        "is_duplicate": customer.is_duplicate,
    }


def _extract_limit(query: str, default: int = 10, maximum: int = 50) -> int:
    words = query.lower().split()

    for index, word in enumerate(words):
        if word.isdigit():
            value = int(word)

            # Accept phrases such as "show 5 customers"
            if index > 0 and words[index - 1] in {"show", "top", "first", "limit"}:
                return min(max(value, 1), maximum)

    return default


def query_customers(user_query: str) -> dict[str, Any]:
    """
    Simple deterministic chatbot over the customers table.

    Supported examples:
      - "how many customers"
      - "count customers"
      - "show customers"
      - "show 5 customers"
      - "customers in chennai"
      - "search john"
      - "find john@example.com"
      - "show duplicate customers"
    """

    query_text = (user_query or "").strip()

    if not query_text:
        return {
            "query": query_text,
            "intent": "invalid",
            "message": "Please provide a customer-related query.",
            "count": 0,
            "results": [],
        }

    normalized = query_text.lower()
    limit = _extract_limit(query_text)

    with session_scope() as session:
        # ---------------------------------------------------------
        # COUNT
        # ---------------------------------------------------------
        if (
            "how many" in normalized
            or "count" in normalized
            or "number of customers" in normalized
        ):
            count = session.query(func.count(Customer.id)).scalar() or 0

            return {
                "query": query_text,
                "intent": "count",
                "message": f"There are {count} customers.",
                "count": count,
                "results": [],
            }

        # ---------------------------------------------------------
        # DUPLICATES
        # ---------------------------------------------------------
        if "duplicate" in normalized:
            rows = (
                session.query(Customer)
                .filter(Customer.is_duplicate.is_(True))
                .order_by(Customer.id.asc())
                .limit(limit)
                .all()
            )

            return {
                "query": query_text,
                "intent": "duplicates",
                "message": f"Found duplicate customer records.",
                "count": len(rows),
                "results": [_serialize_customer(row) for row in rows],
            }

        # ---------------------------------------------------------
        # CITY FILTER
        # ---------------------------------------------------------
        city_prefixes = (
            "customers in ",
            "customer in ",
            "people in ",
            "users in ",
        )

        for prefix in city_prefixes:
            if normalized.startswith(prefix):
                city = query_text[len(prefix):].strip()

                rows = (
                    session.query(Customer)
                    .filter(Customer.city.ilike(city))
                    .order_by(Customer.id.asc())
                    .limit(limit)
                    .all()
                )

                return {
                    "query": query_text,
                    "intent": "city_filter",
                    "message": f"Found {len(rows)} customer records in {city}.",
                    "count": len(rows),
                    "results": [_serialize_customer(row) for row in rows],
                }

        # ---------------------------------------------------------
        # GENERAL SEARCH
        # ---------------------------------------------------------
        search_text = normalized

        for prefix in (
            "search for ",
            "search ",
            "find ",
            "show ",
            "list ",
        ):
            if search_text.startswith(prefix):
                search_text = search_text[len(prefix):].strip()
                break

        # Remove generic words that should not become search terms.
        search_text = search_text.replace("customers", "").strip()

        if not search_text:
            rows = (
                session.query(Customer)
                .order_by(Customer.id.asc())
                .limit(limit)
                .all()
            )

            return {
                "query": query_text,
                "intent": "list",
                "message": f"Showing {len(rows)} customer records.",
                "count": len(rows),
                "results": [_serialize_customer(row) for row in rows],
            }

        like = f"%{search_text}%"

        conditions = [
            getattr(Customer, field).ilike(like)
            for field in SEARCHABLE_FIELDS
        ]

        rows = (
            session.query(Customer)
            .filter(or_(*conditions))
            .order_by(Customer.id.asc())
            .limit(limit)
            .all()
        )

        return {
            "query": query_text,
            "intent": "search",
            "message": f"Found {len(rows)} matching customer records.",
            "count": len(rows),
            "results": [_serialize_customer(row) for row in rows],
        }