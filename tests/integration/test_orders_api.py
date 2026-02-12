"""
Orders API Integration Tests.

Ref: .blueprint/code_structure.md §5
Testing API complete flow - HTTP Request triggers Service correctly.

Test Coverage:
1. Success paths: place order, list orders, get order detail
2. Edge cases: insufficient stock, invalid coupon, unauthenticated
3. Security: user cannot access other user's orders
4. Rate limiting: frequent orders are blocked
"""
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Coupon, Order
from apps.products.models import Category, Product, Stock

User = get_user_model()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def api_client():
    """Create an API test client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    """Create another test user for permission tests."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="otherpass123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(
        name="Test Category",
        slug="test-category",
    )


@pytest.fixture
def product(db, category):
    """Create a test product."""
    return Product.objects.create(
        category=category,
        name="Test Product",
        description="A test product",
        price=Decimal("99.99"),
        is_active=True,
    )


@pytest.fixture
def product_with_stock(db, product):
    """Create product with stock."""
    Stock.objects.create(
        product=product,
        quantity=100,
    )
    return product


@pytest.fixture
def valid_coupon(db):
    """Create a valid coupon."""
    from django.utils import timezone
    from datetime import timedelta

    return Coupon.objects.create(
        code="DISCOUNT10",
        discount_type=Coupon.DiscountType.PERCENTAGE,
        discount_value=Decimal("10.00"),
        min_purchase_amount=Decimal("50.00"),
        valid_from=timezone.now() - timedelta(days=1),
        valid_until=timezone.now() + timedelta(days=30),
        total_limit=100,
        used_count=0,
        is_active=True,
    )


@pytest.fixture
def expired_coupon(db):
    """Create an expired coupon."""
    from django.utils import timezone
    from datetime import timedelta

    return Coupon.objects.create(
        code="EXPIRED",
        discount_type=Coupon.DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("20.00"),
        min_purchase_amount=Decimal("0.00"),
        valid_from=timezone.now() - timedelta(days=30),
        valid_until=timezone.now() - timedelta(days=1),
        total_limit=0,
        used_count=0,
        is_active=True,
    )


# =============================================================================
# Success Path Tests
# =============================================================================


@pytest.mark.django_db(transaction=True)
class TestPlaceOrderSuccess:
    """Test successful order placement."""

    def test_place_order_success(self, authenticated_client, product_with_stock):
        """Test placing a basic order successfully."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 2}
            ]
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "Order placed successfully"
        assert "order" in response.data
        assert response.data["order"]["status"] == "PENDING"
        assert Decimal(response.data["order"]["total_amount"]) == Decimal("199.98")

        # Verify stock was decreased
        product_with_stock.stock.refresh_from_db()
        assert product_with_stock.stock.quantity == 98

    def test_place_order_with_coupon(
        self, authenticated_client, product_with_stock, valid_coupon
    ):
        """Test placing order with valid coupon."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 2}
            ],
            "coupon_code": "DISCOUNT10",
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        # 199.98 * 10% = 19.998, rounded to 20.00
        assert Decimal(response.data["order"]["discount_amount"]) == Decimal("20.00")
        assert response.data["order"]["applied_coupon"]["code"] == "DISCOUNT10"


