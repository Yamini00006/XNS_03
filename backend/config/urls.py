"""
backend/config/urls.py

Top-level URL routing. Each Member-2 app owns its own urls.py; this file
just mounts them under /api/<app>/.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("apps.auth.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/files/", include("apps.files.urls")),
    path("api/processing/", include("apps.processing.urls")),
    path("api/data/", include("apps.data.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/exports/", include("apps.exports.urls")),
    path("api/chatbot/", include("apps.chatbot.urls")),
]