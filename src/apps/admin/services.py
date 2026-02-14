"""Admin Services - Business Logic for Admin Portal.

Ref: .blueprint/code_sturcture.md §2
Ref: .blueprint/data.md §5 - Must use services, not direct DB updates
Ref: .blueprint/infra.md §8A - Structured logging
"""
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.products.constants import REDIS_KEY_STOCK, STOCK_CACHE_TTL_SECONDS
from apps.products.models import Category, Product, Stock
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
    redis_key = REDIS_KEY_STOCK.format(product_id=product_id_str)

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


# =============================================================================
# Product Management Services for Admin CRUD
# =============================================================================


def create_product_with_inventory(
    name: str,
    price: Decimal,
    category_id: UUID,
    admin_user: "AbstractUser",
    description: str | None = None,
    image_url: str | None = None,
    initial_stock: int = 0,
) -> dict[str, Any]:
    """
    Create a new product with initial inventory.

    Flow:
    1. Validate inputs (price > 0, initial_stock >= 0)
    2. Create Product within transaction
    3. Create Stock record with initial quantity
    4. On commit, set Redis cache
    5. Log structured JSON

    Ref: .blueprint/code_structure.md §2
    Ref: .blueprint/data.md §5 - Must use services
    Ref: .blueprint/infra.md §8A - Structured logging

    Args:
        name: Product name (1-200 chars)
        price: Product price (must be > 0)
        category_id: Category UUID
        admin_user: Admin performing the operation
        description: Optional product description
        image_url: Optional product image URL
        initial_stock: Initial stock quantity (default 0)

    Returns:
        dict: Created product and stock data

    Raises:
        ValueError: If validation fails
        Category.DoesNotExist: If category not found
    """
    from apps.products.models import Category, Product, Stock
    from apps.admin.selectors import get_product_with_realtime_stock

    # Validation
    if not name or not name.strip():
        raise ValueError("Product name is required")
    if len(name) > 200:
        raise ValueError("Product name must be <= 200 characters")
    if price is None or price <= 0:
        raise ValueError("Price must be greater than 0")
    if initial_stock < 0:
        raise ValueError("Initial stock must be >= 0")

    # Get category
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        logger.error(
            "Category not found",
            extra={"extra_data": {"category_id": str(category_id)}},
        )
        raise

    # Create product and stock in transaction
    with transaction.atomic():
        # Create product
        product = Product.objects.create(
            category=category,
            name=name.strip(),
            description=description or "",
            price=price,
            image_url=image_url or "",
            is_active=True,
        )

        # Create stock
        stock = Stock.objects.create(
            product=product,
            quantity=initial_stock,
        )

        # Log product creation (within transaction context)
        logger.info(
            "product_created",
            extra={
                "extra_data": {
                    "product_id": str(product.id),
                    "name": product.name,
                    "price": str(product.price),
                    "category_id": str(product.category_id),
                    "initial_stock": initial_stock,
                    "created_by": str(admin_user.id),
                    "created_by_username": admin_user.username,
                    "timestamp": timezone.now().isoformat(),
                }
            },
        )

    # Update Redis after DB commit
    product_id_str = str(product.id)
    transaction.on_commit(
        lambda: _update_redis_on_create(product_id_str, initial_stock)
    )

    # Get full product data with stock
    result = get_product_with_realtime_stock(product.id)
    if not result:
        raise RuntimeError("Failed to fetch created product")

    return {
        "product": result,
        "stock": {
            "product_id": str(stock.product_id),
            "quantity": stock.quantity,
        },
    }


def _update_redis_on_create(product_id_str: str, initial_stock: int) -> None:
    """Update Redis cache after product creation."""
    redis_key = REDIS_KEY_STOCK.format(product_id=product_id_str)
    cache.set(redis_key, initial_stock, timeout=STOCK_CACHE_TTL_SECONDS)

    logger.debug(
        "redis_cache_set",
        extra={
            "extra_data": {
                "product_id": product_id_str,
                "quantity": initial_stock,
                "redis_key": redis_key,
            }
        },
    )


