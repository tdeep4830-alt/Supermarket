# =============================================================================
# Online Supermarket - Multi-stage Dockerfile
# Ref: .blueprint/infra.md §2A
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS production

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    DJANGO_SETTINGS_MODULE=core.settings.production

WORKDIR $APP_HOME

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Ref: infra.md §2A - User Permission)
RUN groupadd --gid 1000 django-group && \
    useradd --uid 1000 --gid django-group --shell /bin/bash --create-home django-user

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=django-user:django-group ./src $APP_HOME

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Switch to non-root user
USER django-user

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

# Start command (Ref: infra.md §4 - Start Command)
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]

# -----------------------------------------------------------------------------
# Stage 3: Development - With dev dependencies
# -----------------------------------------------------------------------------
FROM production AS development

USER root

# Install dev dependencies (base.txt is referenced by development.txt)
COPY requirements/base.txt requirements/base.txt
COPY requirements/development.txt requirements/development.txt
RUN pip install --no-cache-dir -r requirements/development.txt

USER django-user

# Override command for development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
