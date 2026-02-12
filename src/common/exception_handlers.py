"""
Custom Exception Handlers for Django REST Framework.

Ref: .blueprint/protocol.md §4
- All API responses must include standardized Error Response
- Distinguish between business errors (stock insufficient) and system errors (DB timeout)
"""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.exceptions import (
    CouponAlreadyUsedException,
    CouponExpiredException,
    CouponNotFoundException,
    CouponQuotaExceededException,
    InsufficientStockException,
    InvalidOrderStatusException,
    MinimumPurchaseNotMetException,
    OrderNotFoundException,
    RateLimitExceededException,
    StockUpdateConflictException,
    SupermarketException,
)
from common.logging import get_logger

logger = get_logger(__name__)

# Mapping of exception types to HTTP status codes
EXCEPTION_STATUS_MAP = {
    # 400 Bad Request - Client errors
    MinimumPurchaseNotMetException: status.HTTP_400_BAD_REQUEST,
    InvalidOrderStatusException: status.HTTP_400_BAD_REQUEST,
    # 404 Not Found
    OrderNotFoundException: status.HTTP_404_NOT_FOUND,
    CouponNotFoundException: status.HTTP_404_NOT_FOUND,
    # 409 Conflict - Resource state conflicts
    InsufficientStockException: status.HTTP_409_CONFLICT,
    StockUpdateConflictException: status.HTTP_409_CONFLICT,
    CouponAlreadyUsedException: status.HTTP_409_CONFLICT,
    CouponQuotaExceededException: status.HTTP_409_CONFLICT,
    CouponExpiredException: status.HTTP_409_CONFLICT,
    # 429 Too Many Requests
    RateLimitExceededException: status.HTTP_429_TOO_MANY_REQUESTS,
}


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Custom exception handler for DRF.

    Converts SupermarketException instances to standardized JSON responses.
    Falls back to DRF's default handler for other exceptions.

    Args:
        exc: The exception instance
        context: Additional context (view, request, etc.)

    Returns:
        Response or None
    """
    # First, call DRF's default exception handler
    response = exception_handler(exc, context)

    # Handle our custom business exceptions
    if isinstance(exc, SupermarketException):
        status_code = EXCEPTION_STATUS_MAP.get(
            type(exc),
            status.HTTP_400_BAD_REQUEST,
        )

        logger.warning(
            f"Business exception: {exc.code}",
            extra={"extra_data": {
                "exception_type": type(exc).__name__,
                "code": exc.code,
                "message": exc.message,
                "details": exc.extra,
            }},
        )

        return Response(
            exc.to_dict(),
            status=status_code,
        )

    # Handle Django's ObjectDoesNotExist (e.g., Product.DoesNotExist)
    if isinstance(exc, ObjectDoesNotExist):
        logger.warning(
            f"Object not found: {type(exc).__name__}",
            extra={"extra_data": {"message": str(exc)}},
        )
        return Response(
            {
                "error": {
                    "code": "not_found",
                    "message": str(exc) or "Requested resource not found",
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Handle validation errors with consistent format
    if response is not None and response.status_code == 400:
        # Wrap DRF validation errors in our format
        if isinstance(response.data, dict) and "error" not in response.data:
            response.data = {
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request data",
                    "details": response.data,
                }
            }

    return response
