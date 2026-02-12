"""
Custom Business Exceptions for Online Supermarket.

Ref: .blueprint/code_sturcture.md §4
- Business errors should raise custom exceptions
- Do NOT return None or False for errors
"""
from typing import Any


class SupermarketException(Exception):
    """Base exception for all business logic errors."""

    default_message = "An error occurred"
    default_code = "error"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.extra = extra or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to API response format."""
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.extra:
            result["error"]["details"] = self.extra
        return result


# =============================================================================
# Inventory Exceptions (Ref: data.md §1B)
# =============================================================================

class InsufficientStockException(SupermarketException):
    """Raised when attempting to purchase more than available stock."""
    default_message = "Insufficient stock for this product"
    default_code = "insufficient_stock"


class StockUpdateConflictException(SupermarketException):
    """Raised when optimistic locking detects concurrent update."""
    default_message = "Stock was modified by another transaction"
    default_code = "stock_conflict"


# =============================================================================
# Order Exceptions (Ref: data.md §1C)
# =============================================================================

class OrderNotFoundException(SupermarketException):
    default_message = "Order not found"
    default_code = "order_not_found"


class InvalidOrderStatusException(SupermarketException):
    default_message = "Invalid order status transition"
    default_code = "invalid_order_status"


# =============================================================================
# Coupon Exceptions (Ref: data.md §1E)
# =============================================================================

class CouponNotFoundException(SupermarketException):
    default_message = "Coupon not found"
    default_code = "coupon_not_found"


class CouponExpiredException(SupermarketException):
    default_message = "This coupon has expired"
    default_code = "coupon_expired"


class CouponAlreadyUsedException(SupermarketException):
    default_message = "You have already used this coupon"
    default_code = "coupon_already_used"


class CouponQuotaExceededException(SupermarketException):
    default_message = "This coupon is no longer available"
    default_code = "coupon_quota_exceeded"


class MinimumPurchaseNotMetException(SupermarketException):
    default_message = "Minimum purchase amount not met"
    default_code = "minimum_purchase_not_met"


# =============================================================================
# Rate Limiting (Ref: data.md §2D)
# =============================================================================

class RateLimitExceededException(SupermarketException):
    default_message = "Too many requests, please try again later"
    default_code = "rate_limit_exceeded"
