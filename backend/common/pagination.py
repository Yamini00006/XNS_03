"""
backend/common/pagination.py

Standard pagination envelope used across list endpoints.

Query params: ?page=<int>&page_size=<int>
Response shape:
    {
        "count": <total records>,
        "page": <current page>,
        "page_size": <records per page>,
        "total_pages": <int>,
        "results": [...]
    }
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "total_pages": self.page.paginator.num_pages,
            "results": data,
        })


def paginate_list(items: list, page: int, page_size: int) -> dict:
    """
    Manual pagination helper for endpoints that build their result set
    from a raw SQLAlchemy query (list already sliced from the DB) rather
    than going through DRF's ListAPIView pagination machinery.
    """
    count = len(items)
    total_pages = max(1, (count + page_size - 1) // page_size)
    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }