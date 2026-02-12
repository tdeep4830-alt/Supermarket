"""
Custom Middleware for Online Supermarket.

Ref: .blueprint/infra.md §8A - Structured Logging with request_id
Ref: .blueprint/infra.md §8B - Performance Monitoring & Latency Tracking
Ref: .blueprint/infra.md §8C - Error Rate Alerting
"""
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from django.http import HttpRequest, HttpResponse

from .logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Latency thresholds in milliseconds
SLOW_QUERY_THRESHOLD_MS = 500  # Default threshold for SLOW_QUERY marking

# Path-specific thresholds (path prefix -> threshold in ms)
PATH_LATENCY_THRESHOLDS: dict[str, int] = {
    "/api/orders/": 500,     # Order API - critical path
    "/api/products/": 300,   # Product listing
    "/api/coupons/": 200,    # Coupon validation
}

# Error rate alert configuration
ERROR_RATE_THRESHOLD = 0.05  # 5% error rate threshold
ERROR_RATE_WINDOW_SECONDS = 300  # 5-minute sliding window
ERROR_RATE_MIN_REQUESTS = 10  # Minimum requests before alerting


# =============================================================================
# Request ID Middleware
# =============================================================================


class RequestIDMiddleware:
    """
    Adds unique request_id to each request for distributed tracing.

    Ref: infra.md §8A - Each request must have unique request_id (Trace ID).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]

        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        return response


# =============================================================================
# Request Latency Middleware
# =============================================================================


class RequestLatencyMiddleware:
    """
    Records API request latency and logs slow queries.

    Ref: infra.md §8B - Performance Monitoring

    Features:
    - Records latency for every API request
    - Marks requests exceeding threshold as SLOW_QUERY
    - Adds latency header to response (X-Response-Time)
    - Outputs structured logs for Grafana/Prometheus integration

    Log Fields (for Grafana):
    - latency_ms: Request latency in milliseconds
    - is_slow: Boolean flag for slow queries
    - path: Request path
    - method: HTTP method
    - status_code: Response status code
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip non-API requests (static files, admin, etc.)
        if not self._should_track(request.path):
            return self.get_response(request)

        # Record start time
        start_time = time.perf_counter()

        # Process request
        response = self.get_response(request)

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Add latency header for client-side monitoring
        response["X-Response-Time"] = f"{latency_ms:.2f}ms"

        # Determine if this is a slow query
        threshold = self._get_threshold(request.path)
        is_slow = latency_ms > threshold

        # Get request_id if available
        request_id = getattr(request, "request_id", None)

        # Build log context
        log_data = {
            "latency_ms": round(latency_ms, 2),
            "is_slow": is_slow,
            "threshold_ms": threshold,
            "path": request.path,
            "method": request.method,
            "status_code": response.status_code,
            "query_params": dict(request.GET) if request.GET else None,
        }

        if request_id:
            log_data["request_id"] = request_id

        # Add user info if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            log_data["user_id"] = str(request.user.id)

        # Log with appropriate level
        if is_slow:
            # SLOW_QUERY - Warning level for Grafana alerting
            logger.warning(
                f"SLOW_QUERY: {request.method} {request.path} took {latency_ms:.2f}ms",
                extra={
                    "extra_data": log_data,
                    "slow_query": True,
                    "request_id": request_id,
                },
            )
        else:
            # Normal request - Debug level
            logger.debug(
                f"API Request: {request.method} {request.path} - {latency_ms:.2f}ms",
                extra={
                    "extra_data": log_data,
                    "request_id": request_id,
                },
            )

        return response

    def _should_track(self, path: str) -> bool:
        """
        Determine if this request should be tracked.

        Only track API endpoints, skip static files and admin.
        """
        # Track all /api/ endpoints
        if path.startswith("/api/"):
            return True

        # Skip everything else
        return False

    def _get_threshold(self, path: str) -> int:
        """
        Get the latency threshold for a given path.

        Returns path-specific threshold if defined, otherwise default.
        """
        for prefix, threshold in PATH_LATENCY_THRESHOLDS.items():
            if path.startswith(prefix):
                return threshold

        return SLOW_QUERY_THRESHOLD_MS


# =============================================================================
# Request Metrics Middleware (Optional - for Prometheus)
# =============================================================================


class RequestMetricsMiddleware:
    """
    Collects request metrics for Prometheus/Grafana.

    Ref: infra.md §8B - Metrics Collection

    Metrics collected:
    - http_request_duration_seconds: Histogram of request durations
    - http_requests_total: Counter of total requests

    Note: This middleware is optional and requires prometheus_client library.
    Enable by adding to MIDDLEWARE after installing prometheus_client.
    """

    # Placeholder for prometheus metrics
    _request_histogram = None
    _request_counter = None
    _initialized = False

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._init_metrics()

    @classmethod
    def _init_metrics(cls) -> None:
        """Initialize Prometheus metrics (lazy loading)."""
        if cls._initialized:
            return

        try:
            from prometheus_client import Counter, Histogram

            cls._request_histogram = Histogram(
                "http_request_duration_seconds",
                "HTTP request duration in seconds",
                ["method", "endpoint", "status"],
                buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            )

            cls._request_counter = Counter(
                "http_requests_total",
                "Total HTTP requests",
                ["method", "endpoint", "status"],
            )

            cls._initialized = True
            logger.info("Prometheus metrics initialized")

        except ImportError:
            logger.debug("prometheus_client not installed, metrics disabled")
            cls._initialized = True

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        start_time = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start_time

        # Normalize endpoint for metric labels (avoid high cardinality)
        endpoint = self._normalize_endpoint(request.path)

        # Record metrics if available
        if self._request_histogram is not None:
            self._request_histogram.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).observe(duration)

        if self._request_counter is not None:
            self._request_counter.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).inc()

        return response

    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path to avoid high cardinality in metrics.

        Examples:
            /api/orders/abc-123/ -> /api/orders/{id}/
            /api/products/xyz/ -> /api/products/{id}/
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/",
            "/{id}/",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+/", "/{id}/", path)

        return path


