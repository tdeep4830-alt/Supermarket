"""Product & Inventory Admin Configuration."""
from django.contrib import admin

from .models import Category, Product, Stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category Admin."""

    list_display = ["name", "slug", "parent", "is_active", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]


class StockInline(admin.TabularInline):
    """Inline Stock editor for Product Admin."""

    model = Stock
    extra = 0
    readonly_fields = ["version"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product Admin."""

    list_display = ["name", "category", "price", "is_active", "get_stock", "created_at"]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "description"]
    list_editable = ["is_active"]
    ordering = ["-created_at"]
    inlines = [StockInline]

    @admin.display(description="Stock")
    def get_stock(self, obj: Product) -> int:
        """Display stock quantity."""
        try:
            return obj.stock.quantity
        except Stock.DoesNotExist:
            return 0


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """
    Stock Admin.

    Note: version is read-only to prevent manual modification.
    Stock changes should go through services.py (Ref: data.md §5).
    """

    list_display = ["product", "quantity", "version", "updated_at"]
    search_fields = ["product__name"]
    readonly_fields = ["version"]
    ordering = ["-updated_at"]
