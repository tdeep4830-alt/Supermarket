"""
Delivery Services (Write Operations).

Ref: .blueprint/code_structure.md §2
Ref: .blueprint/data.md §3 - Delivery Slot Management
Ref: .blueprint/data.md §5 - Transaction Safety

Services for managing delivery slots with high concurrency support.
"""

import logging
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from django.db import transaction, models
from django.db.models import F
from django.utils import timezone

from apps.delivery.models import DeliverySlot, DeliverySlotException

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from apps.orders.models import Order

logger = logging.getLogger(__name__)

# =============================================================================
# Custom Exceptions
# =============================================================================


class DeliverySlotError(Exception):
    """Base exception for delivery slot errors."""
    pass


class DeliverySlotFullError(DeliverySlotError):
    """Raised when attempting to reserve a full slot."""
    pass


class DeliverySlotNotFoundError(DeliverySlotError):
    """Raised when slot is not found."""
    pass


class DeliverySlotExpiredError(DeliverySlotError):
    """Raised when slot date/time has passed."""
    pass


# =============================================================================
# Delivery Slot Services
# =============================================================================


@transaction.atomic
def reserve_slot(
    slot_id: UUID,
    order_id: UUID,
    admin_user: "AbstractUser",
) -> dict[str, object]:
    """
    Reserve a delivery slot for an order.

    Uses Django F() expressions for atomic increment to handle high concurrency.
    This ensures we don't over-book slots even with multiple simultaneous requests.

    Ref: .blueprint/data.md §3A - Delivery Slot Requirement
    Ref: .blueprint/data.md §5 - Transaction Safety

    Args:
        slot_id: UUID of the delivery slot to reserve
        order_id: UUID of the order reserving the slot
        admin_user: User making the reservation (for logging)

    Returns:
        Dict containing reservation result

    Raises:
        DeliverySlotFullError: If slot is full
        DeliverySlotNotFoundError: If slot doesn't exist
        DeliverySlotExpiredError: If slot date/time has passed
    """
    try:
        # Lock the slot row for update to prevent race conditions
        slot = DeliverySlot.objects.select_for_update().get(id=slot_id)
    except DeliverySlot.DoesNotExist:
        logger.warning(
            "Delivery slot not found",
            extra={"extra_data": {"slot_id": str(slot_id), "order_id": str(order_id)}},
        )
        raise DeliverySlotNotFoundError("Delivery slot not found")

    # Check if slot has expired
    if slot.has_passed:
        logger.warning(
            "Attempted to reserve expired slot",
            extra={
                "extra_data": {
                    "slot_id": str(slot.id),
                    "slot_date": str(slot.date),
                    "slot_time": slot.start_time.isoformat(),
                    "order_id": str(order_id),
                }
            },
        )
        raise DeliverySlotExpiredError("Delivery slot has expired")

    # Check if slot is full before attempting reservation
    if slot.is_full:
        logger.warning(
            "Attempted to reserve full slot",
            extra={
                "extra_data": {
                    "slot_id": str(slot.id),
                    "current_count": slot.current_count,
                    "max_capacity": slot.max_capacity,
                    "order_id": str(order_id),
                }
            },
        )
        raise DeliverySlotFullError("Delivery slot is full")

    # Atomic increment using F() expression to handle high concurrency
    # This ensures current_count is updated atomically without race conditions
    updated = DeliverySlot.objects.filter(
        id=slot_id,
        current_count__lt=F("max_capacity"),  # Double-check capacity
    ).update(current_count=F("current_count") + 1)

    if not updated:
        # Another request may have filled the slot just now
        logger.warning(
            "Delivery slot reservation conflict detected",
            extra={
                "extra_data": {
                    "slot_id": str(slot.id),
                    "order_id": str(order_id),
                }
            },
        )
        raise DeliverySlotFullError("Delivery slot just became full")

    # Refetch the slot to get updated count
    slot.refresh_from_db()

    logger.info(
        "delivery_slot_reserved",
        extra={
            "extra_data": {
                "slot_id": str(slot.id),
                "date": str(slot.date),
                "start_time": slot.start_time.isoformat(),
                "order_id": str(order_id),
                "admin_user_id": str(admin_user.id),
                "new_count": slot.current_count,
                "max_capacity": slot.max_capacity,
            }
        },
    )

    return {
        "success": True,
        "slot_id": slot.id,
        "new_count": slot.current_count,
        "available_count": slot.available_count,
    }


