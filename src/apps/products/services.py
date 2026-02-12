"""
Product & Inventory Services (Write Operations).

Ref: .blueprint/data.md §1B, §2A, §2D, §3, §5
Ref: .blueprint/code_sturcture.md §2

搶購核心邏輯：
1. Redis DECRBY 快速扣減（攔截超賣）
2. PostgreSQL F() + version 樂觀鎖（數據一致性）
3. 失敗時 Redis INCRBY 回滾

Concurrency Control Layers:
Layer 1: Redis DECRBY - 快速攔截超賣請求
Layer 2: PostgreSQL select_for_update - 悲觀鎖，確保同一時間只有一個事務修改
Layer 3: PostgreSQL F() + version - 樂觀鎖，最終一致性檢查
Layer 4: Retry mechanism - 樂觀鎖衝突時自動重試

IMPORTANT: 禁止在 View 層直接修改 Stock.quantity
"""
import time
from typing import TYPE_CHECKING
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.db.models import F

from common.exceptions import (
    InsufficientStockException,
    RateLimitExceededException,
    StockUpdateConflictException,
)
from common.logging import get_logger

from .constants import (
    RATE_LIMIT_ORDER_SECONDS,
    REDIS_KEY_RATE_LIMIT_ORDER,
    REDIS_KEY_STOCK,
    STOCK_CACHE_TTL_SECONDS,
)
from .models import Stock

if TYPE_CHECKING:
    from .models import Product

logger = get_logger(__name__)

# Optimistic lock retry configuration
OPTIMISTIC_LOCK_MAX_RETRIES = 3
OPTIMISTIC_LOCK_RETRY_DELAY_MS = 10  # Base delay in milliseconds


# =============================================================================
# Stock Services (Ref: data.md §1B, §2A, §3, §5)
# =============================================================================


