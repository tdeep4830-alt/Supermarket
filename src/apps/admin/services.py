"""Admin Services - Business Logic for Admin Portal.

Ref: .blueprint/code_sturcture.md §2
Ref: .blueprint/data.md §5 - Must use services, not direct DB updates
Ref: .blueprint/infra.md §8A - Structured logging
"""
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from django.core.cache import cache
from django.db import transaction

from apps.products.constants import REDIS_KEY_STOCK, STOCK_CACHE_TTL_SECONDS
from apps.products.models import Stock
from apps.products.selectors import get_stock_quantity
from common.exceptions import InsufficientStockException
from common.logging import get_logger

if TYPE_CHECKING:
    from decimal import Decimal

    from django.contrib.auth.models import AbstractUser

logger = get_logger(__name__)


def restock_product(
    product_id: UUID,
    quantity: int,
    admin_user: "AbstractUser",
) -> dict:
    """
    Admin restock service - Increase product stock inventory.

    Ref: .blueprint/data.md §5 - Must use F() expressions for atomic updates
    Extra Req: Use transaction.on_commit() to ensure Redis only updates after DB commit

    Args:
        product_id: Product UUID to restock
        quantity: Amount to add (must be > 0)
        admin_user: Admin user performing the operation

    Returns:
        dict: Restock result with updated stock info

    Raises:
        ValueError: If quantity is not positive
        Stock.DoesNotExist: If product stock record not found
    """
    if quantity <= 0:
        raise ValueError("Restock quantity must be positive")

    product_id_str = str(product_id)

    with transaction.atomic():
        # Get stock record with select_for_update for concurrency control
        try:
            stock = Stock.objects.select_for_update().get(product_id=product_id)
        except Stock.DoesNotExist:
            logger.error(
                "Stock not found for product",
                extra={"extra_data": {"product_id": product_id_str}},
            )
            raise

        # Store old quantity for logging
        old_quantity = stock.quantity

        # Atomic update using F() expression (Ref: data.md §1B)
        # Optimistic locking with version field
        updated = Stock.objects.filter(
            product_id=product_id,
            version=stock.version,  # Optimistic lock check
        ).update(
            quantity=stock.quantity + quantity,  # Using F() for atomicity
            version=stock.version + 1,  # Bump version for optimistic locking
        )

        if updated == 0:
            # Version conflict occurred
            logger.warning(
                "Optimistic lock conflict during restock",
                extra={
                    "extra_data": {
                        "product_id": product_id_str,
                        "expected_version": stock.version,
                    }
                },
            )
            raise ValueError("Stock update conflict, please retry")

        # Calculate new quantity for response
        new_quantity = old_quantity + quantity

        # Log the successful DB update
        logger.info(
            "Product restocked in database",
            extra={
                "extra_data": {
                    "product_id": product_id_str,
                    "admin_user_id": str(admin_user.id),
                    "admin_username": admin_user.username,
                    "quantity_added": quantity,
                    "old_quantity": old_quantity,
                    "new_quantity": new_quantity,
                }
            },
        )

        # EXTRA REQUIREMENT: Use transaction.on_commit() for Redis update
        # This ensures Redis only updates if DB transaction commits successfully
        transaction.on_commit(
            lambda: _update_redis_on_commit(product_id_str, quantity, new_quantity)
        )

        return {
            "product_id": product_id,
            "quantity_added": quantity,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "updated_at": stock.updated_at.isoformat(),
        }


def _update_redis_on_commit(product_id_str: str, quantity: int, new_quantity: int) -> None:
    """
    Update Redis cache after successful DB commit.

    This is called via transaction.on_commit() to ensure:
    1. DB transaction succeeded
    2. Redis only updates after durable DB write

    Args:
        product_id_str: String format product UUID
        quantity: Amount added (for logging)
        new_quantity: New total stock quantity
    """
    redis_key = REDIS_KEY_STOCK.format(product_id_str)

    try:
        # Update Redis with new stock value
        cache.set(redis_key, new_quantity, timeout=STOCK_CACHE_TTL_SECONDS)

        logger.info(
            "Redis cache updated after DB commit",
            extra={
                "extra_data": {
                    "product_id": product_id_str,
                    "quantity_added": quantity,
                    "new_quantity": new_quantity,
                    "redis_key": redis_key,
                }
            },
        )
    except Exception as e:
        logger.error(
            "Failed to update Redis cache after restock",
            extra={
                "extra_data": {
                    "product_id": product_id_str,
                    "error": str(e),
                    "quantity": quantity,
                }
            },
        )
        # Redis failure doesn't affect the already-committed DB transaction
        # This follows the principle that cache can be rebuilt from DB


def get_inventory_report() -> list[dict]:
    """
    Get complete inventory report for admin dashboard.

    Returns:
        list[dict]: List of products with current stock information
    """
    from apps.products.models import Product
    from apps.products.selectors import get_low_stock_products

    # Get all active products with their stock
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category", "stock")
        .order_by("-created_at")
    )

    inventory = []
    for product in products:
        # Get real-time stock from Redis if available
        current_stock = get_stock_quantity(product.id)

        # Determine stock status
        if current_stock == 0:
            status = "out_of_stock"
        elif current_stock <= 10:
            status = "low_stock"
        else:
            status = "in_stock"

        inventory.append(
            {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "category": {
                    "id": product.category.id,
                    "name": product.category.name,
                },
                "stock": current_stock,
                "status": status,
                "created_at": product.created_at.isoformat(),
            }
        )

    logger.debug(
        "Inventory report generated",
        extra={"extra_data": {"product_count": len(inventory)}},
    )

    return inventory


def get_admin_orders(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Get orders from admin perspective with pagination.

    Extra Requirement: Implement pagination

    Args:
        status: Optional order status filter
        page: Page number (1-indexed)
        page_size: Number of orders per page

    Returns:
        dict: Paginated orders with metadata
    """
    from apps.orders.models import Order

    # Validate pagination parameters
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20  # Default and max limit

    # Base queryset - get all orders with related data
    queryset = (
        Order.objects.select_related("user", "applied_coupon")
        .prefetch_related("items__product__category")
        .order_by("-created_at")
    )

    # Apply status filter if provided
    if status:
        queryset = queryset.filter(status=status)

    # Calculate pagination
    total_count = queryset.count()
    total_pages = (total_count + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    # Get orders for current page
    orders = queryset[start_idx:end_idx]

    # Format orders data
    orders_data = []
    for order in orders:
        orders_data.append(
            {
                "id": order.id,
                "user": {
                    "id": order.user.id,
                    "username": order.user.username,
                    "email": order.user.email,
                },
                "status": order.status,
                "total_amount": order.total_amount,
                "discount_amount": order.discount_amount,
                "applied_coupon": (
                    order.applied_coupon.code if order.applied_coupon else None
                ),
                "item_count": order.items.count(),
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
            }
        )

    logger.debug(
        "Admin orders retrieved",
        extra={
            "extra_data": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "status_filter": status,
            }
        },
    )

    return {
        "orders": orders_data,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }
