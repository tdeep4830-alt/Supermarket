"""
Integration tests for Delivery Slot Management System.

Tests cover:
- Model functionality
- Selectors (get_available_slots)
- Services (reserve_slot, release_slot, batch_create)
- API endpoints
- High concurrency scenarios

Ref: .blueprint/infra.md §7 - Automated Testing
"""

import pytest
from datetime import date, timedelta, datetime, time
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.delivery.models import DeliverySlot, DeliverySlotException
from apps.delivery import services, selectors

User = get_user_model()

pytestmark = pytest.mark.django_db


# Fixtures
@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        username="admin_test",
        email="admin@test.com",
        password="adminpass123",
        is_staff=True
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user."""
    return User.objects.create_user(
        username="user_test",
        email="user@test.com",
        password="userpass123",
    )


@pytest.fixture
def delivery_slot(db):
    """Create a delivery slot."""
    tomorrow = timezone.now().date() + timedelta(days=1)
    return DeliverySlot.objects.create(
        date=tomorrow,
        start_time=time(9, 0),
        end_time=time(12, 0),
        max_capacity=10,
        current_count=0,
    )


@pytest.fixture
def blocked_date(db):
    """Create a blocked date."""
    return DeliverySlotException.objects.create(
        date=timezone.now().date() + timedelta(days=3),
        reason="Holiday",
        is_blocked=True
    )


# Model tests
class TestDeliverySlotModel:
    """Test DeliverySlot model properties and methods."""

    def test_is_full_property(self, delivery_slot):
        """Test is_full property."""
        assert not delivery_slot.is_full

        delivery_slot.current_count = 10
        delivery_slot.save()
        assert delivery_slot.is_full

    def test_is_almost_full_property(self, delivery_slot):
        """Test is_almost_full property (80% threshold)."""
        assert not delivery_slot.is_almost_full

        delivery_slot.current_count = 8  # 80% of 10
        delivery_slot.save()
        assert delivery_slot.is_almost_full

    def test_available_count_property(self, delivery_slot):
        """Test available_count property."""
        assert delivery_slot.available_count == 10

        delivery_slot.current_count = 3
        delivery_slot.save()
        assert delivery_slot.available_count == 7

    def test_has_passed_property(self, delivery_slot):
        """Test has_passed property filters past times."""
        # Past slot
        delivery_slot.date = timezone.now().date() - timedelta(days=1)
        delivery_slot.save()
        assert delivery_slot.has_passed

        # Future slot
        delivery_slot.date = timezone.now().date() + timedelta(days=1)
        delivery_slot.save()
        assert not delivery_slot.has_passed


# Selector tests
class TestGetAvailableSlotsSelector:
    """Test get_available_slots selector."""

    def test_returns_future_slots_only(self):
        """Ensure only future slots are returned."""
        today = timezone.now().date()

        # Create past slot
        DeliverySlot.objects.create(
            date=today - timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(12, 0),
            max_capacity=10,
        )

        # Create future slot
        future_slot = DeliverySlot.objects.create(
            date=today + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(12, 0),
            max_capacity=10,
        )

        slots = selectors.get_available_slots()

        assert len(slots) == 1
        assert slots[0]["id"] == str(future_slot.id)

    def test_filters_blocked_dates(self, blocked_date):
        """Test that blocked dates are filtered out."""
        # Create slot on blocked date
        DeliverySlot.objects.create(
            date=blocked_date.date,
            start_time=time(9, 0),
            end_time=time(12, 0),
            max_capacity=10,
        )

        slots = selectors.get_available_slots()

        # Should not include slots on blocked dates
        assert not any(slot["date"] == blocked_date.date.isoformat() for slot in slots)

    def test_filters_full_slots(self, delivery_slot):
        """Test that full slots are filtered out."""
        delivery_slot.current_count = 10  # Make it full
        delivery_slot.save()

        slots = selectors.get_available_slots()

        assert len(slots) == 0

    def test_returns_only_active_slots(self, delivery_slot):
        """Test that only active slots are returned."""
        delivery_slot.is_active = False
        delivery_slot.save()

        slots = selectors.get_available_slots()

        assert len(slots) == 0

    def test_default_7_days_ahead(self):
        """Test default behavior returns 7 days ahead."""
        today = timezone.now().date()

        # Create slots for next 10 days
        for i in range(10):
            DeliverySlot.objects.create(
                date=today + timedelta(days=i),
                start_time=time(9, 0),
                end_time=time(12, 0),
                max_capacity=10,
            )

        slots = selectors.get_available_slots()

        # Should get exactly 7 days
        assert len(slots) == 7

    def test_custom_date_range(self):
        """Test custom date range parameter."""
        today = timezone.now().date()

        # Create slots for next 10 days
        for i in range(10):
            DeliverySlot.objects.create(
                date=today + timedelta(days=i),
                start_time=time(9, 0),
                end_time=time(12, 0),
                max_capacity=10,
            )

        slots = selectors.get_available_slots(start_date=today, days_ahead=5)

        assert len(slots) == 5

    def test_today_past_times_filtered(self):
        """Test that today's past times are filtered out."""
        now = timezone.now()
        current_time = now.time()

        # Create slot with start time in the past
        past_slot = DeliverySlot.objects.create(
            date=now.date(),
            start_time=time(current_time.hour - 1, 0),  # 1 hour ago
            end_time=time(current_time.hour, 0),
            max_capacity=10,
        )

        # Create slot with start time in the future
        future_slot = DeliverySlot.objects.create(
            date=now.date(),
            start_time=time(current_time.hour + 1, 0),  # 1 hour from now
            end_time=time(current_time.hour + 2, 0),
            max_capacity=10,
        )

        slots = selectors.get_available_slots()

        # Should only include future slot
        slot_ids = [slot["id"] for slot in slots]
        assert str(past_slot.id) not in slot_ids
        assert str(future_slot.id) in slot_ids