def decrease_stock(
    product_id: UUID,
    quantity: int,
    *,
    use_redis: bool = True,
    max_retries: int = OPTIMISTIC_LOCK_MAX_RETRIES,
) -> bool:
    """
    扣減商品庫存（搶購核心）.

    Ref: data.md §1B, §2A, §3, §5

    流程：
    1. Redis DECRBY 快速扣減（若啟用）
    2. PostgreSQL F() + version 樂觀鎖扣減（含重試機制）
    3. 若 DB 失敗，Redis INCRBY 回滾

    Concurrency Control:
    - Layer 1 (Redis): DECRBY 原子操作快速攔截超賣
    - Layer 2 (PostgreSQL): select_for_update 悲觀鎖
    - Layer 3 (PostgreSQL): F() + version 樂觀鎖
    - Layer 4 (Retry): 樂觀鎖衝突時指數退避重試

    Args:
        product_id: 商品 UUID
        quantity: 扣減數量（必須 > 0）
        use_redis: 是否使用 Redis 快取層（預設 True）
        max_retries: 樂觀鎖衝突最大重試次數（預設 3）

    Returns:
        bool: 扣減成功返回 True

    Raises:
        InsufficientStockException: 庫存不足
        StockUpdateConflictException: 樂觀鎖衝突（重試耗盡後）
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    redis_key = REDIS_KEY_STOCK.format(product_id=str(product_id))
    redis_decremented = False

    try:
        # Step 1: Redis 快速扣減 (Ref: data.md §2A - DECRBY)
        if use_redis:
            # 確保 Redis 有庫存快照
            _ensure_stock_in_redis(product_id)

            # DECRBY 原子扣減
            new_quantity = cache.decr(redis_key, quantity)

            if new_quantity < 0:
                # 庫存不足，立即回滾 Redis
                cache.incr(redis_key, quantity)
                logger.warning(
                    "Stock insufficient in Redis",
                    extra={"extra_data": {
                        "product_id": str(product_id),
                        "requested": quantity,
                    }},
                )
                raise InsufficientStockException(
                    extra={"product_id": str(product_id), "requested": quantity}
                )

            redis_decremented = True

        # Step 2: PostgreSQL F() + version 樂觀鎖 (Ref: data.md §1B)
        # 使用重試機制處理樂觀鎖衝突
        last_exception: StockUpdateConflictException | None = None

        for attempt in range(max_retries):
            try:
                success = _decrease_stock_db(product_id, quantity)
                if success:
                    logger.info(
                        "Stock decreased successfully",
                        extra={"extra_data": {
                            "product_id": str(product_id),
                            "quantity": quantity,
                            "attempt": attempt + 1,
                        }},
                    )
                    return True
            except StockUpdateConflictException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # 指數退避重試 (exponential backoff)
                    delay = OPTIMISTIC_LOCK_RETRY_DELAY_MS * (2 ** attempt) / 1000
                    logger.warning(
                        "Optimistic lock conflict, retrying",
                        extra={"extra_data": {
                            "product_id": str(product_id),
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay_ms": delay * 1000,
                        }},
                    )
                    time.sleep(delay)
                continue
            except InsufficientStockException:
                # 庫存不足不重試，直接拋出
                raise

        # 重試耗盡，拋出最後的異常
        if last_exception:
            logger.error(
                "Optimistic lock conflict - max retries exceeded",
                extra={"extra_data": {
                    "product_id": str(product_id),
                    "max_retries": max_retries,
                }},
            )
            raise last_exception

        # 不應到達此處
        raise StockUpdateConflictException(
            extra={"product_id": str(product_id), "reason": "unknown"}
        )

    except (InsufficientStockException, StockUpdateConflictException):
        # Step 3: 回滾 Redis (Ref: data.md §3 - 一致性)
        if redis_decremented:
            cache.incr(redis_key, quantity)
            logger.info(
                "Redis stock rolled back",
                extra={"extra_data": {"product_id": str(product_id)}},
            )
        raise

    except Stock.DoesNotExist:
        if redis_decremented:
            cache.incr(redis_key, quantity)
        raise InsufficientStockException(
            message="Product stock not found",
            extra={"product_id": str(product_id)},
        )


def _decrease_stock_db(product_id: UUID, quantity: int) -> bool:
    """
    PostgreSQL 庫存扣減（內部函數）.

    使用雙重鎖定策略：
    1. select_for_update (悲觀鎖) - 防止並發修改
    2. F() + version (樂觀鎖) - 最終一致性檢查

    Args:
        product_id: 商品 UUID
        quantity: 扣減數量

    Returns:
        bool: 扣減成功返回 True

    Raises:
        InsufficientStockException: 庫存不足
        StockUpdateConflictException: 版本衝突
    """
    with transaction.atomic():
        # 悲觀鎖：獲取行鎖
        stock = Stock.objects.select_for_update().get(product_id=product_id)
        current_version = stock.version

        # 樂觀鎖：F() 表達式原子更新 + version 檢查
        updated = Stock.objects.filter(
            product_id=product_id,
            quantity__gte=quantity,
            version=current_version,
        ).update(
            quantity=F("quantity") - quantity,
            version=F("version") + 1,
        )

        if updated == 0:
            # 判斷失敗原因：庫存不足 or 版本衝突
            stock.refresh_from_db()
            if stock.quantity < quantity:
                raise InsufficientStockException(
                    extra={
                        "product_id": str(product_id),
                        "available": stock.quantity,
                        "requested": quantity,
                    }
                )
            else:
                # 版本衝突（另一個事務已修改）
                raise StockUpdateConflictException(
                    extra={
                        "product_id": str(product_id),
                        "expected_version": current_version,
                        "current_version": stock.version,
                    }
                )

        return True


def restore_stock(
    product_id: UUID,
    quantity: int,
    *,
    use_redis: bool = True,
) -> bool:
    """
    恢復商品庫存（取消訂單/退款用）.

    Ref: data.md §1B

    Args:
        product_id: 商品 UUID
        quantity: 恢復數量（必須 > 0）
        use_redis: 是否同步更新 Redis

    Returns:
        bool: 恢復成功返回 True
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    with transaction.atomic():
        updated = Stock.objects.filter(
            product_id=product_id,
        ).update(
            quantity=F("quantity") + quantity,
            version=F("version") + 1,
        )

        if updated == 0:
            raise Stock.DoesNotExist(f"Stock not found for product {product_id}")

    # 同步 Redis
    if use_redis:
        redis_key = REDIS_KEY_STOCK.format(product_id=str(product_id))
        try:
            cache.incr(redis_key, quantity)
        except ValueError:
            # Key 不存在，重新同步
            sync_stock_to_redis(product_id)

    logger.info(
        "Stock restored successfully",
        extra={"extra_data": {
            "product_id": str(product_id),
            "quantity": quantity,
        }},
    )
    return True


