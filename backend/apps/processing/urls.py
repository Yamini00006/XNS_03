from django.urls import path

from .views import (
    ProcessingBatchStatusView,
    ProcessingDetailView,
    ProcessingErrorsView,
    ProcessingListView,
    StartBatchProcessingView,
    StartProcessingView,
)

urlpatterns = [
    path(
        "batch/start/",
        StartBatchProcessingView.as_view(),
        name="processing-batch-start",
    ),
    path(
        "batch/status/",
        ProcessingBatchStatusView.as_view(),
        name="processing-batch-status",
    ),
    path(
        "<int:file_id>/start/",
        StartProcessingView.as_view(),
        name="processing-start",
    ),
    path(
        "<int:job_id>/errors/",
        ProcessingErrorsView.as_view(),
        name="processing-errors",
    ),
    path(
        "<int:job_id>/",
        ProcessingDetailView.as_view(),
        name="processing-detail",
    ),
    path(
        "",
        ProcessingListView.as_view(),
        name="processing-list",
    ),
]