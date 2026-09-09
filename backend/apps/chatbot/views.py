from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import NotFoundError, ValidationAPIError
from common.db import session_scope
from database.schema.models import ProcessingBatch, UploadFile

from .services import query_customers


class ChatbotQueryView(APIView):
    """
    POST /api/chatbot/query/

    Request:

        {
            "query": "how many customers?",
            "batch_id": 6
        }

    batch_id is optional for backwards compatibility.

    When batch_id is supplied, the batch must belong to the
    authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_query = request.data.get("query")

        if not isinstance(user_query, str):
            raise ValidationAPIError(
                "'query' must be a string."
            )

        user_query = user_query.strip()

        if not user_query:
            raise ValidationAPIError(
                "'query' cannot be empty."
            )

        if len(user_query) > 500:
            raise ValidationAPIError(
                "'query' cannot exceed 500 characters."
            )

        # ---------------------------------------------------------
        # Parse batch_id
        # ---------------------------------------------------------

        batch_id_value = request.data.get("batch_id")

        batch_id = None

        if batch_id_value is not None and batch_id_value != "":
            try:
                batch_id = int(batch_id_value)
            except (TypeError, ValueError):
                raise ValidationAPIError(
                    "'batch_id' must be a valid integer."
                )

            if batch_id <= 0:
                raise ValidationAPIError(
                    "'batch_id' must be greater than 0."
                )

            # -----------------------------------------------------
            # Verify batch ownership
            # -----------------------------------------------------

            with session_scope() as session:
                batch = (
                    session.query(ProcessingBatch)
                    .join(
                        UploadFile,
                        UploadFile.batch_id == ProcessingBatch.id,
                    )
                    .filter(
                        ProcessingBatch.id == batch_id,
                        UploadFile.uploaded_by == request.user.id,
                    )
                    .first()
                )

            if batch is None:
                raise NotFoundError(
                    f"Processing batch {batch_id} not found."
                )

        # ---------------------------------------------------------
        # Execute chatbot query
        # ---------------------------------------------------------

        result = query_customers(
            user_query,
            batch_id=batch_id,
        )

        return Response(result)