"""
Order & Coupon Services (Write Operations).

Ref: .blueprint/data.md §1C, §1E, §2E, §5
Ref: .blueprint/code_sturcture.md §2

下單核心邏輯：
1. 限流檢查
2. 優惠碼校驗
3. transaction.atomic 內：扣庫存 + 創建訂單 + 應用優惠碼
4. 失敗全部回滾

IMPORTANT:
- 優惠碼校驗邏輯必須放在 services.py (data.md §1E)
- used_count 必須用 F() 更新 (data.md §1E)
- 創建訂單 + 扣庫存必須在 transaction.atomic 中 (data.md §5)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.products.models import Product
from apps.products.services import (
    check_order_rate_limit,
    decrease_stock,
    restore_stock,
)
from common.exceptions import (
    CouponAlreadyUsedException,
    CouponExpiredException,
    CouponNotFoundException,
    CouponQuotaExceededException,
    InvalidOrderStatusException,
    MinimumPurchaseNotMetException,
    OrderNotFoundException,
)
from common.logging import get_logger

from .constants import (
    COUPON_QUOTA_CACHE_TTL_SECONDS,
    REDIS_KEY_COUPON_QUOTA,
    STATUSES_REQUIRING_STOCK_RESTORE,
    VALID_STATUS_TRANSITIONS,
)
from .models import Coupon, Order, OrderItem, UserCoupon

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()
logger = get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class OrderItemInput:
    """Input data for order item."""

    product_id: UUID
    quantity: int


@dataclass
class PlaceOrderResult:
    """Result of place_order service."""

    order: Order
    items: list[OrderItem]
    discount_amount: Decimal


# =============================================================================
# Order Services (Ref: data.md §1C, §5)
# =============================================================================


def place_order(
    user: "AbstractUser",
    items: list[OrderItemInput],
    coupon_code: str | None = None,
) -> PlaceOrderResult:
    """
    下單服務（整合搶購 + 優惠碼）.

    Ref: data.md §5
    創建訂單 + 扣減庫存必須包裝在 transaction.atomic 事務中。

    流程：
    1. 限流檢查 (data.md §2D)
    2. 優惠碼校驗 (data.md §1E)
    3. transaction.atomic:
       - 扣減庫存（按 product_id 排序，避免死鎖）
       - 計算總金額與折扣
       - 創建 Order + OrderItems
       - 應用優惠碼（更新 used_count + UserCoupon）
    4. 失敗則全部回滾

    Concurrency Control (防止超賣):
    - 按 product_id 排序獲取鎖，避免死鎖 (Deadlock Prevention)
    - decrease_stock 內部使用 select_for_update 悲觀鎖
    - decrease_stock 內部使用 F() + version 樂觀鎖雙重保護
    - Redis DECRBY 作為第一層快速攔截

    Args:
        user: 下單用戶
        items: 訂單項目列表
        coupon_code: 優惠碼（可選）

    Returns:
        PlaceOrderResult: 訂單結果

    Raises:
        RateLimitExceededException: 超過下單頻率限制
        InsufficientStockException: 庫存不足
        CouponNotFoundException: 優惠碼不存在
        CouponExpiredException: 優惠碼已過期
        CouponAlreadyUsedException: 用戶已使用該優惠碼
        MinimumPurchaseNotMetException: 未達最低消費
    """
    if not items:
        raise ValueError("Order must have at least one item")

    # Step 1: 限流檢查 (Ref: data.md §2D)
    check_order_rate_limit(user.id)

    # Step 2: 預先校驗優惠碼（在事務外，避免長時間鎖定）
    coupon = None
    if coupon_code:
        coupon = validate_coupon(coupon_code, user)

    # Step 3: 事務處理 (Ref: data.md §5)
    with transaction.atomic():
        # 3.1 獲取商品資訊並扣減庫存
        # IMPORTANT: 按 product_id 排序，確保一致的鎖獲取順序，避免死鎖
        sorted_items = sorted(items, key=lambda x: str(x.product_id))

        order_items_data = []
        subtotal = Decimal("0.00")

        for item in sorted_items:
            # 獲取商品資訊（無需 select_for_update，因為 decrease_stock 會處理 Stock 鎖）
            product = Product.objects.get(
                id=item.product_id,
                is_active=True,
            )

            # 扣減庫存 (調用 products.services)
            # decrease_stock 內部已實作:
            # - select_for_update (悲觀鎖)
            # - F() + version (樂觀鎖)
            # - Redis DECRBY (快速攔截)
            decrease_stock(product.id, item.quantity)

            item_subtotal = product.price * item.quantity
            subtotal += item_subtotal

            order_items_data.append({
                "product": product,
                "quantity": item.quantity,
                "price_at_purchase": product.price,
            })

        # 3.2 計算折扣
        discount_amount = Decimal("0.00")
        if coupon:
            discount_amount = calculate_discount(coupon, subtotal)

        # 3.3 計算最終金額
        total_amount = max(subtotal - discount_amount, Decimal("0.00"))

        # 3.4 創建訂單
        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_amount=total_amount,
            applied_coupon=coupon,
            discount_amount=discount_amount,
        )

        # 3.5 創建訂單項目
        created_items = []
        for item_data in order_items_data:
            order_item = OrderItem.objects.create(
                order=order,
                product=item_data["product"],
                quantity=item_data["quantity"],
                price_at_purchase=item_data["price_at_purchase"],
            )
            created_items.append(order_item)

        # 3.6 應用優惠碼（更新使用次數）
        if coupon:
            _apply_coupon(coupon, user)

    logger.info(
        "Order placed successfully",
        extra={"extra_data": {
            "order_id": str(order.id),
            "user_id": str(user.id),
            "total_amount": str(total_amount),
            "discount_amount": str(discount_amount),
        }},
    )

    return PlaceOrderResult(
        order=order,
        items=created_items,
        discount_amount=discount_amount,
    )


def cancel_order(order_id: UUID) -> Order:
    """
    取消訂單.

    Ref: data.md §1C
    - 只有 PENDING 狀態可取消
    - 需恢復庫存

    Args:
        order_id: 訂單 UUID

    Returns:
        Order: 更新後的訂單

    Raises:
        OrderNotFoundException: 訂單不存在
        InvalidOrderStatusException: 不允許的狀態轉換
    """
    return update_order_status(order_id, Order.Status.CANCELLED)


def update_order_status(order_id: UUID, new_status: str) -> Order:
    """
    更新訂單狀態.

    Ref: data.md §1C

    Args:
        order_id: 訂單 UUID
        new_status: 目標狀態

    Returns:
        Order: 更新後的訂單

    Raises:
        OrderNotFoundException: 訂單不存在
        InvalidOrderStatusException: 不允許的狀態轉換
    """
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            raise OrderNotFoundException(extra={"order_id": str(order_id)})

        # 檢查狀態轉換是否允許
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(order.status, [])
        if new_status not in allowed_transitions:
            raise InvalidOrderStatusException(
                message=f"Cannot transition from {order.status} to {new_status}",
                extra={
                    "order_id": str(order_id),
                    "current_status": order.status,
                    "target_status": new_status,
                },
            )

        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        # 如果需要恢復庫存（取消或退款）
        if new_status in STATUSES_REQUIRING_STOCK_RESTORE:
            _restore_order_stock(order)

    logger.info(
        "Order status updated",
        extra={"extra_data": {
            "order_id": str(order_id),
            "old_status": old_status,
            "new_status": new_status,
        }},
    )

    return order


def _restore_order_stock(order: Order) -> None:
    """
    恢復訂單的庫存.

    Args:
        order: 訂單實例
    """
    for item in order.items.all():
        restore_stock(item.product_id, item.quantity)

    logger.info(
        "Order stock restored",
        extra={"extra_data": {"order_id": str(order.id)}},
    )


# =============================================================================
# Coupon Services (Ref: data.md §1E, §2E)
# =============================================================================


def validate_coupon(coupon_code: str, user: "AbstractUser") -> Coupon:
    """
    校驗優惠碼.

    Ref: data.md §1E
    優惠碼校驗邏輯必須放在 services.py。

    檢查項目：
    1. 優惠碼是否存在
    2. 是否啟用 (is_active)
    3. 是否在有效期內
    4. 是否超過使用次數限制
    5. 用戶是否已使用過

    Args:
        coupon_code: 優惠碼
        user: 用戶

    Returns:
        Coupon: 驗證通過的優惠碼

    Raises:
        CouponNotFoundException: 優惠碼不存在
        CouponExpiredException: 優惠碼已過期或未啟用
        CouponQuotaExceededException: 超過使用次數限制
        CouponAlreadyUsedException: 用戶已使用過
    """
    # 1. 查詢優惠碼
    try:
        coupon = Coupon.objects.get(code=coupon_code)
    except Coupon.DoesNotExist:
        raise CouponNotFoundException(extra={"code": coupon_code})

    # 2. 檢查是否啟用
    if not coupon.is_active:
        raise CouponExpiredException(
            message="This coupon is not active",
            extra={"code": coupon_code},
        )

    # 3. 檢查有效期
    now = timezone.now()
    if now < coupon.valid_from:
        raise CouponExpiredException(
            message="This coupon is not yet valid",
            extra={"code": coupon_code, "valid_from": str(coupon.valid_from)},
        )
    if now > coupon.valid_until:
        raise CouponExpiredException(
            message="This coupon has expired",
            extra={"code": coupon_code, "valid_until": str(coupon.valid_until)},
        )

    # 4. 檢查使用次數（Redis 快速攔截 + DB 雙重檢查）
    if coupon.total_limit > 0:
        # Redis 快速檢查 (Ref: data.md §2E)
        redis_key = REDIS_KEY_COUPON_QUOTA.format(coupon_code=coupon_code)
        cached_remaining = cache.get(redis_key)

        if cached_remaining is not None and int(cached_remaining) <= 0:
            raise CouponQuotaExceededException(extra={"code": coupon_code})

        # DB 雙重檢查
        if coupon.used_count >= coupon.total_limit:
            # 同步 Redis
            cache.set(redis_key, 0, timeout=COUPON_QUOTA_CACHE_TTL_SECONDS)
            raise CouponQuotaExceededException(extra={"code": coupon_code})

    # 5. 檢查用戶是否已使用
    if UserCoupon.objects.filter(user=user, coupon=coupon, used_at__isnull=False).exists():
        raise CouponAlreadyUsedException(extra={"code": coupon_code})

    return coupon


def calculate_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
    """
    計算折扣金額.

    Ref: data.md §1E

    Args:
        coupon: 優惠碼
        subtotal: 訂單小計（折扣前）

    Returns:
        Decimal: 折扣金額

    Raises:
        MinimumPurchaseNotMetException: 未達最低消費
    """
    # 檢查最低消費
    if subtotal < coupon.min_purchase_amount:
        raise MinimumPurchaseNotMetException(
            extra={
                "code": coupon.code,
                "min_purchase": str(coupon.min_purchase_amount),
                "subtotal": str(subtotal),
            },
        )

    # 計算折扣
    if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
        # 百分比折扣
        discount = subtotal * (coupon.discount_value / Decimal("100"))
    else:
        # 固定金額折扣
        discount = coupon.discount_value

    # 折扣不能超過訂單金額
    return min(discount, subtotal)


def _apply_coupon(coupon: Coupon, user: "AbstractUser") -> None:
    """
    應用優惠碼（內部函數）.

    Ref: data.md §1E
    - 更新 used_count（必須用 F() 表達式）
    - 創建 UserCoupon 記錄

    Args:
        coupon: 優惠碼
        user: 用戶
    """
    # 更新使用次數 (F() 原子操作)
    Coupon.objects.filter(id=coupon.id).update(
        used_count=F("used_count") + 1,
    )

    # 更新 Redis 快取
    if coupon.total_limit > 0:
        redis_key = REDIS_KEY_COUPON_QUOTA.format(coupon_code=coupon.code)
        try:
            cache.decr(redis_key)
        except ValueError:
            # Key 不存在，計算並設置
            remaining = coupon.total_limit - coupon.used_count - 1
            cache.set(redis_key, max(remaining, 0), timeout=COUPON_QUOTA_CACHE_TTL_SECONDS)

    # 創建/更新 UserCoupon 記錄
    UserCoupon.objects.update_or_create(
        user=user,
        coupon=coupon,
        defaults={"used_at": timezone.now()},
    )

    logger.info(
        "Coupon applied",
        extra={"extra_data": {
            "coupon_code": coupon.code,
            "user_id": str(user.id),
        }},
    )


def sync_coupon_quota_to_redis(coupon_code: str) -> int:
    """
    同步優惠碼配額到 Redis.

    Ref: data.md §2E

    Args:
        coupon_code: 優惠碼

    Returns:
        int: 剩餘配額
    """
    try:
        coupon = Coupon.objects.get(code=coupon_code)
        if coupon.total_limit == 0:
            return -1  # 無限制

        remaining = coupon.total_limit - coupon.used_count
        redis_key = REDIS_KEY_COUPON_QUOTA.format(coupon_code=coupon_code)
        cache.set(redis_key, remaining, timeout=COUPON_QUOTA_CACHE_TTL_SECONDS)
        return remaining

    except Coupon.DoesNotExist:
        return 0


# =============================================================================
# Payment Services
# =============================================================================


def mark_order_paid(order_id: UUID, payment_id: str) -> Order:
    """
    標記訂單為已支付.

    Args:
        order_id: 訂單 UUID
        payment_id: 支付憑證 ID

    Returns:
        Order: 更新後的訂單
    """
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            raise OrderNotFoundException(extra={"order_id": str(order_id)})

        if order.status != Order.Status.PENDING:
            raise InvalidOrderStatusException(
                message="Only pending orders can be marked as paid",
                extra={"order_id": str(order_id), "current_status": order.status},
            )

        order.status = Order.Status.PAID
        order.payment_id = payment_id
        order.save(update_fields=["status", "payment_id", "updated_at"])

    logger.info(
        "Order marked as paid",
        extra={"extra_data": {
            "order_id": str(order_id),
            "payment_id": payment_id,
        }},
    )

    return order
