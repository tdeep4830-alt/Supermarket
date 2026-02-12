"""
Stock Concurrency Tests.

Ref: .blueprint/code_sturcture.md §5
測試搶購鎖機制，驗證無超賣。
"""
import threading
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.products.models import Category, Product, Stock
from apps.products.services import decrease_stock, restore_stock

User = get_user_model()


@pytest.fixture
def category(db):
    """Create test category."""
    return Category.objects.create(
        name="Test Category",
        slug="test-category",
    )


@pytest.fixture
def product(db, category):
    """Create test product."""
    return Product.objects.create(
        category=category,
        name="Test Product",
        price=Decimal("99.99"),
    )


@pytest.fixture
def stock(db, product):
    """Create test stock with 100 units."""
    return Stock.objects.create(
        product=product,
        quantity=100,
    )


@pytest.mark.django_db(transaction=True)
class TestDecreaseStock:
    """Test decrease_stock service."""

    def test_decrease_stock_success(self, stock):
        """Test successful stock decrease."""
        result = decrease_stock(stock.product_id, 10, use_redis=False)

        assert result is True
        stock.refresh_from_db()
        assert stock.quantity == 90
        assert stock.version == 1

    def test_decrease_stock_insufficient(self, stock):
        """Test stock decrease with insufficient quantity."""
        from common.exceptions import InsufficientStockException

        with pytest.raises(InsufficientStockException):
            decrease_stock(stock.product_id, 150, use_redis=False)

        stock.refresh_from_db()
        assert stock.quantity == 100  # Unchanged

    def test_decrease_stock_concurrent_no_oversell(self, stock):
        """
        Test concurrent stock decrease - NO OVERSELL.

        Ref: code_sturcture.md §5
        啟動多個 Thread 同時扣減，驗證最後庫存正確且無負數。
        """
        from django.db import connection

        num_threads = 20
        quantity_per_thread = 10  # Total: 200, Stock: 100
        success_count = 0
        failure_count = 0
        lock = threading.Lock()

        def decrease_task():
            nonlocal success_count, failure_count
            try:
                decrease_stock(stock.product_id, quantity_per_thread, use_redis=False)
                with lock:
                    success_count += 1
            except Exception:
                with lock:
                    failure_count += 1
            finally:
                # Close the database connection for this thread
                connection.close()

        # Create and start threads
        threads = [threading.Thread(target=decrease_task) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify results
        stock.refresh_from_db()

        # 最多成功 10 次（100 / 10 = 10）
        assert success_count == 10
        assert failure_count == 10
        assert stock.quantity == 0
        assert stock.quantity >= 0  # 絕對不能為負數


class TestRestoreStock:
    """Test restore_stock service."""

    def test_restore_stock_success(self, stock):
        """Test successful stock restore."""
        # First decrease
        decrease_stock(stock.product_id, 50, use_redis=False)

        # Then restore
        result = restore_stock(stock.product_id, 30, use_redis=False)

        assert result is True
        stock.refresh_from_db()
        assert stock.quantity == 80


class TestStockWithRedis:
    """Test stock operations with Redis."""

    @patch("apps.products.services.cache")
    def test_decrease_stock_with_redis(self, mock_cache, stock):
        """Test stock decrease with Redis caching."""
        mock_cache.get.return_value = 100
        mock_cache.decr.return_value = 90

        result = decrease_stock(stock.product_id, 10, use_redis=True)

        assert result is True
        mock_cache.decr.assert_called_once()

    @patch("apps.products.services.cache")
    def test_decrease_stock_redis_rollback_on_db_failure(self, mock_cache, stock):
        """Test Redis rollback when DB update fails."""
        from common.exceptions import InsufficientStockException

        mock_cache.get.return_value = 100
        mock_cache.decr.return_value = 90

        # Request more than available in DB
        with pytest.raises(InsufficientStockException):
            decrease_stock(stock.product_id, 150, use_redis=True)

        # Redis should be rolled back
        mock_cache.incr.assert_called()
