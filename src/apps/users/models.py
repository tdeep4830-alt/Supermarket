"""
User Models.

Ref: .blueprint/auth.md §2A (Custom User Model)
Ref: .blueprint/data.md §1D (Cart)
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class MembershipTier(models.TextChoices):
    """會員等級 (Ref: auth.md §2A)"""
    REGULAR = "REGULAR", "Regular"
    GOLD = "GOLD", "Gold"
    PLATINUM = "PLATINUM", "Platinum"


class User(AbstractUser):
    """
    Custom User Model (Ref: auth.md §2A).

    Extends Django's AbstractUser with additional fields:
    - phone: Optional phone number (unique)
    - is_verified: Whether phone/email is verified
    - avatar_url: User avatar URL
    - membership_tier: REGULAR, GOLD, PLATINUM
    """

    # Override id to use UUID (Ref: data.md §4)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Extended fields (Ref: auth.md §2A)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="User phone number (optional, unique)",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether phone/email has been verified",
    )
    avatar_url = models.URLField(
        blank=True,
        null=True,
        help_text="User avatar URL",
    )
    membership_tier = models.CharField(
        max_length=10,
        choices=MembershipTier.choices,
        default=MembershipTier.REGULAR,
        help_text="Membership tier: REGULAR, GOLD, PLATINUM",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.username
