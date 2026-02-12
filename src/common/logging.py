"""
Structured JSON Logging for Online Supermarket.

Ref: .blueprint/infra.md §8A - All logs must be JSON format.
Ref: .blueprint/infra.md §8B - Performance Monitoring fields.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Outputs logs in JSON format for Render Log Streams / Grafana.

    Ref: infra.md §8A, §8B

    Standard Fields:
    - timestamp: ISO 8601 format
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - module, function, line: Source location

    Optional Fields:
    - request_id: Distributed tracing ID
    - slow_query: Boolean flag for performance monitoring
    - extra: Additional context data

    Grafana Integration:
    - Use `slow_query: true` to filter slow requests
    - Use `extra.latency_ms` for latency histograms
    - Use `extra.status_code` for error rate dashboards
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Distributed tracing
        if hasattr(record, "request_id") and record.request_id:
            log_record["request_id"] = record.request_id

        # Performance monitoring - SLOW_QUERY flag
        if hasattr(record, "slow_query") and record.slow_query:
            log_record["slow_query"] = True

        # Exception info
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Extra context data
        if hasattr(record, "extra_data") and record.extra_data:
            log_record["extra"] = record.extra_data

            # Promote latency_ms to top level for easier Grafana queries
            if "latency_ms" in record.extra_data:
                log_record["latency_ms"] = record.extra_data["latency_ms"]

        return json.dumps(log_record, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Usage:
        from common.logging import get_logger
        logger = get_logger(__name__)

        # Basic logging
        logger.info("Order created", extra={"extra_data": {"order_id": "xxx"}})

        # With request_id for distributed tracing
        logger.info("Processing order", extra={
            "request_id": "abc-123",
            "extra_data": {"order_id": "xxx"},
        })

        # Slow query logging (for Grafana alerting)
        logger.warning("SLOW_QUERY: ...", extra={
            "slow_query": True,
            "extra_data": {"latency_ms": 750, "path": "/api/orders/"},
        })
    """
    return logging.getLogger(name)
