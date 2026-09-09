from unittest.mock import patch

from apps.chatbot.services import query_customers


class FakeQuery:
    def scalar(self):
        return 25


class FakeSession:
    def query(self, *args, **kwargs):
        return FakeQuery()


def test_chatbot_count_customers():
    with patch(
        "apps.chatbot.services.session_scope"
    ) as mocked_scope:

        mocked_scope.return_value.__enter__.return_value = FakeSession()

        result = query_customers("how many customers")

        assert result["intent"] == "count"
        assert result["count"] == 25
        assert "25" in result["message"]