from django.urls import path

from .views import CustomerDetailView, CustomerListView, CustomerRawView

urlpatterns = [
    path("", CustomerListView.as_view(), name="data-list"),
    path("<int:customer_id>/raw/", CustomerRawView.as_view(), name="data-raw"),
    path("<int:customer_id>/", CustomerDetailView.as_view(), name="data-detail"),
]