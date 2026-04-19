---
name: observability
description: Observability - Prometheus metrics, Grafana dashboards, Loki logging, Tempo traces, OpenTelemetry, alert rules
license: MIT
compatibility: opencode
metadata:
  audience: architects, senior-developers
  workflow: monitoring
---

# Observability Skill

## Role

Architect responsible for monitoring and observability. NOT a developer task - this is for the architect who sets up, maintains, and interprets monitoring systems.

## Stack Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Observability Stack                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │ Prometheus  │───►│  Grafana    │───►│  Alerting   │        │
│   │  (metrics)  │    │(dashboards) │    │  (alerts)   │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                                      ▲               │
│         ▼                                      │               │
│   ┌─────────────┐    ┌─────────────┐           │               │
│   │    Loki     │───►│  Grafana    │           │               │
│   │  (logs)     │    │ (log view)  │           │               │
│   └─────────────┘    └─────────────┘           │               │
│         │                                      │               │
│         ▼                                      │               │
│   ┌─────────────┐    ┌─────────────┐           │               │
│   │   Tempo     │───►│  Grafana    │───────────┘               │
│   │  (traces)   │    │(trace view) │                           │
│   └─────────────┘    └─────────────┘                           │
│                                                                 │
│   ┌─────────────┐                                              │
│   │ OTEL        │◄── Applications emit                          │
│   │ Collector   │                                              │
│   └─────────────┘                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Project Configuration

### docker-compose.staging.yml monitoring services

```yaml
# Docker Compose Staging includes:
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:10
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}

  loki:
    image: grafana/loki:2.9
    ports:
      - "3100:3100"

  tempo:
    image: grafana/tempo:2.3
    ports:
      - "4316:4316"  # gRPC
      - "4317:4317"  # HTTP

  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    volumes:
      - ./monitoring/otel-collector.yml:/etc/otelcol-contrib/config.yml:ro
```

## Prometheus

### prometheus.yml

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - /etc/prometheus/alert.rules.yml

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Backend metrics
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  # PostgreSQL exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis exporter
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Nginx exporter
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
```

### Alert Rules

```yaml
# monitoring/alert.rules.yml
groups:
  - name: backend_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
          > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "p99 latency is {{ $value | humanizeDuration }} (threshold: 2s)"

      # Backend down
      - alert: BackendDown
        expr: up{job="backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Backend is down"
          description: "Backend has been unreachable for more than 1 minute"

      # High memory usage
      - alert: HighMemoryUsage
        expr: |
          (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90%"

      # Celery task failures
      - alert: CeleryTaskFailures
        expr: |
          sum(rate(celery_tasks_failed_total[5m])) > 0.1
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Celery task failures detected"
          description: "Task failure rate is {{ $value }} per second"

  - name: database_alerts
    rules:
      # PostgreSQL down
      - alert: PostgreSQLDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"
```

### Key Metrics to Monitor

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `http_requests_total` | Total HTTP requests | - |
| `http_requests_total{status="5xx"}` | Server errors | Rate > 5% |
| `http_request_duration_seconds` | Request latency | p99 > 2s |
| `up{job="backend"}` | Backend availability | = 0 |
| `celery_tasks_failed_total` | Failed tasks | Rate > 0.1/s |
| `celery_queue_length` | Task backlog | > 100 |
| `postgres_connections` | DB connections | > 80% max |
| `redis_connected_clients` | Redis clients | > 1000 |

### Basic PromQL Queries

```promql
# Request rate per endpoint
sum(rate(http_requests_total[5m])) by (endpoint)

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# p99 latency
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Requests per second by status
sum(rate(http_requests_total[5m])) by (status)

# Top slow endpoints
topk(5, histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)))
```

## Grafana

### Data Sources Configuration

```yaml
# monitoring/grafana/datasources/datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3100
```

### Dashboard Structure

```json
{
  "dashboard": {
    "title": "Backend Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (status)"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8}
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m]))"
          }
        ],
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8}
      },
      {
        "title": "Latency (p99)",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ],
        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8}
      },
      {
        "title": "Top Endpoints by Latency",
        "type": "table",
        "targets": [
          {
            "expr": "topk(5, histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)))"
          }
        ],
        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8}
      }
    ]
  }
}
```

### Loki Log Queries

```loki
# All errors from backend
{job="backend"} |= "level=error"

# Logs with trace ID
{job="backend"} | json | trace_id != ""

# Slow requests (>1s)
{job="backend"} | json | request_duration > 1

# User-related logs
{job="backend"} | json | user_id = "12345"

# Error logs with stack traces
{job="backend"} |= "Traceback" | json

# Service communication errors
{job="backend"} |= "upstream" | json | status >= 500
```

### Trace Queries in Grafana

```traceql
# All traces with errors
{totalSpans > 0} | status = ERROR

# Trace by ID
{totalSpans > 0} | trace_id = "abc123"

