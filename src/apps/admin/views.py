"""Admin API Views.

Ref: .blueprint/code_sturcture.md §2
Ref: .blueprint/auth.md §4: IsAdminUser permission
Ref: .blueprint/data.md §5: Never modify stock directly in views

All /api/admin/* endpoints require IsAdminUser permission.
"""
from typing import Any
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import get_logger

from .serializers import (
    AdminOrdersListResponseSerializer,
    InventoryListResponseSerializer,
    RestockRequestSerializer,
    RestockResponseSerializer,
)
from .selectors import get_all_products_with_stock, get_product_with_realtime_stock
from .services import get_admin_orders, get_inventory_report, restock_product

logger = get_logger(__name__)


class AdminInventoryListView(APIView):
    """API endpoint for admin inventory management."""

    permission_classes = [IsAdminUser]

    def get(self, request: Request) -> Response:
        """
        List all products with inventory information.

        GET /api/admin/inventory/

        Query params:
            search: Optional product name search
            status: Optional stock status filter (low_stock, out_of_stock, in_stock)
            page: Page number (default: 1)
            page_size: Items per page (default: 20)
        """
        # Get query parameters
        search = request.query_params.get("search")
        stock_status = request.query_params.get("status")

        # TODO: Implement pagination and filtering in next phase

        logger.info(
            "Admin inventory list requested",
            extra={
                "extra_data": {
                    "admin_user_id": str(request.user.id),
                    "admin_username": request.user.username,
                }
            },
        )

        # Get inventory data
        inventory = get_inventory_report()

        # Apply search filter if provided
        if search:
            inventory = [item for item in inventory if search.lower() in item["name"].lower()]

        # Apply stock status filter if provided
        if stock_status in ["low_stock", "out_of_stock", "in_stock"]:
            inventory = [item for item in inventory if item["status"] == stock_status]

        # Serialize response
        serializer = InventoryListResponseSerializer({"inventory": inventory})

        logger.debug(
            "Admin inventory list returned", extra={"extra_data": {"count": len(inventory)}}
        )

        return Response(serializer.data)


class AdminInventoryRestockView(APIView):
    """API endpoint for restocking products."""

    permission_classes = [IsAdminUser]

    def patch(self, request: Request, product_id: UUID) -> Response:
        """
        Restock product inventory.

        PATCH /api/admin/inventory/{id}/restock/

        Request body:
            quantity: Integer amount to add to stock (must be > 0)

        Returns:
            Updated stock information
        """
        # Validate request data
        serializer = RestockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        logger.info(
            "Product restock initiated",
            extra={
                "extra_data": {
                    "product_id": str(product_id),
                    "admin_user_id": str(request.user.id),
                    "admin_username": request.user.username,
                    "quantity": quantity,
                }
            },
        )

        try:
            # Call service to restock product
            # Uses transaction.on_commit() to ensure Redis only updates after DB commit
            result = restock_product(product_id, quantity, request.user)

            logger.info(
                "Product restocked successfully",
                extra={"extra_data": result},
            )

            response_serializer = RestockResponseSerializer(result)
            return Response(
                {
                    "success": True,
                    "message": f"Successfully added {quantity} units to stock",
                    "data": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            logger.warning(
                "Restock validation failed",
                extra={
                    "extra_data": {
                        "product_id": str(product_id),
                        "error": str(e),
                    }
                },
            )
            return Response(
                {"error": {"code": "invalid_quantity", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Stock.DoesNotExist:
            logger.warning(
                "Product not found for restock",
                extra={"extra_data": {"product_id": str(product_id)}},
            )
            return Response(
                {
                    "error": {
                        "code": "product_not_found",
                        "message": "Product stock record not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class AdminOrdersListView(APIView):
    """API endpoint for admin order management with pagination."""

    permission_classes = [IsAdminUser]

    def get(self, request: Request) -> Response:
        """
        List all orders from admin perspective with pagination.

        GET /api/admin/orders/

        Query params:
            status: Optional order status filter (PENDING, PAID, SHIPPED, etc.)
            page: Page number (default: 1)
            page_size: Orders per page (default: 20, max: 100)
        """
        # Get pagination parameters
        try:
            page = int(request.query_params.get("page", 1))
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        try:
            # Ensure admin can only view up to 100 items per page
            page_size = int(request.query_params.get("page_size", 20))
            page_size = min(max(page_size, 1), 100)
        except ValueError:
            page_size = 20

        status_filter = request.query_params.get("status")

        logger.info(
            "Admin orders list requested",
            extra={
                "extra_data": {
                    "admin_user_id": str(request.user.id),
                    "admin_username": request.user.username,
                    "page": page,
                    "page_size": page_size,
                    "status_filter": status_filter,
                }
            },
        )

        # Get paginated orders using the service
        orders_data = get_admin_orders(
            status=status_filter, page=page, page_size=page_size
        )

        # Serialize response
        serializer = AdminOrdersListResponseSerializer(orders_data)

        logger.debug(
            "Admin orders list returned",
            extra={
                "extra_data": {
                    "count": len(orders_data["orders"]),
                    "total_count": orders_data["pagination"]["total_count"],
                }
            },
        )

        return Response(serializer.data)
