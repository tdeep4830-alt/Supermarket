"""Integration tests for Admin API endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.products.models import Category, Product, Stock

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
def products_with_stock(db, category):
    """Create products with stock for testing."""
    products = []
    for i in range(1, 4):
        product = Product.objects.create(
            category=category,
            name=f"Test Product {i}",
            price="99.99",
        )
        Stock.objects.create(product=product, quantity=10 * i)
        products.append(product)
    return products


@pytest.mark.django_db
def test_admin_inventory_list_authenticated(admin_client, products_with_stock):
    """Test GET /api/admin/inventory/ with admin authentication."""
    url = "/api/admin/inventory/"
    response = admin_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert "inventory" in response.data
    assert len(response.data["inventory"]) == 3

    # Check inventory items structure
    for item in response.data["inventory"]:
        assert "id" in item
        assert "name" in item
        assert "stock" in item
        assert "status" in item
        assert "category" in item


@pytest.mark.django_db
def test_admin_inventory_list_unauthenticated(client):
    """Test GET /api/admin/inventory/ without authentication."""
    url = "/api/admin/inventory/"
    response = client.get(url)

    # Should return 403 (unauthorized)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_inventory_list_non_admin_user(client, regular_user):
    """Test GET /api/admin/inventory/ with non-admin user."""
    client.force_login(regular_user)
    url = "/api/admin/inventory/"
    response = client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_restock_product_success(admin_client, products_with_stock):
    """Test PATCH /api/admin/inventory/{id}/restock/ with valid data."""
    product = products_with_stock[0]
    old_stock = product.stock.quantity
    url = f"/api/admin/inventory/{product.id}/restock/"

    response = admin_client.patch(url, {"quantity": 15}, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["data"]["quantity_added"] == 15
    assert response.data["data"]["old_quantity"] == old_stock
    assert response.data["data"]["new_quantity"] == old_stock + 15

    # Verify database was updated
    product.stock.refresh_from_db()
    assert product.stock.quantity == old_stock + 15


@pytest.mark.django_db
def test_admin_restock_product_invalid_quantity(admin_client, products_with_stock):
    """Test PATCH /api/admin/inventory/{id}/restock/ with invalid quantity."""
    product = products_with_stock[0]
    url = f"/api/admin/inventory/{product.id}/restock/"

    # Test with 0 quantity
    response = admin_client.patch(url, {"quantity": 0}, content_type="application/json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Test with negative quantity
    response = admin_client.patch(url, {"quantity": -5}, content_type="application/json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_admin_restock_nonexistent_product(admin_client):
    """Test PATCH /api/admin/inventory/{id}/restock/ with non-existent product."""
    import uuid

    fake_product_id = uuid.uuid4()
    url = f"/api/admin/inventory/{fake_product_id}/restock/"

    response = admin_client.patch(url, {"quantity": 10}, content_type="application/json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_admin_orders_list_pagination(admin_client, regular_user):
    """Test GET /api/admin/orders/ with pagination."""
    from apps.orders.models import Order

    # Create 25 orders
    for i in range(25):
        Order.objects.create(
            user=regular_user,
            status="PAID",
            total_amount="100.00",
        )

    url = "/api/admin/orders/"

    # Test first page (default: 20 items)
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["orders"]) == 20
    assert response.data["pagination"]["current_page"] == 1
    assert response.data["pagination"]["total_count"] == 25
    assert response.data["pagination"]["total_pages"] == 2

    # Test second page
    response = admin_client.get(f"{url}?page=2")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["orders"]) == 5
    assert response.data["pagination"]["current_page"] == 2

    # Test with custom page size
    response = admin_client.get(f"{url}?page=1&page_size=10")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["orders"]) == 10
    assert response.data["pagination"]["page_size"] == 10
    assert response.data["pagination"]["total_pages"] == 3


@pytest.mark.django_db
def test_admin_orders_list_status_filter(admin_client, regular_user):
    """Test GET /api/admin/orders/ with status filter."""
    from apps.orders.models import Order

    # Create orders with different statuses
    for i in range(3):
        Order.objects.create(
            user=regular_user,
            status="PAID",
            total_amount="100.00",
        )

    for i in range(2):
        Order.objects.create(
            user=regular_user,
            status="PENDING",
            total_amount="50.00",
        )

    url = "/api/admin/orders/"

    # Filter by PAID status
    response = admin_client.get(f"{url}?status=PAID")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["orders"]) == 3
    assert response.data["pagination"]["total_count"] == 3

    # Filter by PENDING status
    response = admin_client.get(f"{url}?status=PENDING")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["orders"]) == 2
    assert response.data["pagination"]["total_count"] == 2


@pytest.mark.django_db
def test_admin_api_permission_denied_for_regular_user(client, regular_user, products_with_stock):
    """Test all admin APIs return 403 for non-admin users."""
    client.force_login(regular_user)
    product = products_with_stock[0]

    # Test inventory list
    url = "/api/admin/inventory/"
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Test restock
    url = f"/api/admin/inventory/{product.id}/restock/"
    response = client.patch(url, {"quantity": 10}, content_type="application/json")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Test orders list
    url = "/api/admin/orders/"
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
