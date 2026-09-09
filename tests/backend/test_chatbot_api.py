import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch


@pytest.mark.django_db
def test_chatbot_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/chatbot/query/",
        {"query": "how many customers"},
        format="json",
    )

    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_chatbot_query():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "apps.chatbot.views.query_customers"
    ) as mocked_query:

        mocked_query.return_value = {
            "query": "how many customers",
            "intent": "count",
            "message": "There are 10 customers.",
            "count": 10,
            "results": [],
        }

        response = client.post(
            "/api/chatbot/query/",
            {"query": "how many customers"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["intent"] == "count"
    assert response.data["count"] == 10


@pytest.mark.django_db
def test_chatbot_rejects_empty_query():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_empty_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/chatbot/query/",
        {"query": ""},
        format="json",
    )

    assert response.status_code == 400