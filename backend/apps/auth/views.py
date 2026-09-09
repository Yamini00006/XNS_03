from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.exceptions import ValidationAPIError


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds authenticated user information to the login response."""

    def validate(self, attrs):
        data = super().validate(attrs)

        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "is_staff": self.user.is_staff,
        }

        return data


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Body:
        {
            "username": "...",
            "password": "..."
        }
    """

    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    """
    POST /api/auth/refresh/

    Body:
        {
            "refresh": "..."
        }
    """

    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Body:
        {
            "refresh": "..."
        }

    Requires a valid access token.

    The refresh token must belong to the currently authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            raise ValidationAPIError("'refresh' token is required.")

        try:
            token = RefreshToken(refresh_token)

            token_user_id = token.get("user_id")

            if token_user_id is None:
                raise ValidationAPIError("Refresh token does not contain a user identity.")

            if int(token_user_id) != request.user.id:
                raise ValidationAPIError(
                    "The refresh token does not belong to the authenticated user."
                )

            token.blacklist()

        except TokenError as exc:
            raise ValidationAPIError(
                f"Invalid or expired refresh token: {exc}"
            )

        return Response(status=status.HTTP_205_RESET_CONTENT)