"""
Delivery Models.

Ref: .blueprint/code_structure.md §1
- DeliverySlot (time slot management)

Delivery slot management system for scheduling deliveries
with capacity control and high concurrency handling.
"""

import uuid
from datetime import time

from django.db import models
from django.utils import timezone


class DeliverySlot(models.Model):
    """
    Delivery Slot Model.

    Represents a time window for deliveries with capacity control.
    Each slot has a maximum capacity and tracks current bookings.

    Attributes:
        date: Delivery date
        start_time: Start time of delivery window
        end_time: End time of delivery window
        max_capacity: Maximum number of orders for this slot
        current_count: Current number of booked orders
        is_active: Whether this slot is available for booking

    Example:
        date: 2026-01-15
        start_time: 09:00
        end_time: 12:00
        max_capacity: 20 (max 20 orders)
        current_count: 8 (8 orders booked)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(help_text="Delivery date")
    start_time = models.TimeField(help_text="Start time of delivery window")
    end_time = models.TimeField(help_text="End time of delivery window")
    max_capacity = models.IntegerField(
        help_text="Maximum number of orders for this slot"
    )
    current_count = models.IntegerField(
        default=0, help_text="Current number of booked orders"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this slot is available for booking"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delivery_slots"
        ordering = ["date", "start_time"]
        unique_together = [["date", "start_time", "end_time"]]
        indexes = [
            models.Index(fields=["date", "start_time"]),
            models.Index(fields=["is_active", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.start_time}-{self.end_time} ({self.current_count}/{self.max_capacity})"

    @property
    def is_full(self) -> bool:
        """Check if the slot is fully booked."""
        return self.current_count >= self.max_capacity

    @property
    def is_almost_full(self) -> bool:
        """Check if the slot is almost full (80% capacity)."""
        return self.current_count >= (self.max_capacity * 0.8)

    @property
    def available_count(self) -> int:
        """Get remaining available capacity."""
        return max(0, self.max_capacity - self.current_count)

    @property
    def has_passed(self) -> bool:
        """Check if this slot date and time has passed."""
        from datetime import datetime

        # Get the current time in the default timezone
        now = timezone.now()

        # Create a timezone-aware datetime for the slot in the same timezone as now
        slot_datetime = timezone.make_aware(
            datetime.combine(self.date, self.start_time),
            now.tzinfo  # Use the same timezone as now()
        )

        return slot_datetime < now


class DeliverySlotException(models.Model):
    """
    Delivery Slot Exception.

    For blocking specific dates (e.g., holidays, emergencies).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(help_text="Date to block deliveries")
    reason = models.CharField(max_length=200, help_text="Reason for blocking")
    is_blocked = models.BooleanField(
        default=True, help_text="Whether deliveries are blocked on this date"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "delivery_slot_exceptions"
        unique_together = [["date"]]

    def __str__(self) -> str:
        return f"{self.date} - {self.reason}"
