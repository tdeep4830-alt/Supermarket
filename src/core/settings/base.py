"""
Django Base Settings for Online Supermarket.

Ref: .blueprint/infra.md, .blueprint/code_sturcture.md
This module contains settings shared across all environments.
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-key-change-in-production"
)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "django_prometheus",  # Observability (Ref: infra.md §8C)
    # Local apps
    "common",
    "apps.products",
    "apps.orders",
    "apps.users",
    "apps.delivery",
    "apps.admin",  # Admin Portal API
]

MIDDLEWARE = [
    # Prometheus - MUST be first (Ref: infra.md §8C)
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware (Ref: infra.md §8A, §8B, §8C)
    "common.middleware.RequestIDMiddleware",       # Adds X-Request-ID for tracing
    "common.middleware.RequestLatencyMiddleware",  # Logs latency & SLOW_QUERY
    "common.middleware.ErrorRateAlertMiddleware",  # Alerts on high error rates
    # Prometheus - MUST be last (Ref: infra.md §8C)
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Hong_Kong"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type (Ref: data.md §4 - UUID)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model (Ref: auth.md §2A)
AUTH_USER_MODEL = "users.User"

# Session Configuration (Ref: auth.md §1, §3)
# Session data stored in Redis for performance and scalability
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"  # Uses Redis cache defined in CACHES
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_COOKIE_HTTPONLY = True  # Prevent JS access (XSS protection)
SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection
SESSION_COOKIE_SECURE = False  # Override to True in production settings
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session expiry on each request

# CSRF Configuration (Ref: auth.md §3)
CSRF_COOKIE_HTTPONLY = False  # Frontend needs to read CSRF token from cookie
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False  # Override to True in production settings
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3001",  # React dev server
    "http://127.0.0.1:3001",
]

# Logging Configuration (Ref: infra.md §8A - Structured JSON Logging)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "common.logging.JSONFormatter",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Middleware logging (Ref: infra.md §8B - SLOW_QUERY monitoring)
        "common.middleware": {
            "handlers": ["console"],
            "level": os.environ.get("MIDDLEWARE_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
    },
}

# Django REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "EXCEPTION_HANDLER": "common.exception_handlers.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
