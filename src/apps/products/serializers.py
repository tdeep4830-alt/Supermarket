"""
Product Serializers.

Ref: .blueprint/code_structure.md §2
Serializers for Product, Category, and Stock models.
"""
from rest_framework import serializers

from .models import Category, Product, Stock
from .selectors import get_stock_quantity


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "is_active",
        ]
        read_only_fields = ["id"]


class CategoryNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for Category (minimal fields)."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model (list view)."""

    category = CategoryNestedSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image_url",
            "is_active",
            "category",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProductWithStockSerializer(serializers.ModelSerializer):
    """Serializer for Product with stock information."""

    category = CategoryNestedSerializer(read_only=True)
    stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image_url",
            "is_active",
            "category",
            "stock",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_stock(self, obj: Product) -> int:
        """Get stock quantity using selector (Cache-Aside pattern)."""
        return get_stock_quantity(obj.id)


class ProductMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Product (used in OrderItem)."""

    class Meta:
        model = Product
        fields = ["id", "name", "price", "image_url"]
