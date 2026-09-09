from django.urls import path

from .views import (
    ProcessingBatchDetailView,
    ProcessingBatchListView,
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
        "batches/<int:batch_id>/",
        ProcessingBatchDetailView.as_view(),
        name="processing-batch-detail",
    ),
    path(
        "batches/",
        ProcessingBatchListView.as_view(),
        name="processing-batch-list",
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