@pytest.mark.django_db
class TestOrderListSuccess:
    """Test successful order listing."""

    def test_get_orders_list_empty(self, authenticated_client):
        """Test getting empty order list."""
        url = reverse("orders:order-list-create")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["orders"] == []

    def test_get_orders_list_with_orders(
        self, authenticated_client, user, product_with_stock
    ):
        """Test getting order list with existing orders."""
        # Create an order first
        Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_amount=Decimal("99.99"),
        )

        url = reverse("orders:order-list-create")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["orders"]) == 1

    def test_get_orders_list_filtered_by_status(
        self, authenticated_client, user
    ):
        """Test filtering orders by status."""
        Order.objects.create(
            user=user, status=Order.Status.PENDING, total_amount=Decimal("100")
        )
        Order.objects.create(
            user=user, status=Order.Status.PAID, total_amount=Decimal("200")
        )

        url = reverse("orders:order-list-create")
        response = authenticated_client.get(url, {"status": "PAID"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["orders"]) == 1
        assert response.data["orders"][0]["status"] == "PAID"


@pytest.mark.django_db
class TestOrderDetailSuccess:
    """Test successful order detail retrieval."""

    def test_get_order_detail(self, authenticated_client, user):
        """Test getting order details."""
        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_amount=Decimal("99.99"),
        )

        url = reverse("orders:order-detail", kwargs={"order_id": order.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(order.id)
        assert response.data["status"] == "PENDING"


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.django_db(transaction=True)
class TestPlaceOrderEdgeCases:
    """Test order placement edge cases."""

    def test_place_order_insufficient_stock(
        self, authenticated_client, product_with_stock
    ):
        """Test placing order with insufficient stock."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 150}
            ]
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"]["code"] == "insufficient_stock"

    def test_place_order_invalid_coupon(
        self, authenticated_client, product_with_stock
    ):
        """Test placing order with non-existent coupon."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 1}
            ],
            "coupon_code": "NONEXISTENT",
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "coupon_not_found"

    def test_place_order_expired_coupon(
        self, authenticated_client, product_with_stock, expired_coupon
    ):
        """Test placing order with expired coupon."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 1}
            ],
            "coupon_code": "EXPIRED",
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"]["code"] == "coupon_expired"

    def test_place_order_empty_items(self, authenticated_client):
        """Test placing order with no items."""
        url = reverse("orders:order-list-create")
        data = {"items": []}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_place_order_invalid_product_id(self, authenticated_client):
        """Test placing order with non-existent product."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(uuid4()), "quantity": 1}
            ]
        }

        response = authenticated_client.post(url, data, format="json")

        # Product.DoesNotExist should be handled
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]


# =============================================================================
# Authentication Tests
# =============================================================================


@pytest.mark.django_db
class TestOrderAuthentication:
    """Test order API authentication requirements."""

    def test_place_order_unauthenticated(self, api_client, product_with_stock):
        """Test that unauthenticated users cannot place orders."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 1}
            ]
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_orders_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list orders."""
        url = reverse("orders:order-list-create")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_order_detail_unauthenticated(self, api_client, user):
        """Test that unauthenticated users cannot view order details."""
        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_amount=Decimal("99.99"),
        )

        url = reverse("orders:order-detail", kwargs={"order_id": order.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Security Tests (Ref: code_structure.md §6 - DoD)
# =============================================================================


@pytest.mark.django_db
class TestOrderSecurity:
    """Test order security - users cannot access other users' orders."""

    def test_get_order_forbidden_other_user(
        self, authenticated_client, other_user
    ):
        """Test that user cannot view another user's order."""
        # Create order for other_user
        other_order = Order.objects.create(
            user=other_user,
            status=Order.Status.PENDING,
            total_amount=Decimal("99.99"),
        )

        url = reverse("orders:order-detail", kwargs={"order_id": other_order.id})
        response = authenticated_client.get(url)

        # Should return 404 (not 403) to avoid leaking order existence
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_orders_list_only_shows_own_orders(
        self, authenticated_client, user, other_user
    ):
        """Test that order list only shows user's own orders."""
        # Create orders for both users
        Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_amount=Decimal("100"),
        )
        Order.objects.create(
            user=other_user,
            status=Order.Status.PENDING,
            total_amount=Decimal("200"),
        )

        url = reverse("orders:order-list-create")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["orders"]) == 1
        assert Decimal(response.data["orders"][0]["total_amount"]) == Decimal("100")


# =============================================================================
# Rate Limiting Tests (Ref: data.md §2D)
# =============================================================================


@pytest.mark.django_db(transaction=True)
class TestOrderRateLimiting:
    """Test order rate limiting."""

    def test_place_order_rate_limited(
        self, authenticated_client, product_with_stock
    ):
        """Test that rapid consecutive orders are rate limited."""
        url = reverse("orders:order-list-create")
        data = {
            "items": [
                {"product_id": str(product_with_stock.id), "quantity": 1}
            ]
        }

        # First order should succeed
        response1 = authenticated_client.post(url, data, format="json")
        assert response1.status_code == status.HTTP_201_CREATED

        # Immediate second order should be rate limited
        response2 = authenticated_client.post(url, data, format="json")
        assert response2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response2.data["error"]["code"] == "rate_limit_exceeded"
