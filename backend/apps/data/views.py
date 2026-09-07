"""
backend/apps/data/views.py

Data Explorer API over the standardized `customers` golden-record table.

    GET /api/data/          — search, filter, sort, paginate
    GET /api/data/{id}/     — single customer record
    GET /api/data/{id}/raw/ — raw source rows this customer was built from
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sqlalchemy import or_

from common.db import session_scope, to_dict
from common.exceptions import NotFoundError, ValidationAPIError
from common.pagination import paginate_list
from common.query_params import parse_page, parse_sort

from database.schema.models import Customer, CustomerSource

_SORTABLE_FIELDS = {
    "id", "email", "full_name", "first_name", "last_name",
    "city", "state", "country", "created_at", "updated_at", "source_count",
}

_SEARCHABLE_FIELDS = ("email", "full_name", "first_name", "last_name", "phone", "city")

_FILTERABLE_FIELDS = ("city", "state", "country", "postal_code")


class CustomerListView(APIView):
    """
    GET /api/data/

    Query params:
      page, page_size
      search=<text>           — matches email/full_name/first_name/last_name/phone/city
      sort=<field> | -<field> — default -created_at
      city=, state=, country=, postal_code= — exact-match filters
      is_duplicate=true|false
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page, page_size = parse_page(request)
        sort_field, descending = parse_sort(request, _SORTABLE_FIELDS, default="-created_at")
        search = request.query_params.get("search", "").strip()

        with session_scope() as session:
            query = session.query(Customer)

            if search:
                like = f"%{search}%"
                conditions = [getattr(Customer, f).ilike(like) for f in _SEARCHABLE_FIELDS]
                query = query.filter(or_(*conditions))

            for field in _FILTERABLE_FIELDS:
                value = request.query_params.get(field)
                if value:
                    query = query.filter(getattr(Customer, field) == value)

            is_dup = request.query_params.get("is_duplicate")
            if is_dup is not None:
                if is_dup.lower() not in ("true", "false"):
                    raise ValidationAPIError("'is_duplicate' must be 'true' or 'false'.")
                query = query.filter(Customer.is_duplicate == (is_dup.lower() == "true"))

            total = query.count()

            column = getattr(Customer, sort_field)
            query = query.order_by(column.desc() if descending else column.asc())

            rows = query.offset((page - 1) * page_size).limit(page_size).all()
            results = [to_dict(r) for r in rows]

        meta = paginate_list(range(total), page, page_size)
        meta["results"] = results
        return Response(meta)


class CustomerDetailView(APIView):
    """GET /api/data/{id}/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id: int):
        with session_scope() as session:
            record = session.get(Customer, customer_id)
            if record is None:
                raise NotFoundError(f"Customer {customer_id} not found.")
            data = to_dict(record)
        return Response(data)


class CustomerRawView(APIView):
    """GET /api/data/{id}/raw/ — the original source row(s) this customer was merged from."""
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id: int):
        with session_scope() as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                raise NotFoundError(f"Customer {customer_id} not found.")

            sources = (
                session.query(CustomerSource)
                .filter(CustomerSource.customer_id == customer_id)
                .order_by(CustomerSource.id.asc())
                .all()
            )
            results = [to_dict(s) for s in sources]

        return Response({"customer_id": customer_id, "sources": results})