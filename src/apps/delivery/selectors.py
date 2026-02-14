"""
Delivery Selectors (Read Operations).

Ref: .blueprint/code_structure.md §2
Ref: .blueprint/data.md §3 - Delivery Slot Management

Selectors for querying delivery slots with business logic applied.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.delivery.models import DeliverySlot, DeliverySlotException


def get_available_slots(start_date: date | None = None, days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Get available delivery slots for the next N days.

    Returns slots that:
    1. Are in the next `days_ahead` days (default: 7)
    2. Are active
    3. Are not full
    4. Are not blocked by exceptions
    5. Filter out today's past times

    Args:
        start_date: Date to start from (default: today)
        days_ahead: Number of days to look ahead (default: 7)

    Returns:
        List of available slot dictionaries, sorted by date and time

    Ref: Delivery Slot Management - Requirement §3A
    """
    if start_date is None:
        start_date = timezone.now().date()

    # Calculate end date
    end_date = start_date + timedelta(days=days_ahead)

    # Get blocked dates
    blocked_dates = set(
        DeliverySlotException.objects.filter(
            is_blocked=True,
            date__range=[start_date, end_date]
        ).values_list("date", flat=True)
    )

    # Get current time for today's filtering
    now = timezone.now()
    current_time = now.time()

    # Build query for available slots
    queryset = DeliverySlot.objects.filter(
        date__range=[start_date, end_date],
        is_active=True,
        current_count__lt=models.F("max_capacity"),
    ).order_by("date", "start_time")

    # Filter results
    available_slots = []
    for slot in queryset:
        # Skip blocked dates
        if slot.date in blocked_dates:
            continue

        # Skip today's past times
        if slot.date == start_date and slot.start_time < current_time:
            continue

        # Skip passed slots
        if slot.has_passed:
            continue

        available_slots.append(
            {
                "id": str(slot.id),
                "date": slot.date.isoformat(),
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "max_capacity": slot.max_capacity,
                "current_count": slot.current_count,
                "available_count": slot.available_count,
                "is_almost_full": slot.is_almost_full,
            }
        )

    return available_slots


def get_slot_by_id(slot_id: str) -> DeliverySlot | None:
    """
    Get a delivery slot by ID.

    Args:
        slot_id: UUID string of the slot

    Returns:
        DeliverySlot object or None if not found
    """
    try:
        return DeliverySlot.objects.get(id=slot_id)
    except DeliverySlot.DoesNotExist:
        return None


def get_upcoming_slots(days: int = 7, include_inactive: bool = False) -> List[DeliverySlot]:
    """
    Get all upcoming slots (including full ones) for admin view.

    Args:
        days: Number of days to look ahead
        include_inactive: Whether to include inactive slots (admin only)

    Returns:
        List of DeliverySlot objects
    """
    today = timezone.now().date()
    end_date = today + timedelta(days=days)

    queryset = DeliverySlot.objects.filter(
        date__range=[today, end_date]
    ).order_by("date", "start_time")

    if not include_inactive:
        queryset = queryset.filter(is_active=True)

    return list(queryset)

