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

# Import models for exception handling
from apps.products.models import Category, Stock, Product

from .serializers import (
    AdminOrdersListResponseSerializer,
    InventoryListResponseSerializer,
    RestockRequestSerializer,
    RestockResponseSerializer,
    ProductCreateRequestSerializer,
    ProductCreateResponseSerializer,
    ProductUpdateRequestSerializer,
    ProductDeleteResponseSerializer,
)
from .selectors import get_all_products_with_stock, get_product_with_realtime_stock
from .services import (
    get_admin_orders,
    get_inventory_report,
    restock_product,
    create_product_with_inventory,
    update_product,
    delete_product,
)

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


class AdminProductCreateView(APIView):
    """API endpoint for creating new products with inventory."""

    permission_classes = [IsAdminUser]

    def post(self, request: Request) -> Response:
        """
        Create a new product with initial inventory.

        POST /api/admin/inventory/

        Request body:
            name: Product name (required)
            price: Product price (required, must be > 0)
            category_id: Category UUID (required)
            description: Product description (optional)
            image_url: Product image URL (optional)
            initial_stock: Initial stock quantity (optional, default: 0)

        Returns:
            Created product information
        """
        # Validate request data
        serializer = ProductCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        logger.info(
            "Product creation initiated",
            extra={
                "extra_data": {
                    "admin_user_id": str(request.user.id),
                    "admin_username": request.user.username,
                    "product_data": serializer.validated_data,
                }
            },
        )

        try:
            # Call service to create product with inventory
            result = create_product_with_inventory(
                name=serializer.validated_data["name"],
                price=serializer.validated_data["price"],
                category_id=serializer.validated_data["category_id"],
                description=serializer.validated_data.get("description", ""),
                image_url=serializer.validated_data.get("image_url", ""),
                initial_stock=serializer.validated_data.get("initial_stock", 0),
                admin_user=request.user,
            )

            logger.info(
                "Product created successfully",
                extra={
                    "extra_data": {
                        "product_id": str(result["product"]["id"]),
                        "name": result["product"]["name"],
                        "initial_stock": result["stock"]["quantity"],
                    }
                },
            )

            response_data = {
                "success": True,
                "data": result
            }
            response_serializer = ProductCreateResponseSerializer(response_data)
            return Response(
                {
                    "success": True,
                    "message": "Product created successfully",
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Category.DoesNotExist:
            logger.warning(
                "Product creation failed - category not found",
                extra={
                    "extra_data": {
                        "category_id": str(serializer.validated_data["category_id"]),
                    }
                },
            )
            return Response(
                {
                    "error": {
                        "code": "category_not_found",
                        "message": "Category not found",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValueError as e:
            logger.warning(
                "Product creation validation failed",
                extra={
                    "extra_data": {
                        "error": str(e),
                    }
                },
            )
            return Response(
                {"error": {"code": "validation_error", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminProductUpdateView(APIView):
    """API endpoint for updating products."""

    permission_classes = [IsAdminUser]

    def patch(self, request: Request, product_id: UUID) -> Response:
        """
        Update product information.

        PATCH /api/admin/inventory/{id}/

        Request body (at least one field required):
            name: Product name
            price: Product price (must be > 0)
            description: Product description
            image_url: Product image URL
            category_id: Category UUID

        Returns:
            Updated product information
        """
        # Validate request data
        serializer = ProductUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        logger.info(
            "Product update initiated",
            extra={
                "extra_data": {
                    "product_id": str(product_id),
                    "admin_user_id": str(request.user.id),
                    "admin_username": request.user.username,
                    "update_data": serializer.validated_data,
                }
            },
        )

        try:
            # Call service to update product
            result = update_product(
                product_id=product_id,
                admin_user=request.user,
                **serializer.validated_data,
            )

            logger.info(
                "Product updated successfully",
                extra={
                    "extra_data": {
                        "product_id": str(product_id),
                        "updated_fields": list(serializer.validated_data.keys()),
                    }
                },
            )

            return Response(
                {
                    "success": True,
                    "message": "Product updated successfully",
                    "data": result,
                }
            )

        except Product.DoesNotExist:
            logger.warning(
                "Product update failed - product not found",
                extra={"extra_data": {"product_id": str(product_id)}},
            )
            return Response(
                {
                    "error": {
                        "code": "product_not_found",
                        "message": "Product not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Category.DoesNotExist:
            logger.warning(
                "Product update failed - category not found",
                extra={
                    "extra_data": {
                        "category_id": str(serializer.validated_data.get("category_id", "")),
                    }
                },
            )
            return Response(
                {
                    "error": {
                        "code": "category_not_found",
                        "message": "Category not found",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValueError as e:
            logger.warning(
                "Product update validation failed",
                extra={
                    "extra_data": {
                        "product_id": str(product_id),
                        "error": str(e),
                    }
                },
            )
            return Response(
                {"error": {"code": "validation_error", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request: Request, product_id: UUID) -> Response:
        """
        Soft delete a product (set is_active=False).

        DELETE /api/admin/products/{id}/

        Returns:
            Deletion confirmation
        """
        logger.info(
            "Product deletion initiated",
            extra={
                "extra_data": {
                    "product_id": str(product_id),
                    "admin_user_id": str(request.user.id),
                    "admin_username": request.user.username,
                }
            },
        )

        try:
            # Call service to delete product
            delete_product(product_id=product_id, admin_user=request.user)

            response_data = {
                "success": True,
                "message": f"Product {product_id} deleted successfully"
            }
            serializer = ProductDeleteResponseSerializer(response_data)

            logger.info(
                "Product deleted successfully",
                extra={"extra_data": {"product_id": str(product_id)}},
            )

            return Response(serializer.data)

        except Product.DoesNotExist:
            logger.warning(
                "Product deletion failed - product not found",
                extra={"extra_data": {"product_id": str(product_id)}},
            )
            return Response(
                {
                    "error": {
                        "code": "product_not_found",
                        "message": "Product not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class AdminCategoryListView(APIView):
    """API endpoint for listing categories."""

    permission_classes = [IsAdminUser]

    def get(self, request: Request) -> Response:
        """
        List all categories.

        GET /api/admin/categories/
        """
        categories = Category.objects.all().values("id", "name")
        return Response({"categories": list(categories)})
