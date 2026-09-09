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


MISSING_FIELD_MAP = {
    "email": Customer.email,
    "phone": Customer.phone,
    "name": Customer.full_name,
    "full name": Customer.full_name,
    "first name": Customer.first_name,
    "last name": Customer.last_name,
    "city": Customer.city,
    "state": Customer.state,
    "country": Customer.country,
    "postal code": Customer.postal_code,
}


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


def _extract_limit(
    query: str,
    default: int = 10,
    maximum: int = 50,
) -> int:
    """
    Extract a requested result limit.

    Examples:
        show 5 customers
        show top 20 customers
        list first 3 customers
        limit 10 customers
    """

    words = query.lower().split()

    for index, word in enumerate(words):
        if word.isdigit():
            value = int(word)

            if index > 0 and words[index - 1] in {
                "show",
                "top",
                "first",
                "limit",
            }:
                return min(max(value, 1), maximum)

    return default


def _apply_batch_filter(
    query,
    batch_id: int | None,
):
    """
    Restrict a SQLAlchemy Customer query to one processing batch.
    """

    if batch_id is not None:
        query = query.filter(
            Customer.batch_id == batch_id
        )

    return query


def _count_query(
    session,
    filters=None,
) -> int:
    """
    Count Customer records using a dedicated SQLAlchemy COUNT query.

    This is used instead of Query.count() so that counting remains
    compatible with the existing test session abstraction.
    """

    count_query = session.query(
        func.count(Customer.id)
    )

    if filters:
        for condition in filters:
            count_query = count_query.filter(
                condition
            )

    return count_query.scalar() or 0


def _build_response(
    query_text: str,
    intent: str,
    message: str,
    count: int,
    rows: list[Customer],
) -> dict[str, Any]:
    return {
        "query": query_text,
        "intent": intent,
        "message": message,
        "count": count,
        "results": [
            _serialize_customer(row)
            for row in rows
        ],
    }


def _is_missing(column):
    """
    Treat both NULL and empty/whitespace-only strings
    as missing.
    """

    return or_(
        column.is_(None),
        func.trim(column) == "",
    )


