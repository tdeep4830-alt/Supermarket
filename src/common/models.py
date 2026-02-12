"""
Common Base Models for Online Supermarket.

Ref: .blueprint/data.md §1, §4
- All models must inherit TimeStampedModel
- ID must use UUID
"""
import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model providing:
    - UUID primary key (Ref: data.md §4)
    - Auto-updating created_at and updated_at fields (Ref: data.md §1)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
