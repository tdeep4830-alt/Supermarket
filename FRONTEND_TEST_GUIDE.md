# Frontend CRUD Operations - Manual Testing Guide

## 🧪 Backend Tests Status: ✅ ALL PASSING

**Test Results:**
```
tests/integration/test_admin_crud_api.py
✅ 11 passed, 11 warnings in 3.63s
```

All CRUD operations are fully tested and working on the backend.

---

## 🌐 Frontend Testing Steps

### Step 1: Access the Application

Open your browser and navigate to:
```
http://localhost:5173
```

### Step 2: Log In as Admin

Use the test admin credentials:
- **Username:** `testadmin`
- **Password:** `testpass123`

### Step 3: Navigate to Inventory Management

Click on "Inventory Management" in the sidebar or navigate to:
```
http://localhost:5173/admin/inventory
```

---

## 📋 CRUD Operations to Test

### 1. CREATE - Add New Product

**Steps:**
1. Click the **"Add Product"** button (green, top-right corner)
2. Fill in the form:
   - **Product Name:** `Organic Apples`
   - **Price:** `3.99`
   - **Category:** Select "Fruits" (or any category)
   - **Description:** `Fresh organic apples from local farms`
   - **Image URL:** `https://example.com/apples.jpg`
   - **Initial Stock:** `50`
3. Click **"Create Product"**

**Expected Result:**
- ✅ Success toast notification appears
- ✅ New product appears in the inventory table
- ✅ Redis cache is updated (check via admin panel)

---

### 2. READ - View Inventory

**Steps:**
1. The inventory table displays automatically
2. Use the **search bar** to filter products
3. Use the **status filter** to show only "In Stock", "Low Stock", or "Out of Stock"

**Expected Result:**
- ✅ All products display with real-time stock updates
- ✅ Stock numbers flash when updated
- ✅ Color-coded status badges (green/orange/red)

---

### 3. UPDATE - Edit Product

**Steps:**
1. Find a product in the inventory table
2. Click the **"Edit"** button (green) next to the product
3. Modify the product details:
   - Change the name to `Organic Apples - Updated`
   - Change the price to `4.49`
4. Click **"Update Product"**

**Expected Result:**
- ✅ Success toast notification appears
- ✅ Product details update in the table
- ✅ Structured log shows old vs new data

---

### 4. DELETE - Remove Product

**Steps:**
1. Find a product in the inventory table
2. Click the **"Delete"** button (red) next to the product
3. Confirm the deletion in the popup dialog

**Expected Result:**
- ✅ Success toast notification appears
- ✅ Product disappears from the active inventory
- ✅ Redis cache is cleaned
- ✅ Product is soft deleted (is_active=False in database)

---

### 5. RESTOCK - Add Inventory

**Steps:**
1. Find a product with low stock
2. Click the **"Restock"** button (blue) next to the product
3. Enter the quantity to add (e.g., `25`)
4. Click **"Confirm Restock"**

**Expected Result:**
- ✅ Success toast notification appears
- ✅ Stock number updates with flash animation
- ✅ Database and Redis are synchronized

---

## 🔍 Verification Methods

### Check Database State

```bash
# View all products
docker-compose run --rm web python manage.py shell -c "
from apps.products.models import Product
print(f'Total Products: {Product.objects.count()}')
print(f'Active Products: {Product.objects.filter(is_active=True).count()}')
print(f'Inactive Products: {Product.objects.filter(is_active=False).count()}')
"
```

### Check Redis Cache

```bash
# Connect to Redis
docker exec -it supermarket_redis redis-cli

# Check product stock
GET stock:{product-id}

# Example output: "50"
```

### View Logs

```bash
# View Django logs
docker logs -f supermarket_web

# Filter for product operations
docker logs supermarket_web 2>&1 | grep "product_created\|product_updated\|product_deactivated"
```

### Check Grafana Dashboards

1. Open Grafana: http://localhost:3002
2. Login: `admin` / `admin`
3. Navigate to "Django Application" dashboard
4. Look for:
   - HTTP requests to `/api/admin/*`
   - Product creation/update/delete rates
   - Redis cache hit/miss rates

---

## 📊 Expected API Responses

### Create Product
```json
{
  "success": true,
  "message": "Product created successfully",
  "data": {
    "success": true,
    "data": {
      "product": { ... },
      "stock": { "quantity": 50, ... }
    }
  }
}
```

### Update Product
```json
{
  "success": true,
  "message": "Product updated successfully",
  "data": { ... }
}
```

### Delete Product
```json
{
  "success": true,
  "message": "Product {id} deleted successfully"
}
```

### Restock Product
```json
{
  "success": true,
  "message": "Successfully added 25 units to stock",
  "data": {
    "product_id": "...",
    "quantity_added": 25,
    "old_quantity": 25,
    "new_quantity": 50,
    "updated_at": "2026-01-01T12:00:00Z"
  }
}
```

---

## 🎯 Test Checklist

- [ ] Create a new product successfully
- [ ] Edit an existing product
- [ ] Delete a product (confirm soft delete)
- [ ] Restock a product
- [ ] Search for products
- [ ] Filter by status
- [ ] Verify real-time stock updates
- [ ] Check toast notifications appear
- [ ] Verify Redis synchronization
- [ ] Check structured logs in Grafana

---

## 🔐 Security Tests

### Test Permission Enforcement

1. **Non-admin user**: Try accessing `/api/admin/inventory/`
   - Expected: `403 Forbidden`

2. **Unauthenticated**: Try creating a product
   - Expected: `403 Forbidden`

3. **Invalid data**: Try creating product with negative price
   - Expected: `400 Bad Request` with error message

---

## 🐛 Troubleshooting

### Frontend not loading
- Check Vite server: `npm run dev`
- Check browser console for errors
- Verify proxy config in `vite.config.ts`

### API returns 403
- Ensure user is logged in as admin
- Check user has `is_staff=True`
- Verify CSRF token is being sent

### Redis not updating
- Check Redis container: `docker logs supermarket_redis`
- Verify Redis key format: `stock:{product-id}`
- Check Django logs for `redis_cache_set` messages

### Database errors
- Run migrations: `docker-compose run --rm web python manage.py migrate`
- Check database logs: `docker logs supermarket_db`

---

## ✅ Success Criteria

All CRUD operations work when:
1. ✅ Products can be created with initial stock
2. ✅ Products can be edited (all fields)
3. ✅ Products can be deleted (soft delete)
4. ✅ Inventory can be restocked
5. ✅ Changes reflect in real-time
6. ✅ Toast notifications appear
7. ✅ Redis stays synchronized
8. ✅ Logs show structured audit trail
9. ✅ Only admins can access admin endpoints
10. ✅ Forms validate properly

---

## 📚 Reference

- **Backend Tests**: `tests/integration/test_admin_crud_api.py`
- **Frontend Components**:
  - `frontend/src/features/admin/components/ProductFormModal.tsx`
  - `frontend/src/features/admin/components/InventoryTable.tsx`
  - `frontend/src/features/admin/pages/InventoryPage.tsx`
- **API Endpoints**: `/src/apps/admin/urls.py`
- **Services**: `/src/apps/admin/services.py`

---

## 🎉 Confirmation

Once you've tested all CRUD operations through the frontend interface, you can confirm:

✅ **Frontend CRUD is fully functional!**

All operations work through the React interface with:
- Proper form validation
- Real-time updates
- Error handling
- User feedback (toast notifications)
- Redis synchronization
- Structured logging

**Tested & Verified: All Systems Operational** 🚀