# =============================================================================
# Error Rate Alert Middleware
# =============================================================================


@dataclass
class RequestStats:
    """Thread-safe request statistics for error rate calculation."""

    total: int = 0
    errors: int = 0
    timestamps: deque = field(default_factory=lambda: deque(maxlen=10000))
    error_timestamps: deque = field(default_factory=lambda: deque(maxlen=10000))
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_alert_time: float = 0


class ErrorRateAlertMiddleware:
    """
    Monitors API error rates and logs warnings when thresholds are exceeded.

    Ref: infra.md §8C - Error Rate Alerting

    Features:
    - Tracks error rate per endpoint using sliding window
    - Logs WARNING when /api/orders/ error rate exceeds 5%
    - Thread-safe implementation for production use
    - Rate-limited alerting (max 1 alert per minute per endpoint)

    Alert Output Format (for Grafana/log aggregation):
    - alert_type: "ERROR_RATE_EXCEEDED"
    - endpoint: "/api/orders/"
    - error_rate: 0.08 (8%)
    - threshold: 0.05 (5%)
    - window_seconds: 300
    """

    # Class-level stats storage (shared across instances)
    _stats: dict[str, RequestStats] = {}
    _stats_lock = threading.Lock()

    # Alert rate limiting (1 alert per minute per endpoint)
    ALERT_COOLDOWN_SECONDS = 60

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only track /api/ endpoints
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        # Process request
        response = self.get_response(request)

        # Normalize endpoint for tracking
        endpoint = self._normalize_endpoint(request.path)

        # Record request
        self._record_request(endpoint, response.status_code)

        # Check error rate for orders endpoint
        if endpoint.startswith("/api/orders"):
            self._check_error_rate(endpoint)

        return response

    def _get_stats(self, endpoint: str) -> RequestStats:
        """Get or create stats for an endpoint (thread-safe)."""
        with self._stats_lock:
            if endpoint not in self._stats:
                self._stats[endpoint] = RequestStats()
            return self._stats[endpoint]

    def _record_request(self, endpoint: str, status_code: int) -> None:
        """Record a request for error rate tracking."""
        stats = self._get_stats(endpoint)
        current_time = time.time()
        is_error = status_code >= 500

        with stats.lock:
            # Add to sliding window
            stats.timestamps.append(current_time)
            stats.total += 1

            if is_error:
                stats.error_timestamps.append(current_time)
                stats.errors += 1

            # Clean old entries outside the window
            self._cleanup_old_entries(stats, current_time)

    def _cleanup_old_entries(self, stats: RequestStats, current_time: float) -> None:
        """Remove entries older than the sliding window."""
        cutoff = current_time - ERROR_RATE_WINDOW_SECONDS

        # Remove old timestamps
        while stats.timestamps and stats.timestamps[0] < cutoff:
            stats.timestamps.popleft()
            stats.total = max(0, stats.total - 1)

        # Remove old error timestamps
        while stats.error_timestamps and stats.error_timestamps[0] < cutoff:
            stats.error_timestamps.popleft()
            stats.errors = max(0, stats.errors - 1)

    def _check_error_rate(self, endpoint: str) -> None:
        """Check if error rate exceeds threshold and log alert if needed."""
        stats = self._get_stats(endpoint)
        current_time = time.time()

        with stats.lock:
            # Need minimum requests to avoid false positives
            if stats.total < ERROR_RATE_MIN_REQUESTS:
                return

            # Calculate error rate
            error_rate = stats.errors / stats.total if stats.total > 0 else 0

            # Check if threshold exceeded
            if error_rate <= ERROR_RATE_THRESHOLD:
                return

            # Rate limit alerts (1 per minute per endpoint)
            if current_time - stats.last_alert_time < self.ALERT_COOLDOWN_SECONDS:
                return

            # Update last alert time
            stats.last_alert_time = current_time

        # Log alert (outside lock to avoid blocking)
        logger.warning(
            f"ERROR_RATE_EXCEEDED: {endpoint} error rate is "
            f"{error_rate:.1%} (threshold: {ERROR_RATE_THRESHOLD:.0%})",
            extra={
                "extra_data": {
                    "alert_type": "ERROR_RATE_EXCEEDED",
                    "endpoint": endpoint,
                    "error_rate": round(error_rate, 4),
                    "error_count": stats.errors,
                    "total_count": stats.total,
                    "threshold": ERROR_RATE_THRESHOLD,
                    "window_seconds": ERROR_RATE_WINDOW_SECONDS,
                },
                "alert": True,
            },
        )

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint for consistent tracking."""
        import re

        # Replace UUIDs with placeholder
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs with placeholder
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        # Remove trailing slash for consistency
        return path.rstrip("/") or "/"
