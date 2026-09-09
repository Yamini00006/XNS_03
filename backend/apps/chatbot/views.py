from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ValidationAPIError

from .services import query_customers


class ChatbotQueryView(APIView):
    """
    POST /api/chatbot/query/

    Request:
        {
            "query": "how many customers?"
        }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_query = request.data.get("query")

        if not isinstance(user_query, str):
            raise ValidationAPIError("'query' must be a string.")

        user_query = user_query.strip()

        if not user_query:
            raise ValidationAPIError("'query' cannot be empty.")

        if len(user_query) > 500:
            raise ValidationAPIError("'query' cannot exceed 500 characters.")

        result = query_customers(user_query)

        return Response(result)