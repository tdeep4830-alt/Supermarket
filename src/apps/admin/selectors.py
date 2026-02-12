"""Admin Selectors - Read Operations for Admin Portal.

Ref: .blueprint/code_structure.md §2
Ref: .blueprint/data.md §3 - Cache-Aside Pattern

All read operations follow Cache-Aside pattern:
1. Check Redis cache first
2. If cache miss, query DB and populate cache
"""
from uuid import UUID

from django.core.cache import cache
from django.db.models import QuerySet

from apps.products.constants import REDIS_KEY_STOCK, STOCK_CACHE_TTL_SECONDS
from apps.products.models import Product


# =============================================================================
# Inventory Selectors
# =============================================================================


def get_all_products_with_stock() -> QuerySet[Product]:
    """
    Get all products with their stock information.

    Returns:
        QuerySet[Product]: Products with stock data
    """
    return (
        Product.objects.filter(is_active=True)
        .select_related("category", "stock")
        .order_by("-created_at")
    )


def get_product_with_realtime_stock(product_id: UUID) -> dict | None:
    """
    Get product info with real-time stock from Redis.

    Args:
        product_id: Product UUID

    Returns:
        dict | None: Product with stock info, or None
    """
    try:
        product = (
            Product.objects.select_related("category", "stock")
            .prefetch_related("category__children")
            .get(id=product_id, is_active=True)
        )

        # Get real-time stock from Redis using cache-aside pattern
        redis_key = REDIS_KEY_STOCK.format(product_id=str(product_id))
        cached_stock = cache.get(redis_key)

        if cached_stock is not None:
            current_stock = int(cached_stock)
        elif product.stock:
            # Cache miss - populate cache
            current_stock = product.stock.quantity
            cache.set(redis_key, current_stock, timeout=STOCK_CACHE_TTL_SECONDS)
        else:
            current_stock = 0

        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "image_url": product.image_url,
            "is_active": product.is_active,
            "category": {
                "id": product.category.id,
                "name": product.category.name,
                "slug": product.category.slug,
            },
            "stock": current_stock,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
        }
    except Product.DoesNotExist:
        return None


def get_low_stock_products_count(threshold: int = 10) -> int:
    """
    Count products with low stock.

    Args:
        threshold: Stock threshold (default 10)

    Returns:
        int: Count of low stock products
    """
    return Product.objects.filter(
        is_active=True, stock__quantity__lte=threshold
    ).count()


def get_out_of_stock_products_count() -> int:
    """
    Count products that are out of stock.

    Returns:
        int: Count of out of stock products
    """
    return Product.objects.filter(is_active=True, stock__quantity=0).count()


# =============================================================================
# Order Selectors for Admin
# =============================================================================


def get_recent_orders(limit: int = 10):
    """
    Get recent orders for admin dashboard overview.

    Args:
        limit: Number of orders to retrieve

    Returns:
        QuerySet: Recent orders with related data
    """
    from apps.orders.models import Order

    return (
        Order.objects.select_related("user", "applied_coupon")
        .prefetch_related("items__product")
        .order_by("-created_at")[:limit]
    )


def get_total_revenue():
    """
    Calculate total revenue from all paid orders.

    Returns:
        Decimal: Total revenue
    """
    from apps.orders.models import Order
    from django.db.models import Sum

    result = Order.objects.filter(status="PAID").aggregate(total=Sum("total_amount"))
    return result["total"] or 0


def get_orders_by_status(status: str):
    """
    Get orders filtered by status.

    Args:
        status: Order status to filter

    Returns:
        QuerySet: Filtered orders
    """
    from apps.orders.models import Order

    return Order.objects.filter(status=status).order_by("-created_at")