# Slow traces (>5s)
{totalSpans > 0} | duration > 5s

# Specific service spans
{service.name = "backend"} | duration > 1s
```

## OpenTelemetry

### otel-collector.yml

```yaml
# monitoring/otel-collector.yml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  prometheus:
    config:
      scrape_configs:
        - job_name: 'backend'
          static_configs:
            - targets: ['backend:8000']

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"

  tempo:
    endpoint: "http://tempo:4317"
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [tempo]
    metrics:
      receivers: [prometheus]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      exporters: [loki]
```

### Backend Tracing Setup

```python
# backend/bootstrap/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

def setup_tracing():
    """Configure OpenTelemetry tracing."""
    resource = Resource(attributes={
        SERVICE_NAME: "backend",
        "deployment.environment": "staging",
    })

    provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )

    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)
```

### Adding Trace Context to Logs

```python
# backend/bootstrap/tracing.py
import structlog
from opentelemetry import trace

def add_trace_context(processor, _, config):
    """Add trace ID and span ID to log entries."""
    def processor_with_context(logger, method_name, event_dict):
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            event_dict["trace_id"] = format(span_context.trace_id, "032x")
            event_dict["span_id"] = format(span_context.span_id, "016x")
        return processor(logger, method_name, event_dict)
    return processor_with_context
```

## Health Checks

### What to Monitor

| Service | Check | Interval | Threshold |
|---------|-------|----------|-----------|
| Backend | HTTP /health | 30s | 3 failures |
| PostgreSQL | pg_isready | 30s | 3 failures |
| Redis | redis-cli ping | 30s | 3 failures |
| Celery | inspect stats | 60s | queue > 100 |

### Health Check Configuration

```yaml
# docker-compose.staging.yml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myservice"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Structlog for Loki

### Structured Logging Configuration

```python
# backend/bootstrap/config.py
import structlog

def setup_logging():
    """Configure structlog for JSON output to Loki."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Log Levels

| Level | Usage |
|-------|-------|
| DEBUG | Detailed information for debugging |
| INFO | Normal operation events |
| WARNING | Potential issues, recoverable errors |
| ERROR | Failed operations, caught exceptions |
| CRITICAL | System failures, service down |

### What to Log

```python
# GOOD: Structured logs with context
logger.info(
    "request_completed",
    method="POST",
    path="/api/users",
    status=201,
    duration_ms=145,
    user_id=123,
)

# GOOD: Error with stack trace
logger.error(
    "request_failed",
    method="GET",
    path="/api/users",
    error=str(exc),
    traceback=traceback,
)

# BAD: Unstructured logs
logger.info("User created")
logger.error("Error occurred")
```

## Portainer

### When to Use

- Container management (start, stop, restart)
- Log viewing
- Container inspection
- Image management
- Stack management

### When NOT to Use

- Deployments (use CI/CD)
- Configuration changes (use Infrastructure as Code)
- User management (configure properly, don't click around)

## Diagnosing Problems

### High Latency

1. Check Prometheus: `histogram_quantile(0.99, ...)` - which endpoints?
2. Check traces in Tempo: Find slow traces for that endpoint
3. Check logs in Loki: Look for database queries, external calls
4. Common causes: slow DB queries, network latency, resource exhaustion

### High Error Rate

1. Check Prometheus: `rate(http_requests_total{status=~"5.."}[5m])`
2. Check logs in Loki: `{status=~"5.."}` - what's the error?
3. Check traces in Tempo: Look for error spans
4. Common causes: DB connection issues, external API failures, OOM

### Service Down

1. Check health checks: `up{job="backend"}`
2. Check container status in Portainer
3. Check logs: `docker-compose logs backend`
4. Common causes: OOM killed, crash loop, network issues

### Memory Leak

1. Check Prometheus: `container_memory_usage_bytes` growing over time
2. Check Grafana dashboard: Memory panel
3. Common causes: Unbounded caches, connection leaks, accumulated logs

## Anti-Patterns

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| No alerts configured | Silent failures | Add alert rules |
| Only CPU/RAM monitoring | Missing business metrics | Add custom metrics |
| No distributed tracing | Can't find slow requests | Add OpenTelemetry |
| Logs without correlation | Can't link logs to traces | Add trace_id to logs |
| Too many alerts | Alert fatigue | Set appropriate thresholds |
| No alert routing | Nobody sees alerts | Configure notification policies |
| Dashboards not used | No visibility | Review dashboards weekly |

## Checklist for Architect

- [ ] Prometheus scraping all services
- [ ] Alert rules configured for critical services
- [ ] Alert routing configured (who gets notified)
- [ ] Grafana dashboards created
- [ ] Loki collecting logs from all services
- [ ] Tempo collecting traces
- [ ] Health checks configured in docker-compose
- [ ] Portainer accessible for debugging
- [ ] Dashboards reviewed weekly
- [ ] Alerts tested periodically
