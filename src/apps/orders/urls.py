"""
Order URL Configuration.

Ref: .blueprint/code_structure.md §1
API endpoints for orders.
"""
from django.urls import path

from .views import OrderDetailView, OrderListCreateView

app_name = "orders"

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order-list-create"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
]
