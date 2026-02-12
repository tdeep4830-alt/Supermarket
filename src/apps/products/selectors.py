"""
Product & Inventory Selectors (Read Operations).

Ref: .blueprint/code_sturcture.md §2
Ref: .blueprint/data.md §3 - Cache-Aside Pattern

所有讀取操作：先查 Redis，若無則查 DB 並回填 Redis。
"""
from uuid import UUID

from django.core.cache import cache
from django.db.models import QuerySet

from .constants import REDIS_KEY_STOCK, STOCK_CACHE_TTL_SECONDS
from .models import Category, Product, Stock


# =============================================================================
# Product Selectors
# =============================================================================


def get_active_products() -> QuerySet[Product]:
    """
    取得所有上架商品.

    Returns:
        QuerySet[Product]: 上架商品列表
    """
    return Product.objects.filter(
        is_active=True,
    ).select_related("category")


def get_products_by_category(category_id: UUID) -> QuerySet[Product]:
    """
    依分類取得商品.

    Args:
        category_id: 分類 UUID

    Returns:
        QuerySet[Product]: 該分類下的上架商品
    """
    return Product.objects.filter(
        category_id=category_id,
        is_active=True,
    ).select_related("category")


def get_product_by_id(product_id: UUID) -> Product | None:
    """
    依 ID 取得商品.

    Args:
        product_id: 商品 UUID

    Returns:
        Product | None: 商品實例或 None
    """
    try:
        return Product.objects.select_related("category").get(id=product_id)
    except Product.DoesNotExist:
        return None


def get_product_with_stock(product_id: UUID) -> dict | None:
    """
    取得商品及其庫存資訊.

    Args:
        product_id: 商品 UUID

    Returns:
        dict | None: 商品資訊含庫存，或 None
    """
    try:
        product = Product.objects.select_related("category", "stock").get(id=product_id)
        stock_quantity = get_stock_quantity(product_id)

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
            },
            "stock": stock_quantity,
        }
    except Product.DoesNotExist:
        return None


# =============================================================================
# Stock Selectors (Ref: data.md §3 - Cache-Aside Pattern)
# =============================================================================


def get_stock_quantity(product_id: UUID) -> int:
    """
    取得商品庫存數量（Cache-Aside Pattern）.

    Ref: data.md §3
    1. 先查 Redis
    2. 若無則查 DB 並回填 Redis

    Args:
        product_id: 商品 UUID

    Returns:
        int: 庫存數量（不存在返回 0）
    """
    redis_key = REDIS_KEY_STOCK.format(product_id=str(product_id))

    # Step 1: 先查 Redis
    cached_quantity = cache.get(redis_key)
    if cached_quantity is not None:
        return int(cached_quantity)

    # Step 2: 查 DB 並回填 Redis
    try:
        stock = Stock.objects.get(product_id=product_id)
        cache.set(redis_key, stock.quantity, timeout=STOCK_CACHE_TTL_SECONDS)
        return stock.quantity
    except Stock.DoesNotExist:
        return 0


def get_stock_by_product(product_id: UUID) -> Stock | None:
    """
    取得商品庫存 Model 實例.

    Args:
        product_id: 商品 UUID

    Returns:
        Stock | None: 庫存實例或 None
    """
    try:
        return Stock.objects.select_related("product").get(product_id=product_id)
    except Stock.DoesNotExist:
        return None


def get_low_stock_products(threshold: int = 10) -> QuerySet[Stock]:
    """
    取得低庫存商品.

    Args:
        threshold: 庫存警戒線（預設 10）

    Returns:
        QuerySet[Stock]: 低庫存商品列表
    """
    return Stock.objects.filter(
        quantity__lte=threshold,
        product__is_active=True,
    ).select_related("product")


# =============================================================================
# Category Selectors
# =============================================================================


def get_active_categories() -> QuerySet[Category]:
    """
    取得所有啟用的分類.

    Returns:
        QuerySet[Category]: 啟用的分類列表
    """
    return Category.objects.filter(is_active=True)


def get_root_categories() -> QuerySet[Category]:
    """
    取得所有根分類（無父分類）.

    Returns:
        QuerySet[Category]: 根分類列表
    """
    return Category.objects.filter(
        parent__isnull=True,
        is_active=True,
    )


def get_category_with_children(category_id: UUID) -> dict | None:
    """
    取得分類及其子分類.

    Args:
        category_id: 分類 UUID

    Returns:
        dict | None: 分類資訊含子分類
    """
    try:
        category = Category.objects.prefetch_related("children").get(id=category_id)
        return {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "children": [
                {"id": child.id, "name": child.name, "slug": child.slug}
                for child in category.children.filter(is_active=True)
            ],
        }
    except Category.DoesNotExist:
        return None
