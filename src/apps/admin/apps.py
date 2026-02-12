"""Admin app configuration."""
from django.apps import AppConfig


class AdminConfig(AppConfig):
    """Configuration for admin app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin"
    label = "shop_admin"  # Avoid conflict with django.contrib.admin
