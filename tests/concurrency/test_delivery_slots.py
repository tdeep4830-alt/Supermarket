"""
Delivery Slot Concurrency Tests.

Ref: .blueprint/code_structure.md §5 - Concurrency Tests
Ref: .blueprint/data.md §5 - Transaction Safety

Verifies that concurrent bookings never exceed max_capacity.
Uses threading to simulate multiple simultaneous reserve_slot calls.
"""
import threading
from datetime import date, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from apps.delivery.models import DeliverySlot
from apps.delivery.services import (
    DeliverySlotFullError,
    reserve_slot,
)

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user for slot reservation."""
    return User.objects.create_superuser(
        username="slot_admin",
        email="slot_admin@test.local",
        password="AdminPass123!",
    )


@pytest.fixture
def delivery_slot(db) -> DeliverySlot:
    """Create a delivery slot with capacity 10."""
    tomorrow = date.today() + timedelta(days=1)
    return DeliverySlot.objects.create(
        date=tomorrow,
        start_time=time(9, 0),
        end_time=time(12, 0),
        max_capacity=10,
        current_count=0,
        is_active=True,
    )


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
class TestDeliverySlotConcurrency:
    """Concurrent delivery slot reservation tests."""

    def test_concurrent_reserve_no_overbooking(self, delivery_slot, admin_user):
        """
        Launch 20 threads each trying to reserve the same slot.
        Capacity is 10 → exactly 10 should succeed, 10 should fail.
        current_count must never exceed max_capacity.

        Ref: code_structure.md §5 - 搶購併發測試
        """
        import uuid

        num_threads = 20
        success_count = 0
        failure_count = 0
        lock = threading.Lock()

        def reserve_task():
            nonlocal success_count, failure_count
            fake_order_id = uuid.uuid4()
            try:
                reserve_slot(
                    slot_id=delivery_slot.id,
                    order_id=fake_order_id,
                    admin_user=admin_user,
                )
                with lock:
                    success_count += 1
            except (DeliverySlotFullError, Exception):
                with lock:
                    failure_count += 1
            finally:
                connection.close()

        threads = [threading.Thread(target=reserve_task) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Refresh from DB
        delivery_slot.refresh_from_db()

        # Exactly 10 should succeed (capacity = 10)
        assert success_count == 10, (
            f"Expected 10 successes, got {success_count}"
        )
        assert failure_count == 10, (
            f"Expected 10 failures, got {failure_count}"
        )
        # current_count must equal max_capacity
        assert delivery_slot.current_count == delivery_slot.max_capacity
        # Absolute safety: never negative, never over capacity
        assert 0 <= delivery_slot.current_count <= delivery_slot.max_capacity

    def test_concurrent_reserve_partial_capacity(self, delivery_slot, admin_user):
        """
        Pre-fill 7 of 10 slots, then launch 10 threads.
        Only 3 should succeed.
        """
        import uuid

        # Pre-fill
        delivery_slot.current_count = 7
        delivery_slot.save()

        num_threads = 10
        success_count = 0
        failure_count = 0
        lock = threading.Lock()

        def reserve_task():
            nonlocal success_count, failure_count
            fake_order_id = uuid.uuid4()
            try:
                reserve_slot(
                    slot_id=delivery_slot.id,
                    order_id=fake_order_id,
                    admin_user=admin_user,
                )
                with lock:
                    success_count += 1
            except (DeliverySlotFullError, Exception):
                with lock:
                    failure_count += 1
            finally:
                connection.close()

        threads = [threading.Thread(target=reserve_task) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        delivery_slot.refresh_from_db()

        assert success_count == 3, (
            f"Expected 3 successes (10-7), got {success_count}"
        )
        assert failure_count == 7
        assert delivery_slot.current_count == 10
        assert delivery_slot.current_count <= delivery_slot.max_capacity
