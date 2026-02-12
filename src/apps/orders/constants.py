"""
Orders App Constants.

Ref: .blueprint/data.md §1C, §2E
Redis Key patterns, status transitions, and configuration constants.
"""
from .models import Order

# =============================================================================
# Redis Key Patterns (Ref: data.md §2E)
# =============================================================================

# 優惠碼配額快照
REDIS_KEY_COUPON_QUOTA = "coupon:quota:{coupon_code}"

# 優惠碼配額過期時間（秒）
COUPON_QUOTA_CACHE_TTL_SECONDS = 300  # 5 minutes

# =============================================================================
# Order Status Transitions (Ref: data.md §1C)
# =============================================================================

# 允許的狀態轉換
# 格式: {當前狀態: [允許轉換的目標狀態]}
VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    Order.Status.PENDING: [
        Order.Status.PAID,
        Order.Status.CANCELLED,
    ],
    Order.Status.PAID: [
        Order.Status.SHIPPED,
        Order.Status.REFUNDED,
    ],
    Order.Status.SHIPPED: [
        Order.Status.REFUNDED,
    ],
    Order.Status.CANCELLED: [],  # 終態
    Order.Status.REFUNDED: [],   # 終態
}

# 需要恢復庫存的狀態
STATUSES_REQUIRING_STOCK_RESTORE = [
    Order.Status.CANCELLED,
    Order.Status.REFUNDED,
]
