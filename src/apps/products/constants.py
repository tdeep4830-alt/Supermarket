"""
Products App Constants.

Ref: .blueprint/data.md §2
Redis Key patterns and configuration constants.
"""

# =============================================================================
# Redis Key Patterns (Ref: data.md §2)
# =============================================================================

# 庫存快照 (§2A)
REDIS_KEY_STOCK = "stock:{product_id}"

# 下單限流 (§2D)
REDIS_KEY_RATE_LIMIT_ORDER = "ratelimit:order:{user_id}"

# =============================================================================
# Configuration Constants
# =============================================================================

# 限流設定：1 秒內只能下單一次
RATE_LIMIT_ORDER_SECONDS = 1

# 庫存快照過期時間（秒）- 用於 Cache-Aside 回填
STOCK_CACHE_TTL_SECONDS = 300  # 5 minutes
