"""Delivery URL Configuration."""

from django.urls import path

from .views import (
    AdminDeliverySlotsListView,
    AdminSlotBatchCreateView,
    AdminSlotEmergencyBlockView,
    AvailableSlotsView,
)

app_name = "delivery"

urlpatterns: list = [
    # Public endpoints - Available slots
    path(
        "slots/available/",
        AvailableSlotsView.as_view(),
        name="available-slots",
    ),
    # Admin endpoints - Slot management
    path(
        "admin/slots/",
        AdminDeliverySlotsListView.as_view(),
        name="admin-slots-list",
    ),
    path(
        "admin/slots/batch-create/",
        AdminSlotBatchCreateView.as_view(),
        name="admin-batch-create",
    ),
    path(
        "admin/slots/<uuid:slot_id>/emergency-block/",
        AdminSlotEmergencyBlockView.as_view(),
        name="admin-emergency-block",
    ),
]
