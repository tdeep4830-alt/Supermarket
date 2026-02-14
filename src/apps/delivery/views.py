"""
Delivery Views.

Ref: .blueprint/code_structure.md §2
Ref: .blueprint/data.md §3 - Delivery Slot Management

API endpoints for delivery slot operations.
"""

import logging
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.delivery import services
from apps.delivery import selectors
from apps.delivery.models import DeliverySlot

logger = logging.getLogger(__name__)

# =============================================================================
# Public API Views - Available to all authenticated users
# =============================================================================


class AvailableSlotsView(APIView):
    """
    Get available delivery slots.

    GET /api/delivery/slots/available/
    Query params:
        - start_date: Start date (YYYY-MM-DD, default: today)
        - days: Number of days to look ahead (default: 7)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """Return available delivery slots for the specified date range."""
        start_date_str = request.query_params.get("start_date")
        days_str = request.query_params.get("days", "7")

        # Parse start date
        if start_date_str:
            try:
                start_date = parse_date(start_date_str)
                if not start_date:
                    return Response(
                        {
                            "error": {
                                "code": "invalid_date",
                                "message": "Invalid date format. Use YYYY-MM-DD.",
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": "invalid_date",
                            "message": "Invalid date format. Use YYYY-MM-DD.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            start_date = timezone.now().date()

        # Parse days
        try:
            days = int(days_str)
            if days < 1 or days > 30:
                return Response(
                    {
                        "error": {
                            "code": "invalid_days",
                            "message": "Days must be between 1 and 30.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValueError:
            days = 7

        try:
            slots = selectors.get_available_slots(start_date=start_date, days_ahead=days)

            logger.debug(
                "Available slots retrieved",
                extra={
                    "extra_data": {
                        "start_date": str(start_date),
                        "days": days,
                        "count": len(slots),
                        "user_id": str(request.user.id) if not isinstance(request.user, AnonymousUser) else None,
                    }
                },
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "slots": slots,
                        "count": len(slots),
                        "start_date": str(start_date),
                        "end_date": str(start_date + timezone.timedelta(days=days)),
                    },
                }
            )
        except Exception as e:
            logger.error(
                "Error retrieving available slots",
                exc_info=True,
                extra={
                    "extra_data": {
                        "error": str(e),
                        "start_date": str(start_date),
                        "days": days,
                    }
                },
            )
            return Response(
                {"error": {"code": "internal_error", "message": "Failed to retrieve slots"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =============================================================================
# Admin API Views - Require admin permissions
# =============================================================================


class AdminSlotBatchCreateView(APIView):
    """
    Batch create delivery slots (admin only).

    POST /api/admin/delivery/slots/batch-create/
    {
        "start_date": "2026-01-15",
        "days": 7,
        "time_slots": [
            ["09:00", "12:00"],
            ["14:00", "17:00"],
            ["18:00", "21:00"]
        ],
        "capacity": 15
    }
    """

    permission_classes = [IsAdminUser]

    def post(self, request: Request) -> Response:
        """Batch create delivery slots for upcoming days."""
        start_date_str = request.data.get("start_date")
        days = request.data.get("days", 7)
        time_slots = request.data.get("time_slots")
        capacity = request.data.get("capacity", 10)

        # Validate required fields
        if not start_date_str:
            return Response(
                {
                    "error": {
                        "code": "missing_field",
                        "message": "start_date is required",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse start date
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return Response(
                {
                    "error": {
                        "code": "invalid_date",
                        "message": "Invalid date format. Use YYYY-MM-DD.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            created_slots = services.batch_create_slots(
                start_date=start_date,
                days=days,
                time_slots=time_slots,
                capacity=capacity,
                admin_user=request.user,
            )

            logger.info(
                "Batch delivery slots created",
                extra={
                    "extra_data": {
                        "admin_user_id": str(request.user.id),
                        "start_date": str(start_date),
                        "days": days,
                        "capacity": capacity,
                        "created_count": len(created_slots),
                    }
                },
            )

            return Response(
                {
                    "success": True,
                    "message": f"Created {len(created_slots)} delivery slots",
                    "data": {"slots": created_slots, "count": len(created_slots)},
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(
                "Error creating delivery slots",
                exc_info=True,
                extra={
                    "extra_data": {
                        "error": str(e),
                        "admin_user_id": str(request.user.id),
                    }
                },
            )
            return Response(
                {"error": {"code": "internal_error", "message": "Failed to create slots"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminSlotEmergencyBlockView(APIView):
    """
    Emergency block a delivery slot (admin only).

    PATCH /api/admin/delivery/slots/{slot_id}/emergency-block/
    {
        "reason": "Vehicle breakdown"
    }
    """

    permission_classes = [IsAdminUser]

    def patch(self, request: Request, slot_id: str) -> Response:
        """Emergency block a delivery slot."""
        reason = request.data.get("reason", "Emergency")

        try:
            result = services.emergency_block_slot(
                slot_id=slot_id, admin_user=request.user, reason=reason
            )

            return Response(
                {
                    "success": True,
                    "message": "Delivery slot has been emergency blocked",
                    "data": result,
                }
            )
        except services.DeliverySlotNotFoundError:
            return Response(
                {
                    "error": {
                        "code": "slot_not_found",
                        "message": "Delivery slot not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error blocking delivery slot",
                exc_info=True,
                extra={
                    "extra_data": {
                        "error": str(e),
                        "slot_id": slot_id,
                        "admin_user_id": str(request.user.id),
                    }
                },
            )
            return Response(
                {"error": {"code": "internal_error", "message": "Failed to block slot"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminDeliverySlotsListView(APIView):
    """
    Get all upcoming delivery slots (admin only).

    GET /api/admin/delivery/slots/
    Query params:
        - days: Number of days to look ahead (default: 30)
    """

    permission_classes = [IsAdminUser]

    def get(self, request: Request) -> Response:
        """Get all upcoming delivery slots."""
        days_str = request.query_params.get("days", "30")

        try:
            days = int(days_str)
            if days < 1 or days > 90:
                return Response(
                    {
                        "error": {
                            "code": "invalid_days",
                            "message": "Days must be between 1 and 90.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValueError:
            days = 30

        try:
            slots = selectors.get_upcoming_slots(days=days, include_inactive=True)

            logger.info(
                "Admin fetched delivery slots",
                extra={
                    "extra_data": {
                        "admin_user_id": str(request.user.id),
                        "days": days,
                        "count": len(slots),
                    }
                },
            )

            return Response(
                {
                    "success": True,
                    "data": [
                        {
                            "id": str(slot.id),
                            "date": slot.date.isoformat(),
                            "start_time": slot.start_time.isoformat(),
                            "end_time": slot.end_time.isoformat(),
                            "max_capacity": slot.max_capacity,
                            "current_count": slot.current_count,
                            "available_count": slot.available_count,
                            "is_active": slot.is_active,
                            "is_almost_full": slot.is_almost_full,
                            "is_full": slot.is_full,
                        }
                        for slot in slots
                    ],
                }
            )
        except Exception as e:
            logger.error(
                "Error fetching admin delivery slots",
                exc_info=True,
                extra={
                    "extra_data": {
                        "error": str(e),
                        "admin_user_id": str(request.user.id),
                    }
                },
            )
            return Response(
                {"error": {"code": "internal_error", "message": "Failed to fetch slots"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
