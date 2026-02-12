"""
Order & Coupon Selectors (Read Operations).

Ref: .blueprint/code_sturcture.md §2

提供訂單與優惠碼的讀取操作：
- get_user_orders: 取得用戶訂單列表
- get_order_by_id: 取得單一訂單
- get_order_with_items: 取得訂單含明細
- get_available_coupons_for_user: 取得用戶可用優惠碼
- get_order_summary_report: 訂單統計報表
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from django.db.models import Count, QuerySet, Sum
from django.utils import timezone

from .models import Coupon, Order, OrderItem, UserCoupon

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


# =============================================================================
# Order Selectors
# =============================================================================


def get_user_orders(
    user: "AbstractUser",
    status: str | None = None,
) -> QuerySet[Order]:
    """
    取得用戶訂單列表.

    Args:
        user: 用戶
        status: 過濾狀態（可選）

    Returns:
        QuerySet[Order]: 訂單列表（按建立時間降序）
    """
    queryset = Order.objects.filter(user=user).select_related(
        "applied_coupon",
    ).prefetch_related(
        "items__product",
    ).order_by("-created_at")

    if status:
        queryset = queryset.filter(status=status)

    return queryset


def get_order_by_id(order_id: UUID) -> Order | None:
    """
    依 ID 取得訂單.

    Args:
        order_id: 訂單 UUID

    Returns:
        Order | None: 訂單實例或 None
    """
    try:
        return Order.objects.select_related(
            "user",
            "applied_coupon",
        ).get(id=order_id)
    except Order.DoesNotExist:
        return None


def get_order_with_items(order_id: UUID) -> dict | None:
    """
    取得訂單及其明細.

    Args:
        order_id: 訂單 UUID

    Returns:
        dict | None: 訂單資訊含明細
    """
    try:
        order = Order.objects.select_related(
            "user",
            "applied_coupon",
        ).prefetch_related(
            "items__product__category",
        ).get(id=order_id)

        items = []
        for item in order.items.all():
            items.append({
                "id": item.id,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "category": item.product.category.name,
                },
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "subtotal": item.price_at_purchase * item.quantity,
            })

        return {
            "id": order.id,
            "user_id": order.user_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "discount_amount": order.discount_amount,
            "applied_coupon": order.applied_coupon.code if order.applied_coupon else None,
            "payment_id": order.payment_id,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": items,
        }

    except Order.DoesNotExist:
        return None


def get_user_order(user: "AbstractUser", order_id: UUID) -> Order | None:
    """
    取得用戶的特定訂單（確認歸屬權）.

    Args:
        user: 用戶
        order_id: 訂單 UUID

    Returns:
        Order | None: 訂單實例或 None
    """
    try:
        return Order.objects.select_related(
            "applied_coupon",
        ).prefetch_related(
            "items__product",
        ).get(id=order_id, user=user)
    except Order.DoesNotExist:
        return None


# =============================================================================
# Coupon Selectors
# =============================================================================


def get_available_coupons_for_user(user: "AbstractUser") -> QuerySet[Coupon]:
    """
    取得用戶可用的優惠碼.

    條件：
    1. 優惠碼啟用中
    2. 在有效期內
    3. 未超過使用限制
    4. 用戶尚未使用過

    Args:
        user: 用戶

    Returns:
        QuerySet[Coupon]: 可用優惠碼列表
    """
    now = timezone.now()

    # 取得用戶已使用的優惠碼 IDs
    used_coupon_ids = UserCoupon.objects.filter(
        user=user,
        used_at__isnull=False,
    ).values_list("coupon_id", flat=True)

    return Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now,
    ).exclude(
        id__in=used_coupon_ids,
    ).extra(
        where=["total_limit = 0 OR used_count < total_limit"],
    ).order_by("-created_at")


def get_coupon_by_code(code: str) -> Coupon | None:
    """
    依代碼取得優惠碼.

    Args:
        code: 優惠碼

    Returns:
        Coupon | None: 優惠碼實例或 None
    """
    try:
        return Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return None


def get_user_coupon_history(user: "AbstractUser") -> QuerySet[UserCoupon]:
    """
    取得用戶優惠碼使用紀錄.

    Args:
        user: 用戶

    Returns:
        QuerySet[UserCoupon]: 使用紀錄列表
    """
    return UserCoupon.objects.filter(
        user=user,
    ).select_related(
        "coupon",
    ).order_by("-used_at")


# =============================================================================
# Report Selectors (Admin)
# =============================================================================


def get_order_summary_report(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """
    取得訂單統計報表.

    Args:
        start_date: 開始日期（可選）
        end_date: 結束日期（可選）

    Returns:
        dict: 統計報表
    """
    queryset = Order.objects.all()

    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)

    # 總體統計
    total_stats = queryset.aggregate(
        total_orders=Count("id"),
        total_revenue=Sum("total_amount"),
        total_discount=Sum("discount_amount"),
    )

    # 按狀態統計
    status_stats = queryset.values("status").annotate(
        count=Count("id"),
        revenue=Sum("total_amount"),
    ).order_by("status")

    return {
        "period": {
            "start": start_date,
            "end": end_date,
        },
        "total": {
            "orders": total_stats["total_orders"] or 0,
            "revenue": total_stats["total_revenue"] or Decimal("0.00"),
            "discount": total_stats["total_discount"] or Decimal("0.00"),
        },
        "by_status": list(status_stats),
    }


def get_coupon_usage_report(coupon_id: UUID) -> dict | None:
    """
    取得優惠碼使用報表.

    Args:
        coupon_id: 優惠碼 UUID

    Returns:
        dict | None: 使用報表
    """
    try:
        coupon = Coupon.objects.get(id=coupon_id)
    except Coupon.DoesNotExist:
        return None

    # 使用此優惠碼的訂單統計
    orders_with_coupon = Order.objects.filter(applied_coupon=coupon)
    stats = orders_with_coupon.aggregate(
        order_count=Count("id"),
        total_discount=Sum("discount_amount"),
        total_revenue=Sum("total_amount"),
    )

    return {
        "coupon": {
            "id": coupon.id,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "total_limit": coupon.total_limit,
            "used_count": coupon.used_count,
            "is_active": coupon.is_active,
            "valid_from": coupon.valid_from,
            "valid_until": coupon.valid_until,
        },
        "usage": {
            "orders": stats["order_count"] or 0,
            "total_discount_given": stats["total_discount"] or Decimal("0.00"),
            "total_order_revenue": stats["total_revenue"] or Decimal("0.00"),
            "remaining_uses": (
                coupon.total_limit - coupon.used_count
                if coupon.total_limit > 0
                else None  # Unlimited
            ),
        },
    }
