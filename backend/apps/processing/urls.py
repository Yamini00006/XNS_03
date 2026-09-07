from django.urls import path

from .views import (
    ProcessingDetailView,
    ProcessingErrorsView,
    ProcessingListView,
    StartProcessingView,
)

urlpatterns = [
    path("<int:file_id>/start/", StartProcessingView.as_view(), name="processing-start"),
    path("<int:job_id>/errors/", ProcessingErrorsView.as_view(), name="processing-errors"),
    path("<int:job_id>/", ProcessingDetailView.as_view(), name="processing-detail"),
    path("", ProcessingListView.as_view(), name="processing-list"),
]