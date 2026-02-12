"""
Common Views for Online Supermarket.

Ref: .blueprint/infra.md §5, §8D - Health Checks
"""
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse


def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for Render/Docker.

    Ref: infra.md §5, §8D
    Checks: Database + Redis connectivity.
    """
    health_status = {
        "status": "healthy",
        "database": "ok",
        "cache": "ok",
    }
    status_code = 200

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        health_status["database"] = f"error: {e}"
        health_status["status"] = "unhealthy"
        status_code = 503

    # Check Redis
    try:
        cache.set("health_check", "ok", timeout=1)
        if cache.get("health_check") != "ok":
            raise ConnectionError("Cache read/write failed")
    except Exception as e:
        health_status["cache"] = f"error: {e}"
        health_status["status"] = "unhealthy"
        status_code = 503

    return JsonResponse(health_status, status=status_code)
