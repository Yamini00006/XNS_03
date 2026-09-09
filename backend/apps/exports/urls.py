from django.urls import path

from .views import CSVExportView, JSONExportView, XLSXExportView

urlpatterns = [
    path("csv/", CSVExportView.as_view(), name="exports-csv"),
    path("xlsx/", XLSXExportView.as_view(), name="exports-xlsx"),
    path("json/", JSONExportView.as_view(), name="exports-json"),
]