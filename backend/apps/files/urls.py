from django.urls import path

from .views import FileDetailView, FileListView, FileUploadView

urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="files-upload"),
    path("", FileListView.as_view(), name="files-list"),
    path("<int:file_id>/", FileDetailView.as_view(), name="files-detail"),
]