"""Order & Coupon Admin Configuration."""
from django.contrib import admin

from .models import Coupon, Order, OrderItem, UserCoupon


class OrderItemInline(admin.TabularInline):
    """Inline OrderItem editor for Order Admin."""

    model = OrderItem
    extra = 0
    readonly_fields = ["price_at_purchase", "subtotal"]

    @admin.display(description="Subtotal")
    def subtotal(self, obj: OrderItem) -> str:
        """Display subtotal."""
        return f"${obj.subtotal}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order Admin."""

    list_display = [
        "id",
        "user",
        "status",
        "total_amount",
        "discount_amount",
        "applied_coupon",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "user__username", "payment_id"]
    readonly_fields = ["applied_coupon", "discount_amount", "total_amount"]
    ordering = ["-created_at"]
    inlines = [OrderItemInline]

    def has_add_permission(self, request) -> bool:
        """Disable manual order creation in admin."""
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """OrderItem Admin."""

    list_display = ["order", "product", "quantity", "price_at_purchase", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["order__id", "product__name"]
    readonly_fields = ["price_at_purchase"]
    ordering = ["-created_at"]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Coupon Admin."""

    list_display = [
        "code",
        "discount_type",
        "discount_value",
        "min_purchase_amount",
        "valid_from",
        "valid_until",
        "usage_display",
        "is_active",
    ]
    list_filter = ["discount_type", "is_active", "valid_from", "valid_until"]
    search_fields = ["code"]
    list_editable = ["is_active"]
    readonly_fields = ["used_count"]
    ordering = ["-created_at"]

    @admin.display(description="Usage")
    def usage_display(self, obj: Coupon) -> str:
        """Display usage count / limit."""
        if obj.total_limit == 0:
            return f"{obj.used_count} / ∞"
        return f"{obj.used_count} / {obj.total_limit}"


@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    """UserCoupon Admin."""

    list_display = ["user", "coupon", "used_at", "created_at"]
    list_filter = ["created_at", "used_at"]
    search_fields = ["user__username", "coupon__code"]
    ordering = ["-created_at"]
