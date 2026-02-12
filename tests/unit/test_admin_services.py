"""Unit tests for admin services."""

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Category, Product, Stock
from apps.admin.services import get_inventory_report, get_admin_orders, restock_product

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        is_staff=True,
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user."""
    return User.objects.create_user(
        username="user",
        email="user@example.com",
        password="userpass123",
        is_staff=False,
    )


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(name="Test Category", slug="test-category")


@pytest.fixture
def product_with_stock(db, category):
    """Create a product with stock."""
    product = Product.objects.create(
        category=category,
        name="Test Product",
        price="99.99",
    )
    stock = Stock.objects.create(product=product, quantity=50)
    return product


class TestRestockProduct:
    """Test restock product service."""

    def test_restock_product_success(self, db, product_with_stock, admin_user):
        """Test successful product restock."""
        old_quantity = product_with_stock.stock.quantity
        restock_quantity = 25

        result = restock_product(product_with_stock.id, restock_quantity, admin_user)

        # Check result
        assert result["product_id"] == product_with_stock.id
        assert result["quantity_added"] == restock_quantity
        assert result["old_quantity"] == old_quantity
        assert result["new_quantity"] == old_quantity + restock_quantity

        # Check database was updated
        product_with_stock.stock.refresh_from_db()
        assert product_with_stock.stock.quantity == old_quantity + restock_quantity

    def test_restock_product_invalid_quantity(self, db, product_with_stock, admin_user):
        """Test restock with invalid quantity."""
        with pytest.raises(ValueError, match="Restock quantity must be positive"):
            restock_product(product_with_stock.id, 0, admin_user)

        with pytest.raises(ValueError, match="Restock quantity must be positive"):
            restock_product(product_with_stock.id, -5, admin_user)

    def test_restock_product_not_found(self, db, admin_user):
        """Test restock of non-existent product."""
        import uuid

        fake_product_id = uuid.uuid4()

        with pytest.raises(Stock.DoesNotExist):
            restock_product(fake_product_id, 10, admin_user)

    def test_concurrent_restock_no_race_condition(self, db, product_with_stock, admin_user):
        """Test concurrent restocks don't cause race conditions."""
        # Note: This test is skipped in unit tests as it requires database
        # transaction handling that's better tested in integration tests
        pytest.skip("Concurrent restock test requires integration test setup")


class TestGetInventoryReport:
    """Test get inventory report service."""

    def test_get_inventory_report(self, db, category):
        """Test getting complete inventory report."""
        # Create test products with different stock levels
        product1 = Product.objects.create(
            category=category,
            name="Product 1",
            price="10.00",
        )
        Stock.objects.create(product=product1, quantity=5)  # Low stock

        product2 = Product.objects.create(
            category=category,
            name="Product 2",
            price="20.00",
        )
        Stock.objects.create(product=product2, quantity=0)  # Out of stock

        product3 = Product.objects.create(
            category=category,
            name="Product 3",
            price="30.00",
        )
        Stock.objects.create(product=product3, quantity=50)  # In stock

        # Create inactive product (should not appear in report)
        product4 = Product.objects.create(
            category=category,
            name="Product 4",
            price="40.00",
            is_active=False,
        )
        Stock.objects.create(product=product4, quantity=10)

        # Get report
        report = get_inventory_report()

        # Check report contains only active products
        assert len(report) == 3
        product_names = [item["name"] for item in report]
        assert "Product 1" in product_names
        assert "Product 2" in product_names
        assert "Product 3" in product_names
        assert "Product 4" not in product_names

        # Check stock statuses
        for item in report:
            if item["name"] == "Product 1":
                assert item["stock"] == 5
                assert item["status"] == "low_stock"
            elif item["name"] == "Product 2":
                assert item["stock"] == 0
                assert item["status"] == "out_of_stock"
            elif item["name"] == "Product 3":
                assert item["stock"] == 50
                assert item["status"] == "in_stock"


class TestGetAdminOrders:
    """Test get admin orders service."""

    def test_get_admin_orders_with_pagination(self, db, regular_user, admin_user):
        """Test getting orders with pagination."""
        from apps.orders.models import Order

        # Create test orders
        orders = []
        for i in range(25):
            order = Order.objects.create(
                user=regular_user,
                status="PAID",
                total_amount="100.00",
            )
            orders.append(order)

        # Test first page
        result = get_admin_orders(page=1, page_size=10)
        assert len(result["orders"]) == 10
        assert result["pagination"]["current_page"] == 1
        assert result["pagination"]["page_size"] == 10
        assert result["pagination"]["total_count"] == 25
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is False

        # Test second page
        result = get_admin_orders(page=2, page_size=10)
        assert len(result["orders"]) == 10
        assert result["pagination"]["current_page"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is True

        # Test third page (last page)
        result = get_admin_orders(page=3, page_size=10)
        assert len(result["orders"]) == 5
        assert result["pagination"]["current_page"] == 3
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is True

    def test_get_admin_orders_with_status_filter(self, db, regular_user):
        """Test getting orders with status filter."""
        from apps.orders.models import Order

        # Create orders with different statuses
        for i in range(5):
            Order.objects.create(
                user=regular_user,
                status="PAID" if i < 3 else "PENDING",
                total_amount="100.00",
            )

        # Filter by PAID status
        result = get_admin_orders(status="PAID", page=1, page_size=20)
        assert len(result["orders"]) == 3
        assert result["pagination"]["total_count"] == 3

        # Filter by PENDING status
        result = get_admin_orders(status="PENDING", page=1, page_size=20)
        assert len(result["orders"]) == 2
        assert result["pagination"]["total_count"] == 2
