"""
Order API Views.

Ref: .blueprint/code_structure.md §2
- View layer: parameter validation, call Service/Selector, handle HTTP status
- Single view function should not exceed 15 lines

Ref: .blueprint/data.md §5
- NEVER modify Stock.quantity directly in View layer
- Must use services.py functions
"""
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import get_logger

from .selectors import get_user_order, get_user_orders
from .serializers import (
    OrderDetailSerializer,
    OrderSerializer,
    PlaceOrderSerializer,
)
from .services import OrderItemInput, place_order

logger = get_logger(__name__)


class OrderListCreateView(APIView):
    """
    API endpoint for listing and creating orders.

    GET /api/orders/ - List user's orders
    POST /api/orders/ - Create a new order
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """
        List user's orders.

        Query params:
            status: Optional filter by order status
        """
        status_filter = request.query_params.get("status")
        orders = get_user_orders(request.user, status=status_filter)
        serializer = OrderSerializer(orders, many=True)
        return Response({"orders": serializer.data})

    def post(self, request: Request) -> Response:
        """
        Place a new order.

        Request body:
            items: List of {product_id, quantity}
            coupon_code: Optional coupon code
        """
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Convert to service input format
        items = [
            OrderItemInput(
                product_id=item["product_id"],
                quantity=item["quantity"],
            )
            for item in serializer.validated_data["items"]
        ]
        coupon_code = serializer.validated_data.get("coupon_code")

        # Call service (Ref: data.md §5 - all logic in services.py)
        result = place_order(
            user=request.user,
            items=items,
            coupon_code=coupon_code,
        )

        logger.info(
            "Order placed via API",
            extra={"extra_data": {
                "order_id": str(result.order.id),
                "user_id": str(request.user.id),
            }},
        )

        return Response(
            {
                "message": "Order placed successfully",
                "order": OrderDetailSerializer(result.order).data,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    """
    API endpoint for order detail.

    GET /api/orders/{id}/ - Get order details
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, order_id: UUID) -> Response:
        """
        Get order details.

        Ref: code_structure.md §6 (DoD)
        - Security: User A cannot view User B's orders
        """
        # Use selector that enforces ownership
        order = get_user_order(request.user, order_id)

        if order is None:
            return Response(
                {
                    "error": {
                        "code": "order_not_found",
                        "message": "Order not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)
