"""Admin Portal URL Configuration.

All /api/admin/* endpoints require IsAdminUser permission.
"""
from django.urls import path

from .views import (
    AdminInventoryListView,
    AdminInventoryRestockView,
    AdminOrdersListView,
)

app_name = "admin"

urlpatterns = [
    # Inventory Management
    path(
        "inventory/",
        AdminInventoryListView.as_view(),
        name="inventory-list",
    ),
    path(
        "inventory/<uuid:product_id>/restock/",
        AdminInventoryRestockView.as_view(),
        name="inventory-restock",
    ),
    # Order Management
    path(
        "orders/",
        AdminOrdersListView.as_view(),
        name="orders-list",
    ),
]
