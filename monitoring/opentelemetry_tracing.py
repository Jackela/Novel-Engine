#!/usr/bin/env python3
"""
OpenTelemetry Distributed Tracing for Novel Engine

Implements comprehensive distributed tracing with:
- Request tracing across all components
- Performance bottleneck identification
- Service dependency mapping
- Error tracking and debugging support
"""

import asyncio
import inspect
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional

import opentelemetry.baggage as baggage

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncIOInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)


@dataclass
class TracingConfig:
    """Configuration for OpenTelemetry tracing"""

    service_name: str = "novel-engine"
    service_version: str = "1.0.0"
    environment: str = "production"

    # Sampling configuration
    sampling_rate: float = 1.0  # 100% sampling for production readiness assessment

    # Exporter configuration
    jaeger_endpoint: Optional[str] = None  # "http://localhost:14268/api/traces"
    otlp_endpoint: Optional[str] = None  # "http://localhost:4317"
    console_export: bool = True

    # Instrumentation settings
    auto_instrument_fastapi: bool = True
    auto_instrument_requests: bool = True
    auto_instrument_sqlite: bool = True
    auto_instrument_aiohttp: bool = True
    auto_instrument_asyncio: bool = True

    # Custom attributes
    custom_attributes: Dict[str, str] = field(default_factory=dict)


class TracingManager:
    """Manages OpenTelemetry tracing configuration and setup"""

    def __init__(self, config: TracingConfig):
        self.config = config
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.is_initialized = False

    def initialize(self) -> trace.Tracer:
        """Initialize OpenTelemetry tracing"""
        if self.is_initialized:
            return self.tracer

        try:
            # Create resource with service information
            resource = Resource.create(
                {
                    "service.name": self.config.service_name,
                    "service.version": self.config.service_version,
                    "deployment.environment": self.config.environment,
                    **self.config.custom_attributes,
                }
            )

            # Create tracer provider with sampling
            sampler = TraceIdRatioBased(self.config.sampling_rate)
            self.tracer_provider = TracerProvider(resource=resource, sampler=sampler)

            # Set up exporters
            self._setup_exporters()

            # Set the global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer
            self.tracer = trace.get_tracer(
                __name__, version=self.config.service_version
            )

            # Set up automatic instrumentation
            self._setup_auto_instrumentation()

            self.is_initialized = True
            logger.info(
                f"OpenTelemetry tracing initialized for {self.config.service_name}"
            )

            return self.tracer

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
            # Return a no-op tracer to prevent application failure
            return trace.NoOpTracer()

    def _setup_exporters(self):
        """Set up trace exporters"""
        exporters = []

        # Console exporter for development
        if self.config.console_export:
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            self.tracer_provider.add_span_processor(console_processor)
            exporters.append("console")

        # Jaeger exporter
        if self.config.jaeger_endpoint:
            try:
                jaeger_exporter = JaegerExporter(
                    agent_host_name="localhost",
                    agent_port=6831,
                    collector_endpoint=self.config.jaeger_endpoint,
                )
                jaeger_processor = BatchSpanProcessor(jaeger_exporter)
                self.tracer_provider.add_span_processor(jaeger_processor)
                exporters.append("jaeger")
            except Exception as e:
                logger.warning(f"Failed to setup Jaeger exporter: {e}")

        # OTLP exporter (for Grafana Tempo, etc.)
        if self.config.otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint,
                    insecure=True,  # Use insecure for local development
                )
                otlp_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(otlp_processor)
                exporters.append("otlp")
            except Exception as e:
                logger.warning(f"Failed to setup OTLP exporter: {e}")

        logger.info(f"Configured trace exporters: {', '.join(exporters)}")

    def _setup_auto_instrumentation(self):
        """Set up automatic instrumentation"""
        try:
            if self.config.auto_instrument_requests:
                RequestsInstrumentor().instrument()
                logger.debug("Enabled requests instrumentation")

            if self.config.auto_instrument_sqlite:
                SQLite3Instrumentor().instrument()
                logger.debug("Enabled SQLite instrumentation")

            if self.config.auto_instrument_aiohttp:
                AioHttpClientInstrumentor().instrument()
                logger.debug("Enabled aiohttp client instrumentation")

            if self.config.auto_instrument_asyncio:
                AsyncIOInstrumentor().instrument()
                logger.debug("Enabled asyncio instrumentation")

        except Exception as e:
            logger.warning(f"Failed to setup some auto-instrumentation: {e}")

    def instrument_fastapi(self, app):
        """Instrument FastAPI application"""
        if self.config.auto_instrument_fastapi:
            try:
                FastAPIInstrumentor.instrument_app(app)
                logger.info("FastAPI instrumentation enabled")
            except Exception as e:
                logger.error(f"Failed to instrument FastAPI: {e}")

    def shutdown(self):
        """Shutdown tracing"""
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("OpenTelemetry tracing shutdown complete")
            except Exception as e:
                logger.error(f"Error during tracing shutdown: {e}")


