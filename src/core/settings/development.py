"""
Django Development Settings for Online Supermarket.

Ref: .blueprint/infra.md §2B
These settings are for local development via Docker Compose.
"""
import os

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "web",                # Docker Compose service name
    "supermarket_web",    # Docker container name (for Prometheus scraping)
]

# Database - Local PostgreSQL via Docker (Ref: infra.md §2B)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "supermarket"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Redis Cache - Local Redis via Docker (Ref: data.md §2)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

# Development-specific: use verbose format instead of JSON for readability
LOGGING["handlers"]["console"]["formatter"] = "verbose"  # noqa: F405

# Debug Toolbar (only in development, if installed)
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "0.0.0.0"]
except ImportError:
    pass

# CORS settings for local frontend development
CORS_ALLOW_ALL_ORIGINS = True