# Service tests
class TestReserveSlotService:
    """Test reserve_slot service."""

    def test_successful_reservation(self, delivery_slot, admin_user):
        """Test successful slot reservation."""
        result = services.reserve_slot(
            slot_id=delivery_slot.id,
            order_id="order-123",
            admin_user=admin_user
        )

        assert result["success"]
        assert result["slot_id"] == delivery_slot.id
        assert result["new_count"] == 1
        assert result["available_count"] == 9

        # Verify database update
        delivery_slot.refresh_from_db()
        assert delivery_slot.current_count == 1

    def test_concurrent_reservations_dont_exceed_capacity(self, delivery_slot, admin_user):
        """Test that concurrent reservations don't exceed capacity."""
        # Simulate 15 concurrent reservations for a slot with capacity 10
        successful = 0
        failed = 0

        from concurrent.futures import ThreadPoolExecutor

        def reserve_attempt(i):
            try:
                services.reserve_slot(
                    slot_id=delivery_slot.id,
                    order_id=f"order-{i}",
                    admin_user=admin_user
                )
                return True
            except services.DeliverySlotFullError:
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(reserve_attempt, range(15)))

        successful = sum(results)
        failed = len(results) - successful

        # Should allow exactly 10 successful reservations
        assert successful == 10
        assert failed == 5

        delivery_slot.refresh_from_db()
        assert delivery_slot.current_count == 10
        assert delivery_slot.is_full

    def test_reservation_fails_for_full_slot(self, delivery_slot, admin_user):
        """Test reservation fails when slot is full."""
        delivery_slot.current_count = 10
        delivery_slot.save()

        with pytest.raises(services.DeliverySlotFullError):
            services.reserve_slot(
                slot_id=delivery_slot.id,
                order_id="order-123",
                admin_user=admin_user
            )

    def test_reservation_fails_for_expired_slot(self, admin_user):
        """Test reservation fails for expired slot."""
        yesterday = timezone.now().date() - timedelta(days=1)
        expired_slot = DeliverySlot.objects.create(
            date=yesterday,
            start_time=time(9, 0),
            end_time=time(12, 0),
            max_capacity=10,
        )

        with pytest.raises(services.DeliverySlotExpiredError):
            services.reserve_slot(
                slot_id=expired_slot.id,
                order_id="order-123",
                admin_user=admin_user
            )


class TestReleaseSlotService:
    """Test release_slot service."""

    def test_slot_release_decrements_count(self, delivery_slot, admin_user):
        """Test releasing slot decrements current_count."""
        # First reserve
        services.reserve_slot(
            slot_id=delivery_slot.id,
            order_id="order-123",
            admin_user=admin_user
        )

        # Then release
        result = services.release_slot(
            slot_id=delivery_slot.id,
            order_id="order-123",
            admin_user=admin_user
        )

        assert result["success"]
        assert result["new_count"] == 0

        delivery_slot.refresh_from_db()
        assert delivery_slot.current_count == 0

    def test_release_cannot_go_below_zero(self, delivery_slot, admin_user):
        """Test release cannot make current_count negative."""
        # Try to release without reserving
        services.release_slot(
            slot_id=delivery_slot.id,
            order_id="order-123",
            admin_user=admin_user
        )

        delivery_slot.refresh_from_db()
        assert delivery_slot.current_count == 0


class TestBatchCreateSlotsService:
    """Test batch_create_slots service."""

    def test_creates_multiple_slots(self, admin_user):
        """Test batch creation creates multiple slots."""
        start_date = timezone.now().date() + timedelta(days=1)

        result = services.batch_create_slots(
            start_date=start_date,
            days=3,
            capacity=10,
            admin_user=admin_user
        )

        # Should create 3 days * 3 default slots = 9 slots
        assert len(result) == 9

        # Verify slots were created in database
        slots = DeliverySlot.objects.filter(date__gte=start_date)
        assert slots.count() == 9

    def test_custom_time_slots(self, admin_user):
        """Test batch creation with custom time slots."""
        start_date = timezone.now().date() + timedelta(days=1)
        custom_slots = [("10:00", "13:00"), ("15:00", "18:00")]

        result = services.batch_create_slots(
            start_date=start_date,
            days=2,
            time_slots=custom_slots,
            capacity=15,
            admin_user=admin_user
        )

        # Should create 2 days * 2 custom slots = 4 slots
        assert len(result) == 4

        # Verify capacity
        for slot_data in result:
            assert slot_data["max_capacity"] == 15


class TestEmergencyBlockSlot:
    """Test emergency_block_slot service."""

    def test_emergency_block_deactivates_slot(self, delivery_slot, admin_user):
        """Test emergency block deactivates slot."""
        result = services.emergency_block_slot(
            slot_id=delivery_slot.id,
            admin_user=admin_user,
            reason="Vehicle breakdown"
        )

        assert result["success"]
        assert result["status"] == "blocked"
        assert result["reason"] == "Vehicle breakdown"

        delivery_slot.refresh_from_db()
        assert not delivery_slot.is_active
