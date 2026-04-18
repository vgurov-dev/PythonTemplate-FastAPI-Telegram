"""Tracing setup for backend with OpenTelemetry."""
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import structlog

logger = structlog.get_logger()


def setup_tracing() -> None:
    """Setup OpenTelemetry tracing."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "backend")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    if not endpoint:
        logger.warning("tracing_disabled_no_endpoint")
        return

    resource = Resource(attributes={
        SERVICE_NAME: service_name,
    })

    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    except Exception as e:
        logger.warning("tracing_export_error", error=str(e))
        return

    trace.set_tracer_provider(provider)

    logger.info("tracing_initialized", service=service_name, endpoint=endpoint)


def setup_fastapi_tracing(app) -> None:
    """Instrument FastAPI with OpenTelemetry."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("fastapi_instrumented")
    except Exception as e:
        logger.warning("fastapi_instrumentation_error", error=str(e))