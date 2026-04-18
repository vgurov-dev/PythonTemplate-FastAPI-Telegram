"""Metrics setup for backend."""
from typing import Optional

from fastapi import FastAPI, Request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import Counter, Histogram, Gauge
import structlog

logger = structlog.get_logger()

# Custom metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

active_connections = Gauge(
    "active_connections",
    "Active database connections",
)

app_version = Gauge(
    "app_version",
    "Application version",
)

app_start_time = Gauge(
    "app_start_time_seconds",
    "Application start time in seconds",
)


def setup_metrics(app: FastAPI) -> None:
    """Setup Prometheus metrics endpoint."""

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from fastapi.responses import Response

        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.middleware("http")
    async def prometheus_metrics(request: Request, call_next):
        """Track request metrics."""
        import time

        method = request.method
        endpoint = request.url.path
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        status = response.status_code

        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status,
        ).inc()

        http_request_duration.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

        return response

    # Set app info
    import time

    app_version.set(1)
    app_start_time.set(time.time())

    logger.info("metrics_initialized")