# Global tracing manager
tracing_manager: Optional[TracingManager] = None


def setup_tracing(config: TracingConfig = None) -> trace.Tracer:
    """Setup OpenTelemetry tracing with configuration"""
    global tracing_manager

    if config is None:
        config = TracingConfig()

    tracing_manager = TracingManager(config)
    return tracing_manager.initialize()


def get_tracer() -> trace.Tracer:
    """Get the current tracer"""
    if tracing_manager and tracing_manager.tracer:
        return tracing_manager.tracer
    return trace.get_tracer(__name__)


# Tracing decorators and context managers
@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Dict[str, Any] = None,
    record_exception: bool = True,
):
    """Context manager for tracing operations"""
    tracer = get_tracer()

    with tracer.start_as_current_span(operation_name) as span:
        # Add custom attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


@asynccontextmanager
async def trace_async_operation(
    operation_name: str,
    attributes: Dict[str, Any] = None,
    record_exception: bool = True,
):
    """Async context manager for tracing operations"""
    tracer = get_tracer()

    with tracer.start_as_current_span(operation_name) as span:
        # Add custom attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def trace_function(
    operation_name: str = None,
    attributes: Dict[str, Any] = None,
    record_exception: bool = True,
    record_parameters: bool = False,
    record_result: bool = False,
):
    """Decorator for tracing functions"""

    def decorator(func: Callable) -> Callable:
        # Determine operation name
        name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()

            with tracer.start_as_current_span(name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # Record parameters if requested
                if record_parameters:
                    # Get function signature
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for param_name, param_value in bound_args.arguments.items():
                        # Only record simple types to avoid serialization issues
                        if isinstance(param_value, (str, int, float, bool)):
                            span.set_attribute(
                                f"parameter.{param_name}", str(param_value)
                            )

                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                try:
                    start_time = time.time()

                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    duration = time.time() - start_time
                    span.set_attribute("duration_ms", duration * 1000)

                    # Record result if requested
                    if record_result and result is not None:
                        if isinstance(result, (str, int, float, bool)):
                            span.set_attribute("result", str(result))
                        elif hasattr(result, "__len__"):
                            span.set_attribute("result_length", len(result))

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()

            with tracer.start_as_current_span(name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # Record parameters if requested
                if record_parameters:
                    # Get function signature
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for param_name, param_value in bound_args.arguments.items():
                        # Only record simple types to avoid serialization issues
                        if isinstance(param_value, (str, int, float, bool)):
                            span.set_attribute(
                                f"parameter.{param_name}", str(param_value)
                            )

                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    span.set_attribute("duration_ms", duration * 1000)

                    # Record result if requested
                    if record_result and result is not None:
                        if isinstance(result, (str, int, float, bool)):
                            span.set_attribute("result", str(result))
                        elif hasattr(result, "__len__"):
                            span.set_attribute("result_length", len(result))

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Novel Engine specific tracing helpers
def trace_story_generation(story_type: str, character_count: int = 0):
    """Decorator for tracing story generation operations"""
    return trace_function(
        operation_name=f"story_generation.{story_type}",
        attributes={
            "story.type": story_type,
            "story.character_count": character_count,
            "component": "story_generation",
        },
        record_parameters=True,
        record_result=True,
    )


def trace_agent_coordination(agent_type: str, coordination_type: str):
    """Decorator for tracing agent coordination operations"""
    return trace_function(
        operation_name=f"agent_coordination.{coordination_type}",
        attributes={
            "agent.type": agent_type,
            "coordination.type": coordination_type,
            "component": "agent_coordination",
        },
        record_parameters=True,
    )


def trace_character_interaction(interaction_type: str):
    """Decorator for tracing character interaction operations"""
    return trace_function(
        operation_name=f"character_interaction.{interaction_type}",
        attributes={
            "interaction.type": interaction_type,
            "component": "character_interaction",
        },
        record_parameters=True,
    )


def trace_database_operation(operation_type: str, table_name: str = None):
    """Decorator for tracing database operations"""
    attributes = {"db.operation": operation_type, "component": "database"}
    if table_name:
        attributes["db.table"] = table_name

    return trace_function(
        operation_name=f"database.{operation_type}",
        attributes=attributes,
        record_parameters=False,  # Don't record DB parameters for security
        record_result=False,
    )


def trace_cache_operation(operation_type: str, cache_type: str = "general"):
    """Decorator for tracing cache operations"""
    return trace_function(
        operation_name=f"cache.{operation_type}",
        attributes={
            "cache.operation": operation_type,
            "cache.type": cache_type,
            "component": "cache",
        },
        record_parameters=False,  # Don't record cache keys for security
        record_result=False,
    )


def trace_api_request(endpoint: str, method: str = "GET"):
    """Decorator for tracing API requests"""
    return trace_function(
        operation_name=f"api.{method.lower()}.{endpoint.replace('/', '_')}",
        attributes={
            "http.method": method,
            "http.endpoint": endpoint,
            "component": "api",
        },
        record_parameters=False,  # HTTP parameters handled by auto-instrumentation
        record_result=False,
    )


# Baggage helpers for cross-service context
def set_baggage_item(key: str, value: str):
    """Set a baggage item for cross-service context"""
    try:
        baggage.set_baggage(key, value)
    except Exception as e:
        logger.warning(f"Failed to set baggage item {key}: {e}")


def get_baggage_item(key: str) -> Optional[str]:
    """Get a baggage item from cross-service context"""
    try:
        return baggage.get_baggage(key)
    except Exception as e:
        logger.warning(f"Failed to get baggage item {key}: {e}")
        return None


# Span utilities
def add_span_attributes(attributes: Dict[str, Any]):
    """Add attributes to the current span"""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Dict[str, Any] = None):
    """Add an event to the current span"""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        event_attributes = {}
        if attributes:
            for key, value in attributes.items():
                event_attributes[key] = str(value)
        current_span.add_event(name, event_attributes)


def record_span_exception(exception: Exception, escaped: bool = False):
    """Record an exception in the current span"""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.record_exception(exception, escaped=escaped)
        current_span.set_status(Status(StatusCode.ERROR, str(exception)))


# Health check for tracing
def get_tracing_health() -> Dict[str, Any]:
    """Get tracing system health information"""
    global tracing_manager

    health = {
        "status": "unknown",
        "initialized": False,
        "exporters": [],
        "sampling_rate": 0.0,
        "service_name": "unknown",
    }

    if tracing_manager:
        health.update(
            {
                "status": "healthy" if tracing_manager.is_initialized else "unhealthy",
                "initialized": tracing_manager.is_initialized,
                "sampling_rate": tracing_manager.config.sampling_rate,
                "service_name": tracing_manager.config.service_name,
                "environment": tracing_manager.config.environment,
            }
        )

        # Check which exporters are configured
        if tracing_manager.config.console_export:
            health["exporters"].append("console")
        if tracing_manager.config.jaeger_endpoint:
            health["exporters"].append("jaeger")
        if tracing_manager.config.otlp_endpoint:
            health["exporters"].append("otlp")

    return health


# Cleanup function
def shutdown_tracing():
    """Shutdown tracing system"""
    global tracing_manager
    if tracing_manager:
        tracing_manager.shutdown()
        tracing_manager = None


__all__ = [
    "TracingConfig",
    "TracingManager",
    "setup_tracing",
    "get_tracer",
    "trace_operation",
    "trace_async_operation",
    "trace_function",
    "trace_story_generation",
    "trace_agent_coordination",
    "trace_character_interaction",
    "trace_database_operation",
    "trace_cache_operation",
    "trace_api_request",
    "set_baggage_item",
    "get_baggage_item",
    "add_span_attributes",
    "add_span_event",
    "record_span_exception",
    "get_tracing_health",
    "shutdown_tracing",
]