@transaction.atomic
def release_slot(
    slot_id: UUID, order_id: UUID, admin_user: "AbstractUser"
) -> dict[str, object]:
    """
    Release a delivery slot when an order is cancelled.

    Automatically recovers the slot by decrementing current_count.
    Uses F() expression for atomic operation to ensure accuracy.

    Args:
        slot_id: UUID of the delivery slot to release
        order_id: UUID of the order cancelling the slot
        admin_user: User making the release (for logging)

    Returns:
        Dict containing release result

    Raises:
        DeliverySlotNotFoundError: If slot doesn't exist

    Ref: Requirement - 訂單取消時時段能自動回收
    """
    try:
        slot = DeliverySlot.objects.select_for_update().get(id=slot_id)
    except DeliverySlot.DoesNotExist:
        logger.warning(
            "Delivery slot not found for release",
            extra={"extra_data": {"slot_id": str(slot_id), "order_id": str(order_id)}},
        )
        raise DeliverySlotNotFoundError("Delivery slot not found")

    # Atomic decrement using F() expression
    DeliverySlot.objects.filter(id=slot_id, current_count__gt=0).update(
        current_count=F("current_count") - 1
    )

    slot.refresh_from_db()

    logger.info(
        "delivery_slot_released",
        extra={
            "extra_data": {
                "slot_id": str(slot.id),
                "order_id": str(order_id),
                "admin_user_id": str(admin_user.id),
                "new_count": slot.current_count,
            }
        },
    )

    return {
        "success": True,
        "slot_id": slot.id,
        "new_count": slot.current_count,
        "available_count": slot.available_count,
    }


@transaction.atomic
def emergency_block_slot(
    slot_id: UUID, admin_user: "AbstractUser", reason: str = "Emergency"
) -> dict[str, object]:
    """
    Emergency block a delivery slot (admin only).

    Allows administrators to immediately block a slot from further reservations.
    Useful for emergencies, vehicle breakdowns, or other issues.

    Args:
        slot_id: UUID of the slot to block
        admin_user: Admin user performing the block
        reason: Reason for emergency block

    Returns:
        Dict containing block result

    Raises:
        DeliverySlotNotFoundError: If slot doesn't exist

    Ref: Requirement - Admin 端增加一個『緊急下架時段』的按鈕
    """
    try:
        slot = DeliverySlot.objects.select_for_update().get(id=slot_id)
    except DeliverySlot.DoesNotExist:
        logger.error(
            "Delivery slot not found for emergency block",
            extra={"extra_data": {"slot_id": str(slot_id)}},
        )
        raise DeliverySlotNotFoundError("Delivery slot not found")

    # Deactivate the slot
    slot.is_active = False
    slot.save()

    logger.warning(
        "delivery_slot_emergency_blocked",
        extra={
            "extra_data": {
                "slot_id": str(slot.id),
                "date": str(slot.date),
                "start_time": slot.start_time.isoformat(),
                "admin_user_id": str(admin_user.id),
                "reason": reason,
                "current_count": slot.current_count,
            }
        },
    )

    return {
        "success": True,
        "slot_id": slot.id,
        "status": "blocked",
        "reason": reason,
    }


@transaction.atomic
def batch_create_slots(
    start_date: date,
    days: int = 7,
    time_slots: Optional[list[tuple[str, str]]] = None,
    capacity: int = 10,
    admin_user: Optional["AbstractUser"] = None,
) -> list[dict[str, object]]:
    """
    Batch create delivery slots for store owners.

    Creates multiple delivery slots for upcoming days with specified time windows.
    Useful for store owners to quickly set up weekly delivery schedules.

    Args:
        start_date: Starting date for slot creation
        days: Number of days to create slots for (default: 7)
        time_slots: List of (start_time, end_time) tuples. If None, uses default slots
        capacity: Maximum capacity for each slot (default: 10)
        admin_user: Admin user creating the slots (for logging)

    Returns:
        List of created slot dictionaries

    Example:
        batch_create_slots(
            start_date=date(2026, 1, 15),
            days=7,
            time_slots=[("09:00", "12:00"), ("14:00", "17:00"), ("18:00", "21:00")],
            capacity=15
        )
    """
    if time_slots is None:
        # Default time slots: 9am-12pm, 2pm-5pm, 6pm-9pm
        time_slots = [
            ("09:00", "12:00"),
            ("14:00", "17:00"),
            ("18:00", "21:00"),
        ]

    created_slots = []

    for i in range(days):
        slot_date = start_date + timedelta(days=i)

        # Skip days with exceptions (e.g., holidays)
        if DeliverySlotException.objects.filter(
            date=slot_date, is_blocked=True
        ).exists():
            logger.warning(
                "Skipping slot creation for blocked date",
                extra={"extra_data": {"date": str(slot_date)}},
            )
            continue

        for start_str, end_str in time_slots:
            start_time = time.fromisoformat(start_str)
            end_time = time.fromisoformat(end_str)

            # Create or get the slot
            slot, created = DeliverySlot.objects.get_or_create(
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                defaults={
                    "max_capacity": capacity,
                    "current_count": 0,
                    "is_active": True,
                },
            )

            if created:
                created_slots.append(
                    {
                        "id": str(slot.id),
                        "date": str(slot.date),
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "max_capacity": capacity,
                    }
                )
                logger.info(
                    "delivery_slot_batch_created",
                    extra={
                        "extra_data": {
                            "slot_id": str(slot.id),
                            "date": str(slot.date),
                            "start_time": start_time.isoformat(),
                            "capacity": capacity,
                            "admin_user_id": str(admin_user.id) if admin_user else None,
                        }
                    },
                )

    return created_slots