def sync_stock_to_redis(product_id: UUID) -> int:
    """
    同步 DB 庫存到 Redis.

    Ref: data.md §2A, §3

    Args:
        product_id: 商品 UUID

    Returns:
        int: 當前庫存數量
    """
    try:
        stock = Stock.objects.get(product_id=product_id)
        redis_key = REDIS_KEY_STOCK.format(product_id=str(product_id))
        cache.set(redis_key, stock.quantity, timeout=STOCK_CACHE_TTL_SECONDS)

        logger.debug(
            "Stock synced to Redis",
            extra={"extra_data": {
                "product_id": str(product_id),
                "quantity": stock.quantity,
            }},
        )
        return stock.quantity

    except Stock.DoesNotExist:
        logger.warning(
            "Stock not found for sync",
            extra={"extra_data": {"product_id": str(product_id)}},
        )
        return 0


def _ensure_stock_in_redis(product_id: UUID) -> None:
    """
    確保 Redis 有庫存快照（Cache-Aside Pattern）.

    Ref: data.md §3
    """
    redis_key = REDIS_KEY_STOCK.format(product_id=str(product_id))
    if cache.get(redis_key) is None:
        sync_stock_to_redis(product_id)


# =============================================================================
# Rate Limiting Services (Ref: data.md §2D)
# =============================================================================


def check_order_rate_limit(user_id: int | str) -> bool:
    """
    檢查用戶下單頻率限制.

    Ref: data.md §2D
    限制同一用戶在 1 秒內只能提交一次訂單，防止刷單。

    Args:
        user_id: 用戶 ID

    Returns:
        bool: 未超限返回 True

    Raises:
        RateLimitExceededException: 超過限制
    """
    redis_key = REDIS_KEY_RATE_LIMIT_ORDER.format(user_id=str(user_id))

    # 使用 add() 原子操作：若 key 已存在則返回 False
    is_allowed = cache.add(redis_key, 1, timeout=RATE_LIMIT_ORDER_SECONDS)

    if not is_allowed:
        logger.warning(
            "Order rate limit exceeded",
            extra={"extra_data": {"user_id": str(user_id)}},
        )
        raise RateLimitExceededException(
            extra={"user_id": str(user_id)}
        )

    return True


# =============================================================================
# Batch Operations
# =============================================================================


def bulk_sync_stock_to_redis(product_ids: list[UUID] | None = None) -> int:
    """
    批量同步庫存到 Redis.

    Args:
        product_ids: 指定商品列表，None 表示全部

    Returns:
        int: 同步數量
    """
    if product_ids:
        stocks = Stock.objects.filter(product_id__in=product_ids)
    else:
        stocks = Stock.objects.all()

    count = 0
    for stock in stocks.iterator():
        redis_key = REDIS_KEY_STOCK.format(product_id=str(stock.product_id))
        cache.set(redis_key, stock.quantity, timeout=STOCK_CACHE_TTL_SECONDS)
        count += 1

    logger.info(
        "Bulk stock sync completed",
        extra={"extra_data": {"count": count}},
    )
    return count
