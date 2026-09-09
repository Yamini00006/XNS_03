"""
backend/apps/exports/views.py

    GET /api/exports/csv/    — ?ids=1,2,3 for selected records, omit for full dataset
    GET /api/exports/xlsx/
    GET /api/exports/json/

Exports the standardized `customers` table (the Data Explorer's data
source). All three formats support the same ?ids= filter.
"""

from __future__ import annotations

import csv
import io
import json

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.db import session_scope, to_dict
from common.exceptions import ValidationAPIError
from database.schema.models import Customer

_EXPORT_COLUMNS = [
    "id", "email", "phone", "full_name", "first_name", "last_name",
    "address_line1", "address_line2", "city", "state", "postal_code",
    "country", "source_count", "is_duplicate", "created_at", "updated_at",
]


def _parse_ids(request) -> list[int] | None:
    raw = request.query_params.get("ids")
    if not raw:
        return None
    try:
        return [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise ValidationAPIError("'ids' must be a comma-separated list of integers.")


def _fetch_rows(ids: list[int] | None) -> list[dict]:
    with session_scope() as session:
        query = session.query(Customer)
        if ids is not None:
            query = query.filter(Customer.id.in_(ids))
        rows = query.order_by(Customer.id.asc()).all()
        return [to_dict(r) for r in rows]


class BaseExportView(APIView):
    permission_classes = [IsAuthenticated]

    def _rows(self, request) -> list[dict]:
        ids = _parse_ids(request)
        return _fetch_rows(ids)


class CSVExportView(BaseExportView):
    def get(self, request):
        rows = self._rows(request)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_EXPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="customers_export.csv"'
        return response


class XLSXExportView(BaseExportView):
    def get(self, request):
        from openpyxl import Workbook

        rows = self._rows(request)
        wb = Workbook()
        ws = wb.active
        ws.title = "Customers"
        ws.append(_EXPORT_COLUMNS)
        for row in rows:
            ws.append([row.get(col) for col in _EXPORT_COLUMNS])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="customers_export.xlsx"'
        return response


class JSONExportView(BaseExportView):
    def get(self, request):
        rows = self._rows(request)
        payload = json.dumps({"count": len(rows), "results": rows}, indent=2)

        response = HttpResponse(payload, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="customers_export.json"'
        return response