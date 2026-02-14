"""Integration tests for Admin CRUD API endpoints."""

import json
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Category, Product, Stock

User = get_user_model()


@pytest.mark.django_db
class TestAdminProductCRUDAPI(APITestCase):
    """Test admin product CRUD operations."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='testadmin@example.com',
            password='testpass123',
            is_staff=True
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
            is_staff=False
        )

        # Create category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        # Create product with stock
        self.product = Product.objects.create(
            name='Original Product',
            price='19.99',
            category=self.category
        )
        self.stock = Stock.objects.create(product=self.product, quantity=50)

    def test_create_product_success(self):
        """Test successful product creation."""
        self.client.force_authenticate(user=self.admin_user)

        # Prepare create data
        create_data = {
            'name': 'New Test Product',
            'price': '29.99',
            'category_id': str(self.category.id),
            'description': 'A test product description',
            'image_url': 'https://example.com/image.jpg',
            'initial_stock': 100
        }

        response = self.client.post(
            '/api/admin/products/',
            data=json.dumps(create_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()

        assert response_data['success'] is True
        assert response_data['message'] == 'Product created successfully'
        assert 'data' in response_data

        # Verify product was created - response has nested structure
        # response_data['data'] contains serialized ProductCreateResponseSerializer
        # which has {success: True, data: {product: {...}, stock: {...}}}
        result_data = response_data['data']['data']
        assert result_data['product']['name'] == 'New Test Product'
        assert str(result_data['product']['price']) == '29.99'  # Compare to string
        assert result_data['stock']['quantity'] == 100

        # Verify database
        product = Product.objects.get(id=result_data['product']['id'])
        assert product.name == 'New Test Product'
        assert str(product.price) == '29.99'
        assert product.stock.quantity == 100

    def test_create_product_invalid_category(self):
        """Test product creation with invalid category."""
        self.client.force_authenticate(user=self.admin_user)

        create_data = {
            'name': 'Invalid Product',
            'price': '19.99',
            'category_id': '00000000-0000-0000-0000-000000000000'  # Non-existent UUID
        }

        response = self.client.post(
            '/api/admin/products/',
            data=json.dumps(create_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert 'error' in response_data
        assert response_data['error']['code'] == 'category_not_found'

    def test_create_product_unauthenticated(self):
        """Test product creation without authentication."""
        create_data = {
            'name': 'Test Product',
            'price': '19.99',
            'category_id': str(self.category.id)
        }

        response = self.client.post(
            '/api/admin/products/',
            data=json.dumps(create_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_non_admin(self):
        """Test product creation with non-admin user."""
        self.client.force_authenticate(user=self.regular_user)

        create_data = {
            'name': 'Test Product',
            'price': '19.99',
            'category_id': str(self.category.id)
        }

        response = self.client.post(
            '/api/admin/products/',
            data=json.dumps(create_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_product_success(self):
        """Test successful product update."""
        self.client.force_authenticate(user=self.admin_user)

        update_data = {
            'name': 'Updated Product Name',
            'price': '25.00',
            'description': 'Updated description'
        }

        response = self.client.patch(
            f'/api/admin/products/{self.product.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data['success'] is True
        assert response_data['message'] == 'Product updated successfully'

        # Verify database was updated
        self.product.refresh_from_db()
        assert self.product.name == 'Updated Product Name'
        assert self.product.price == 25.00
        assert self.product.description == 'Updated description'

    def test_update_product_not_found(self):
        """Test updating non-existent product."""
        self.client.force_authenticate(user=self.admin_user)

        fake_uuid = '00000000-0000-0000-0000-000000000000'
        update_data = {'name': 'Updated Name'}

        response = self.client.patch(
            f'/api/admin/products/{fake_uuid}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = response.json()
        assert 'error' in response_data
        assert response_data['error']['code'] == 'product_not_found'

    def test_update_product_no_fields(self):
        """Test updating product without providing any fields."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            f'/api/admin/products/{self.product.id}/',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert 'error' in response_data

    def test_delete_product_success(self):
        """Test successful product deletion (soft delete)."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.delete(f'/api/admin/products/{self.product.id}/')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data['success'] is True
        assert 'deleted successfully' in response_data['message']

        # Verify product was soft deleted
        self.product.refresh_from_db()
        assert self.product.is_active is False

    def test_delete_product_not_found(self):
        """Test deleting non-existent product."""
        self.client.force_authenticate(user=self.admin_user)

        fake_uuid = '00000000-0000-0000-0000-000000000000'

        response = self.client.delete(f'/api/admin/products/{fake_uuid}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = response.json()
        assert 'error' in response_data
        assert response_data['error']['code'] == 'product_not_found'

    def test_redis_sync_on_create(self):
        """Test that Redis is synchronized when creating product."""
        cache.clear()  # Clear cache before test

        self.client.force_authenticate(user=self.admin_user)

        create_data = {
            'name': 'Redis Test Product',
            'price': '99.99',
            'category_id': str(self.category.id),
            'initial_stock': 75
        }

        response = self.client.post(
            '/api/admin/products/',
            data=json.dumps(create_data),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        product_id = response_data['data']['data']['product']['id']

        # Give Redis a moment to update
        import time
        time.sleep(0.1)

        # Check Redis was updated
        redis_key = f"stock:{product_id}"
        cached_stock = cache.get(redis_key)
        assert cached_stock is not None
        assert cached_stock == 75

    def test_redis_delete_on_product_deletion(self):
        """Test that Redis cache is cleared when product is deleted."""
        # Setup Redis cache
        redis_key = f"stock:{self.product.id}"
        cache.set(redis_key, {'quantity': 50, 'status': 'in_stock'})

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/admin/products/{self.product.id}/')

        assert response.status_code == status.HTTP_200_OK

        # Check Redis cache was cleared
        assert cache.get(redis_key) is None
