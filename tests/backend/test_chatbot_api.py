import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from unittest.mock import patch


@pytest.mark.django_db
def test_chatbot_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/chatbot/query/",
        {
            "query": "how many customers",
        },
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
            {
                "query": "how many customers",
            },
            format="json",
        )

    assert response.status_code == 200
    assert response.data["intent"] == "count"
    assert response.data["count"] == 10

    mocked_query.assert_called_once_with(
        "how many customers",
        batch_id=None,
    )


@pytest.mark.django_db
def test_chatbot_query_with_batch_id():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_batch_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "apps.chatbot.views.query_customers"
    ) as mocked_query, patch(
        "apps.chatbot.views.session_scope"
    ) as mocked_session_scope:

        # Mock the SQLAlchemy session used to verify ownership.
        mocked_session = mocked_session_scope.return_value.__enter__.return_value

        mocked_batch = object()

        mocked_session.query.return_value.join.return_value.filter.return_value.first.return_value = (
            mocked_batch
        )

        mocked_query.return_value = {
            "query": "how many customers",
            "intent": "count",
            "message": "There are 5 customers in processing batch 6.",
            "count": 5,
            "results": [],
        }

        response = client.post(
            "/api/chatbot/query/",
            {
                "query": "how many customers",
                "batch_id": 6,
            },
            format="json",
        )

    assert response.status_code == 200
    assert response.data["count"] == 5

    mocked_query.assert_called_once_with(
        "how many customers",
        batch_id=6,
    )


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
        {
            "query": "",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_chatbot_rejects_non_string_query():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_type_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/chatbot/query/",
        {
            "query": 123,
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_chatbot_rejects_long_query():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_length_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/chatbot/query/",
        {
            "query": "a" * 501,
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_chatbot_rejects_invalid_batch_id():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_invalid_batch_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/chatbot/query/",
        {
            "query": "how many customers",
            "batch_id": "invalid",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_chatbot_rejects_non_positive_batch_id():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_zero_batch_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/chatbot/query/",
        {
            "query": "how many customers",
            "batch_id": 0,
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_chatbot_rejects_batch_not_owned_by_user():
    User = get_user_model()

    user = User.objects.create_user(
        username="chatbot_ownership_test",
        password="TestPassword123!",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "apps.chatbot.views.session_scope"
    ) as mocked_session_scope:

        mocked_session = (
            mocked_session_scope
            .return_value
            .__enter__
            .return_value
        )

        mocked_session.query.return_value.join.return_value.filter.return_value.first.return_value = (
            None
        )

        response = client.post(
            "/api/chatbot/query/",
            {
                "query": "how many customers",
                "batch_id": 999,
            },
            format="json",
        )

    assert response.status_code == 404