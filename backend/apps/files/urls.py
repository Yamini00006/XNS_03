from django.urls import path

from .views import (
    FileAttributeDiscoveryView,
    FileBatchUploadView,
    FileDetailView,
    FileListView,
    FileUploadView,
)

urlpatterns = [
    path(
        "upload/",
        FileUploadView.as_view(),
        name="files-upload",
    ),
    path(
        "upload-batch/",
        FileBatchUploadView.as_view(),
        name="files-upload-batch",
    ),
    path(
        "discover-attributes/",
        FileAttributeDiscoveryView.as_view(),
        name="files-discover-attributes",
    ),
    path(
        "",
        FileListView.as_view(),
        name="files-list",
    ),
    path(
        "<int:file_id>/",
        FileDetailView.as_view(),
        name="files-detail",
    ),
]