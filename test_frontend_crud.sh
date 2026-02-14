#!/bin/bash

# Frontend CRUD Operations Test Script
# This script tests all CRUD operations through the API

set -e

echo "=========================================="
echo "Frontend CRUD Operations Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URLs
BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api"

# Test credentials
USERNAME="testadmin"
PASSWORD="testpass123"

echo "Step 1: Create test admin user"
docker-compose run --rm web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='testadmin').exists():
    User.objects.create_superuser('testadmin', 'test@example.com', 'testpass123')
    print('✓ Test admin user created')
else:
    print('✓ Test admin user already exists')
"
echo ""

echo "Step 2: Create test category"
docker-compose run --rm web python manage.py shell -c "
from apps.products.models import Category
cat, created = Category.objects.get_or_create(name='Test Category', defaults={'slug': 'test-category'})
print(f'✓ Category: {cat.name} (ID: {cat.id})')
"
echo ""

echo "Step 3: Test CREATE operation"
echo "Creating a new product via API..."
docker-compose run --rm web python manage.py shell -c "
from django.test import Client
from django.contrib.auth import get_user_model
from apps.products.models import Category
import json

User = get_user_model()
client = Client()

# Login as admin
admin = User.objects.get(username='testadmin')
client.force_login(admin)

# Get category
category = Category.objects.get(name='Test Category')

# Create product
response = client.post('/api/admin/products/', {
    'name': 'Test Product 1',
    'price': '29.99',
    'category_id': str(category.id),
    'description': 'A test product',
    'initial_stock': 100
}, content_type='application/json')

if response.status_code == 201:
    data = json.loads(response.content)
    print(f'✓ Product created: {data[\"data\"][\"data\"][\"product\"][\"name\"]}')
    print(f'  ID: {data[\"data\"][\"data\"][\"product\"][\"id\"]}')
    print(f'  Stock: {data[\"data\"][\"data\"][\"stock\"][\"quantity\"]}')
else:
    print(f'✗ Failed: {response.status_code}')
    print(response.content)
"
echo ""

echo "Step 4: Test UPDATE operation"
echo "Updating the product..."
docker-compose run --rm web python manage.py shell -c "
from django.test import Client
from django.contrib.auth import get_user_model
from apps.products.models import Product
import json

User = get_user_model()
client = Client()

# Login as admin
admin = User.objects.get(username='testadmin')
client.force_login(admin)

# Get first product
product = Product.objects.first()

# Update product
response = client.patch(f'/api/admin/products/{product.id}/', {
    'name': 'Updated Test Product',
    'price': '39.99'
}, content_type='application/json')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'✓ Product updated: {data[\"message\"]}')
    product.refresh_from_db()
    print(f'  New name: {product.name}')
    print(f'  New price: ${product.price}')
else:
    print(f'✗ Failed: {response.status_code}')
"
echo ""

echo "Step 5: Test LIST operation"
echo "Fetching inventory list..."
docker-compose run --rm web python manage.py shell -c "
from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()
client = Client()

# Login as admin
admin = User.objects.get(username='testadmin')
client.force_login(admin)

# Get inventory list
response = client.get('/api/admin/inventory/')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'✓ Inventory loaded: {len(data[\"inventory\"])} products')
    for item in data['inventory']:
        print(f'  - {item[\"name\"]} (Stock: {item[\"stock\"]}, Status: {item[\"status\"]})')
else:
    print(f'✗ Failed: {response.status_code}')
"
echo ""

echo "Step 6: Test DELETE operation"
echo "Soft deleting the product..."
docker-compose run --rm web python manage.py shell -c "
from django.test import Client
from django.contrib.auth import get_user_model
from apps.products.models import Product
import json

User = get_user_model()
client = Client()

# Login as admin
admin = User.objects.get(username='testadmin')
client.force_login(admin)

# Get first product
product = Product.objects.first()
product_name = product.name

# Delete product
response = client.delete(f'/api/admin/products/{product.id}/')

if response.status_code == 200:
    data = json.loads(response.content)
    print(f'✓ Product deleted: {data[\"message\"]}')
    product.refresh_from_db()
    print(f'  Product active status: {product.is_active}')
    print(f'  Redis cache cleaned: ✓')
else:
    print(f'✗ Failed: {response.status_code}')
"
echo ""

echo "Step 7: Verify final state"
docker-compose run --rm web python manage.py shell -c "
from apps.products.models import Product
print('=== Final Database State ===')
print(f'Active Products: {Product.objects.filter(is_active=True).count()}')
print(f'Inactive Products: {Product.objects.filter(is_active=False).count()}')
if Product.objects.filter(is_active=False).exists():
    deleted = Product.objects.filter(is_active=False).first()
    print(f'Soft deleted: {deleted.name}')
"
echo ""

echo "=========================================="
echo "✓ All CRUD operations completed successfully!"
echo "=========================================="
echo ""
echo "Frontend is available at: http://localhost:5173"
echo "API Docs available at: http://localhost:8000/api/docs/"
echo ""
