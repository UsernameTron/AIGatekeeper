"""
OpenTelemetry Distributed Tracing Integration
Provides distributed tracing across all AI Gatekeeper components
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(self):
        self.service_name = os.getenv('OTEL_SERVICE_NAME', 'ai-gatekeeper')
        self.service_version = os.getenv('OTEL_SERVICE_VERSION', '1.0.0')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')
        self.enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
        self.sample_rate = float(os.getenv('OTEL_SAMPLE_RATE', '1.0'))


def setup_tracing(app=None, db_engine=None) -> Optional[trace.Tracer]:
    """
    Setup OpenTelemetry distributed tracing.

    Args:
        app: Flask application instance (optional)
        db_engine: SQLAlchemy engine instance (optional)

    Returns:
        Tracer instance if enabled, None otherwise
    """
    config = TracingConfig()

    if not config.enabled:
        logging.info("OpenTelemetry tracing is disabled")
        return None

    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: config.service_name,
            SERVICE_VERSION: config.service_version,
            "deployment.environment": config.environment,
            "telemetry.sdk.language": "python"
        })

        # Setup trace provider
        provider = TracerProvider(resource=resource)

        # Setup OTLP exporter
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)
            logging.info(f"OTLP exporter configured: {config.otlp_endpoint}")
        except Exception as e:
            logging.warning(f"Failed to configure OTLP exporter: {e}")
            # Continue without OTLP exporter - spans will still be created

        # Set the global trace provider
        trace.set_tracer_provider(provider)

        # Instrument Flask if provided
        if app:
            FlaskInstrumentor().instrument_app(app)
            logging.info("Flask instrumentation enabled")

        # Instrument SQLAlchemy if provided
        if db_engine:
            SQLAlchemyInstrumentor().instrument(
                engine=db_engine,
                service=config.service_name
            )
            logging.info("SQLAlchemy instrumentation enabled")

        # Instrument requests library
        RequestsInstrumentor().instrument()
        logging.info("Requests library instrumentation enabled")

        # Get tracer
        tracer = trace.get_tracer(
            instrumenting_module_name=config.service_name,
            instrumenting_library_version=config.service_version
        )

        logging.info(f"OpenTelemetry tracing initialized: {config.service_name} v{config.service_version}")
        return tracer

    except Exception as e:
        logging.error(f"Failed to setup OpenTelemetry tracing: {e}")
        return None


def trace_operation(operation_name: str, **attributes):
    """
    Context manager for tracing operations.

    Usage:
        with trace_operation("process_support_request", user_id="123"):
            # Your code here
            pass

    Args:
        operation_name: Name of the operation to trace
        **attributes: Additional attributes to add to the span
    """
    from contextlib import contextmanager

    @contextmanager
    def _trace():
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(operation_name) as span:
            # Add attributes
            for key, value in attributes.items():
                span.set_attribute(key, value)

            try:
                yield span
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    return _trace()


def add_span_attributes(**attributes):
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add to the current span
    """
    try:
        current_span = trace.get_current_span()
        if current_span.is_recording():
            for key, value in attributes.items():
                current_span.set_attribute(key, value)
    except Exception as e:
        logging.debug(f"Failed to add span attributes: {e}")


def add_span_event(name: str, **attributes):
    """
    Add an event to the current span.

    Args:
        name: Event name
        **attributes: Event attributes
    """
    try:
        current_span = trace.get_current_span()
        if current_span.is_recording():
            current_span.add_event(name, attributes)
    except Exception as e:
        logging.debug(f"Failed to add span event: {e}")


def get_trace_context():
    """
    Get the current trace context for propagation.

    Returns:
        Dictionary with trace_id and span_id
    """
    try:
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()

        return {
            "trace_id": format(span_context.trace_id, '032x'),
            "span_id": format(span_context.span_id, '016x'),
            "trace_flags": span_context.trace_flags
        }
    except Exception:
        return {}


# Decorator for automatic tracing
def traced(operation_name: str = None):
    """
    Decorator to automatically trace function execution.

    Usage:
        @traced("my_operation")
        def my_function():
            pass

    Args:
        operation_name: Name for the span (defaults to function name)
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = operation_name or func.__name__
            tracer = trace.get_tracer(__name__)

            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = operation_name or func.__name__
            tracer = trace.get_tracer(__name__)

            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


__all__ = [
    'setup_tracing',
    'trace_operation',
    'add_span_attributes',
    'add_span_event',
    'get_trace_context',
    'traced'
]