def update_product(
    product_id: UUID,
    admin_user: "AbstractUser",
    name: str | None = None,
    price: Decimal | None = None,
    description: str | None = None,
    image_url: str | None = None,
    category_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Update product information.

    Only provided fields will be updated. Logs old vs new data comparison.

    Ref: .blueprint/code_structure.md §2
    Ref: .blueprint/infra.md §8A - Structured logging with old/new data

    Args:
        product_id: Product UUID to update
        admin_user: Admin performing the operation
        name: Optional new name
        price: Optional new price
        description: Optional new description
        image_url: Optional new image URL
        category_id: Optional new category UUID

    Returns:
        dict: Updated product data

    Raises:
        Product.DoesNotExist: If product not found
        ValueError: If validation fails
        Category.DoesNotExist: If category not found
    """
    from apps.products.models import Category, Product

    # Get product with lock
    try:
        product = Product.objects.select_for_update().get(id=product_id)
    except Product.DoesNotExist:
        logger.error(
            "Product not found for update",
            extra={"extra_data": {"product_id": str(product_id)}},
        )
        raise

    # Record old values for logging
    old_values = {
        "name": product.name,
        "price": str(product.price),
        "description": product.description,
        "image_url": product.image_url,
        "category_id": str(product.category_id),
    }

    updates = {}
    changes = {}

    # Build updates
    if name is not None:
        if not name.strip():
            raise ValueError("Product name cannot be empty")
        updates["name"] = name.strip()
        if updates["name"] != old_values["name"]:
            changes["name"] = {"old": old_values["name"], "new": updates["name"]}

    if price is not None:
        if price <= Decimal("0"):
            raise ValueError("Price must be greater than 0")
        updates["price"] = price
        if str(price) != old_values["price"]:
            changes["price"] = {"old": old_values["price"], "new": str(price)}

    if description is not None:
        updates["description"] = description
        if description != old_values["description"]:
            changes["description"] = {
                "old": old_values["description"],
                "new": description,
            }

    if image_url is not None:
        updates["image_url"] = image_url
        if image_url != old_values["image_url"]:
            changes["image_url"] = {"old": old_values["image_url"], "new": image_url}

    if category_id is not None:
        try:
            category = Category.objects.get(id=category_id)
            updates["category"] = category
            if str(category_id) != old_values["category_id"]:
                changes["category_id"] = {
                    "old": old_values["category_id"],
                    "new": str(category_id),
                }
        except Category.DoesNotExist:
            logger.error(
                "Category not found for update",
                extra={"extra_data": {"category_id": str(category_id)}},
            )
            raise

    # Apply updates
    if updates:
        for field, value in updates.items():
            setattr(product, field, value)
        product.save()

        # Log the update with changes
        if changes:
            logger.info(
                "product_updated",
                extra={
                    "extra_data": {
                        "product_id": str(product_id),
                        "changes": changes,
                        "updated_by": str(admin_user.id),
                        "updated_by_username": admin_user.username,
                        "timestamp": timezone.now().isoformat(),
                    }
                },
            )

    # Return updated product
    from apps.admin.selectors import get_product_with_realtime_stock
    result = get_product_with_realtime_stock(product.id)
    if not result:
        raise RuntimeError("Failed to fetch updated product")

    return {"product": result}


def delete_product(
    product_id: UUID,
    admin_user: "AbstractUser",
) -> None:
    """
    Soft delete a product by setting is_active to False.

    Also removes Redis cache entry.

    Ref: .blueprint/code_structure.md §2
    Ref: .blueprint/infra.md §8A - Structured logging with status change

    Args:
        product_id: Product UUID to delete
        admin_user: Admin performing the operation

    Returns:
        None

    Raises:
        Product.DoesNotExist: If product not found
    """
    from apps.products.models import Product

    try:
        product = Product.objects.select_for_update().get(id=product_id)
    except Product.DoesNotExist:
        logger.error(
            "Product not found for deletion",
            extra={"extra_data": {"product_id": str(product_id)}},
        )
        raise

    # Record current state
    old_status = product.is_active

    # Soft delete
    product.is_active = False
    product.save()

    # Remove Redis cache
    product_id_str = str(product_id)
    redis_key = REDIS_KEY_STOCK.format(product_id=product_id_str)
    cache_deleted = cache.delete(redis_key)

    # Log the deletion
    logger.info(
        "product_deactivated",
        extra={
            "extra_data": {
                "product_id": product_id_str,
                "name": product.name,
                "previous_is_active": str(old_status),
                "new_is_active": "False",
                "redis_cache_deleted": cache_deleted,
                "deleted_by": str(admin_user.id),
                "deleted_by_username": admin_user.username,
                "timestamp": timezone.now().isoformat(),
            }
        },
    )