def query_customers(
    user_query: str,
    batch_id: int | None = None,
) -> dict[str, Any]:
    """
    Deterministic chatbot over the standardized customers table.

    Supported examples:

      - "how many customers"
      - "what is the total number of customers"
      - "count customers"

      - "show customers"
      - "show 5 customers"

      - "customers in chennai"
      - "how many customers are from chennai"

      - "customers from tamil nadu"
      - "how many customers are from india"

      - "search john"
      - "find john@example.com"
      - "find John Doe"

      - "show duplicate customers"
      - "how many duplicate customers"

      - "show customers with missing email"
      - "how many customers have missing phone"

    When batch_id is supplied, all queries are restricted
    to that processing batch.
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

    normalized = " ".join(
        query_text.lower().split()
    )

    limit = _extract_limit(query_text)

    with session_scope() as session:

        # =========================================================
        # BASE QUERY
        # =========================================================

        base_query = session.query(Customer)

        base_query = _apply_batch_filter(
            base_query,
            batch_id,
        )

        batch_filter = []

        if batch_id is not None:
            batch_filter.append(
                Customer.batch_id == batch_id
            )

        # =========================================================
        # COUNT DETECTION
        # =========================================================

        is_count_query = (
            "how many" in normalized
            or "count" in normalized
            or "number of customers" in normalized
            or "total number of customers" in normalized
            or normalized.startswith("total customers")
        )

        # =========================================================
        # DUPLICATES
        # =========================================================

        if "duplicate" in normalized:

            duplicate_filter = [
                Customer.is_duplicate.is_(True)
            ]

            duplicate_filters = (
                batch_filter
                + duplicate_filter
            )

            if is_count_query:
                count = _count_query(
                    session,
                    duplicate_filters,
                )

                return _build_response(
                    query_text=query_text,
                    intent="duplicate_count",
                    message=(
                        f"There are {count} "
                        "duplicate customer records."
                    ),
                    count=count,
                    rows=[],
                )

            duplicate_query = base_query.filter(
                Customer.is_duplicate.is_(True)
            )

            rows = (
                duplicate_query
                .order_by(Customer.id.asc())
                .limit(limit)
                .all()
            )

            return _build_response(
                query_text=query_text,
                intent="duplicates",
                message=(
                    f"Found {len(rows)} "
                    "duplicate customer records."
                ),
                count=len(rows),
                rows=rows,
            )

        # =========================================================
        # MISSING FIELD
        # =========================================================

        if (
            "missing" in normalized
            or "without" in normalized
            or "no email" in normalized
            or "no phone" in normalized
        ):

            missing_field = None

            for field_name in (
                "email",
                "phone",
                "full name",
                "name",
                "first name",
                "last name",
                "city",
                "state",
                "country",
                "postal code",
            ):
                if field_name in normalized:
                    missing_field = field_name
                    break

            if missing_field:
                column = MISSING_FIELD_MAP[
                    missing_field
                ]

                missing_condition = _is_missing(
                    column
                )

                if is_count_query:
                    count = _count_query(
                        session,
                        batch_filter
                        + [missing_condition],
                    )

                    return _build_response(
                        query_text=query_text,
                        intent="missing_count",
                        message=(
                            f"There are {count} "
                            "customer records with "
                            f"missing {missing_field}."
                        ),
                        count=count,
                        rows=[],
                    )

                missing_query = base_query.filter(
                    missing_condition
                )

                rows = (
                    missing_query
                    .order_by(Customer.id.asc())
                    .limit(limit)
                    .all()
                )

                return _build_response(
                    query_text=query_text,
                    intent="missing",
                    message=(
                        f"Found {len(rows)} customer "
                        "records with missing "
                        f"{missing_field}."
                    ),
                    count=len(rows),
                    rows=rows,
                )

        # =========================================================
        # CITY / LOCATION FILTER
        # =========================================================

        location_prefixes = (
            ("city", "customers in "),
            ("city", "customer in "),
            ("city", "people in "),
            ("city", "users in "),
            ("location", "customers from "),
            ("location", "customer from "),
            ("location", "people from "),
            ("location", "users from "),
        )

        location_value = None
        location_type = None

        for field_type, prefix in location_prefixes:
            if normalized.startswith(prefix):
                location_value = query_text[
                    len(prefix):
                ].strip()

                location_type = field_type
                break

        if location_value:

            # -----------------------------------------------------
            # "customers from India"
            #
            # Search city, state and country.
            # -----------------------------------------------------

            if normalized.startswith(
                (
                    "customers from ",
                    "customer from ",
                    "people from ",
                    "users from ",
                )
            ):

                location_conditions = [
                    Customer.city.ilike(
                        location_value
                    ),
                    Customer.state.ilike(
                        location_value
                    ),
                    Customer.country.ilike(
                        location_value
                    ),
                ]

                location_condition = or_(
                    *location_conditions
                )

                if is_count_query:
                    count = _count_query(
                        session,
                        batch_filter
                        + [location_condition],
                    )

                    return _build_response(
                        query_text=query_text,
                        intent="location_count",
                        message=(
                            f"There are {count} "
                            "customer records "
                            f"matching {location_value}."
                        ),
                        count=count,
                        rows=[],
                    )

                location_query = base_query.filter(
                    location_condition
                )

                rows = (
                    location_query
                    .order_by(Customer.id.asc())
                    .limit(limit)
                    .all()
                )

                return _build_response(
                    query_text=query_text,
                    intent="location_filter",
                    message=(
                        f"Found {len(rows)} customer "
                        "records matching "
                        f"{location_value}."
                    ),
                    count=len(rows),
                    rows=rows,
                )

            # -----------------------------------------------------
            # "customers in Chennai"
            #
            # Specifically treats "in" as city.
            # -----------------------------------------------------

            city_condition = Customer.city.ilike(
                location_value
            )

            if is_count_query:
                count = _count_query(
                    session,
                    batch_filter
                    + [city_condition],
                )

                return _build_response(
                    query_text=query_text,
                    intent="city_count",
                    message=(
                        f"There are {count} "
                        "customer records in "
                        f"{location_value}."
                    ),
                    count=count,
                    rows=[],
                )

            city_query = base_query.filter(
                city_condition
            )

            rows = (
                city_query
                .order_by(Customer.id.asc())
                .limit(limit)
                .all()
            )

            return _build_response(
                query_text=query_text,
                intent="city_filter",
                message=(
                    f"Found {len(rows)} customer "
                    "records in "
                    f"{location_value}."
                ),
                count=len(rows),
                rows=rows,
            )

        # =========================================================
        # EXPLICIT STATE
        # =========================================================

        state_markers = (
            "state ",
            "from state ",
            "in state ",
        )

        for marker in state_markers:

            if marker in normalized:

                state_value = normalized.split(
                    marker,
                    1,
                )[1].strip()

                if state_value:

                    state_condition = (
                        Customer.state.ilike(
                            state_value
                        )
                    )

                    if is_count_query:
                        count = _count_query(
                            session,
                            batch_filter
                            + [state_condition],
                        )

                        return _build_response(
                            query_text=query_text,
                            intent="state_count",
                            message=(
                                f"There are {count} "
                                "customer records in "
                                f"state {state_value}."
                            ),
                            count=count,
                            rows=[],
                        )

                    state_query = base_query.filter(
                        state_condition
                    )

                    rows = (
                        state_query
                        .order_by(Customer.id.asc())
                        .limit(limit)
                        .all()
                    )

                    return _build_response(
                        query_text=query_text,
                        intent="state_filter",
                        message=(
                            f"Found {len(rows)} "
                            "customer records in "
                            f"state {state_value}."
                        ),
                        count=len(rows),
                        rows=rows,
                    )

        # =========================================================
        # EXPLICIT COUNTRY
        # =========================================================

        country_markers = (
            "country ",
            "from country ",
            "in country ",
        )

        for marker in country_markers:

            if marker in normalized:

                country_value = normalized.split(
                    marker,
                    1,
                )[1].strip()

                if country_value:

                    country_condition = (
                        Customer.country.ilike(
                            country_value
                        )
                    )

                    if is_count_query:
                        count = _count_query(
                            session,
                            batch_filter
                            + [country_condition],
                        )

                        return _build_response(
                            query_text=query_text,
                            intent="country_count",
                            message=(
                                f"There are {count} "
                                "customer records in "
                                f"country {country_value}."
                            ),
                            count=count,
                            rows=[],
                        )

                    country_query = (
                        base_query.filter(
                            country_condition
                        )
                    )

                    rows = (
                        country_query
                        .order_by(Customer.id.asc())
                        .limit(limit)
                        .all()
                    )

                    return _build_response(
                        query_text=query_text,
                        intent="country_filter",
                        message=(
                            f"Found {len(rows)} "
                            "customer records in "
                            f"country {country_value}."
                        ),
                        count=len(rows),
                        rows=rows,
                    )

        # =========================================================
        # GENERAL COUNT
        # =========================================================

        if is_count_query:

            count = _count_query(
                session,
                batch_filter,
            )

            if batch_id is not None:
                message = (
                    f"There are {count} customers "
                    f"in processing batch {batch_id}."
                )
            else:
                message = (
                    f"There are {count} customers."
                )

            return _build_response(
                query_text=query_text,
                intent="count",
                message=message,
                count=count,
                rows=[],
            )

        # =========================================================
        # GENERAL SEARCH / LIST
        # =========================================================

        search_text = normalized

        for prefix in (
            "search for ",
            "search ",
            "find ",
            "show ",
            "list ",
        ):
            if search_text.startswith(prefix):
                search_text = search_text[
                    len(prefix):
                ].strip()
                break

        # Remove generic words.
        for generic_word in (
            "customers",
            "customer",
            "records",
            "record",
        ):
            search_text = search_text.replace(
                generic_word,
                "",
            ).strip()

        # ---------------------------------------------------------
        # LIST
        # ---------------------------------------------------------

        if not search_text:

            rows = (
                base_query
                .order_by(Customer.id.asc())
                .limit(limit)
                .all()
            )

            return _build_response(
                query_text=query_text,
                intent="list",
                message=(
                    f"Showing {len(rows)} "
                    "customer records."
                ),
                count=len(rows),
                rows=rows,
            )

        # =========================================================
        # GENERAL SEARCH
        # =========================================================

        like = f"%{search_text}%"

        conditions = [
            getattr(Customer, field).ilike(like)
            for field in SEARCHABLE_FIELDS
        ]

        search_condition = or_(
            *conditions
        )

        search_query = base_query.filter(
            search_condition
        )

        rows = (
            search_query
            .order_by(Customer.id.asc())
            .limit(limit)
            .all()
        )

        return _build_response(
            query_text=query_text,
            intent="search",
            message=(
                f"Found {len(rows)} matching "
                "customer records."
            ),
            count=len(rows),
            rows=rows,
        )