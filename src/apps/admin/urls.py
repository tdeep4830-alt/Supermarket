"""Admin Portal URL Configuration.

All /api/admin/* endpoints require IsAdminUser permission.
"""
from django.urls import path

from .views import (
    AdminCategoryListView,
    AdminInventoryListView,
    AdminInventoryRestockView,
    AdminOrdersListView,
    AdminProductCreateView,
    AdminProductUpdateView,
)

app_name = "admin"

urlpatterns = [
    # Categories
    path(
        "categories/",
        AdminCategoryListView.as_view(),
        name="category-list",
    ),
    # Inventory Management
    path(
        "inventory/",
        AdminInventoryListView.as_view(),
        name="inventory-list",
    ),
    path(
        "products/",
        AdminProductCreateView.as_view(),
        name="product-create",
    ),
    path(
        "products/<uuid:product_id>/",
        AdminProductUpdateView.as_view(),
        name="product-update-delete",
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
