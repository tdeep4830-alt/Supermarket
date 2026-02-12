"""Admin API Serializers.

Ref: .blueprint/code_sturcture.md §2

All API request/response serialization for admin endpoints.
"""
from decimal import Decimal
from typing import Any
from uuid import UUID

from rest_framework import serializers


class RestockRequestSerializer(serializers.Serializer):
    """Serializer for restock API request."""

    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Quantity to add to stock",
    )


class RestockResponseSerializer(serializers.Serializer):
    """Serializer for restock API response."""

    product_id = serializers.UUIDField()
    quantity_added = serializers.IntegerField()
    old_quantity = serializers.IntegerField()
    new_quantity = serializers.IntegerField()
    updated_at = serializers.DateTimeField()


class InventoryItemSerializer(serializers.Serializer):
    """Serializer for inventory items in list view."""

    id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.SerializerMethodField()
    stock = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_category(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Serialize category field."""
        return {
            "id": obj["category"]["id"],
            "name": obj["category"]["name"],
        }


class InventoryListResponseSerializer(serializers.Serializer):
    """Serializer for inventory list response."""

    inventory = serializers.ListField(child=InventoryItemSerializer())


class AdminOrderItemSerializer(serializers.Serializer):
    """Serializer for order items in admin order list."""

    id = serializers.UUIDField()
    user = serializers.SerializerMethodField()
    status = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    applied_coupon = serializers.CharField(allow_null=True)
    item_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_user(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Serialize user field."""
        return {
            "id": obj["user"]["id"],
            "username": obj["user"]["username"],
            "email": obj["user"]["email"],
        }


class PaginationMetadataSerializer(serializers.Serializer):
    """Serializer for pagination metadata."""

    current_page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)
    total_count = serializers.IntegerField(min_value=0)
    total_pages = serializers.IntegerField(min_value=1)
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()


class AdminOrdersListResponseSerializer(serializers.Serializer):
    """Serializer for admin orders list response."""

    orders = serializers.ListField(child=AdminOrderItemSerializer())
    pagination = PaginationMetadataSerializer()


class AdminDashboardStatsSerializer(serializers.Serializer):
    """Serializer for admin dashboard statistics."""

    total_products = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
