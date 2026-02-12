"""
Order Serializers.

Ref: .blueprint/code_structure.md §2
Serializers for Order, OrderItem, and Coupon models.
"""
from decimal import Decimal
from uuid import UUID

from rest_framework import serializers

from apps.products.serializers import ProductMinimalSerializer

from .models import Coupon, Order, OrderItem


# =============================================================================
# Input Serializers (Request Validation)
# =============================================================================


class OrderItemInputSerializer(serializers.Serializer):
    """
    Serializer for order item input.

    Used in PlaceOrderSerializer to validate each item in the order.
    """

    product_id = serializers.UUIDField(
        help_text="Product UUID to purchase",
    )
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Quantity to purchase (must be >= 1)",
    )


class PlaceOrderSerializer(serializers.Serializer):
    """
    Serializer for place order request.

    Validates the input and converts to format expected by place_order service.
    """

    items = OrderItemInputSerializer(
        many=True,
        min_length=1,
        help_text="List of items to order",
    )
    coupon_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Optional coupon code to apply",
    )

    def validate_items(self, value: list[dict]) -> list[dict]:
        """Validate items list is not empty."""
        if not value:
            raise serializers.ValidationError("Order must have at least one item")
        return value

    def validate_coupon_code(self, value: str | None) -> str | None:
        """Convert empty string to None."""
        if value == "":
            return None
        return value


# =============================================================================
# Output Serializers (Response)
# =============================================================================


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for Coupon model."""

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "min_purchase_amount",
            "valid_from",
            "valid_until",
        ]


class CouponMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Coupon (used in Order)."""

    class Meta:
        model = Coupon
        fields = ["code", "discount_type", "discount_value"]


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    product = ProductMinimalSerializer(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "price_at_purchase",
            "subtotal",
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model (list view)."""

    applied_coupon = CouponMinimalSerializer(read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_amount",
            "discount_amount",
            "applied_coupon",
            "items_count",
            "created_at",
            "updated_at",
        ]

    def get_items_count(self, obj: Order) -> int:
        """Get total number of items in order."""
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for Order model (detail view with items)."""

    applied_coupon = CouponMinimalSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_amount",
            "discount_amount",
            "applied_coupon",
            "payment_id",
            "items",
            "subtotal",
            "created_at",
            "updated_at",
        ]

    def get_subtotal(self, obj: Order) -> Decimal:
        """Calculate subtotal (before discount)."""
        return obj.total_amount + obj.discount_amount


class PlaceOrderResponseSerializer(serializers.Serializer):
    """Serializer for place order response."""

    order = OrderDetailSerializer()
    message = serializers.CharField()
