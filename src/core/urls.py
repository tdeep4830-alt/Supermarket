"""
URL configuration for Online Supermarket.

Ref: .blueprint/infra.md §5 - Health Checks
Ref: .blueprint/infra.md §8C - Metrics Monitoring
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from common.views import health_check

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health Check (Ref: infra.md §5)
    path("health/", health_check, name="health_check"),
    # Prometheus Metrics (Ref: infra.md §8C)
    path("", include("django_prometheus.urls")),
    # API Endpoints
    path("api/products/", include("apps.products.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/auth/", include("apps.users.urls")),  # Auth endpoints (Ref: auth.md §5)
    path("api/delivery/", include("apps.delivery.urls")),
]

# Debug Toolbar URLs (only in development)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
