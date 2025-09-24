#!/usr/bin/env python3
"""
OpenTelemetry Distributed Tracing Infrastructure

Comprehensive distributed tracing implementation for M10 Observability system.
Provides turn-level and phase-level instrumentation with cross-context propagation.
"""

import functools
import logging
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
)
from uuid import UUID

from opentelemetry import baggage, propagate, trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import (
    Decision,
    ParentBased,
    Sampler,
    SamplingResult,
    StaticSampler,
    TraceIdRatioBased,
)
from opentelemetry.util.types import Attributes

logger = logging.getLogger(__name__)


class NovelEngineTracingConfig:
    """Configuration for Novel Engine distributed tracing."""

    def __init__(
        self,
        service_name: str = "novel-engine-orchestration",
        service_version: str = "2.0.0",
        environment: str = "development",
        jaeger_endpoint: Optional[str] = None,
        otlp_endpoint: Optional[str] = None,
        sampling_rate: float = 0.1,
        enable_console_exporter: bool = False,
    ):
        """
        Initialize tracing configuration.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            environment: Environment (development, staging, production)
            jaeger_endpoint: Jaeger collector endpoint
            otlp_endpoint: OTLP collector endpoint
            sampling_rate: Default sampling rate (0.0 to 1.0)
            enable_console_exporter: Whether to enable console export for debugging
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.jaeger_endpoint = (
            jaeger_endpoint or "http://localhost:14268/api/traces"
        )
        self.otlp_endpoint = otlp_endpoint or "http://localhost:4317"
        self.sampling_rate = sampling_rate
        self.enable_console_exporter = enable_console_exporter


class IntelligentSampler(Sampler):
    """
    Intelligent sampling strategy for Novel Engine tracing.

    Implements custom sampling logic based on:
    - Operation type and complexity
    - Error conditions (always sample errors)
    - High-cost operations (sample expensive AI calls)
    - Performance characteristics (sample slow operations)
    """

    def __init__(self, default_rate: float = 0.1):
        """
        Initialize intelligent sampler.

        Args:
            default_rate: Default sampling rate for normal operations
        """
        self.default_rate = default_rate
        self.error_sampler = StaticSampler(Decision.RECORD_AND_SAMPLE)
        self.high_cost_sampler = TraceIdRatioBased(
            0.5
        )  # 50% for expensive operations
        self.slow_operation_sampler = TraceIdRatioBased(
            0.8
        )  # 80% for slow operations
        self.default_sampler = TraceIdRatioBased(default_rate)

    def should_sample(
        self,
        context: Optional[trace.Context],
        trace_id: int,
        name: str,
        kind: Optional[trace.SpanKind] = None,
        attributes: Optional[Attributes] = None,
        links: Optional[Sequence[trace.Link]] = None,
        trace_state: Optional[trace.TraceState] = None,
    ) -> SamplingResult:
        """
        Determine sampling decision based on intelligent criteria.

        Args:
            context: Trace context
            trace_id: Trace ID
            name: Span name
            kind: Span kind
            attributes: Span attributes
            links: Span links
            trace_state: Trace state

        Returns:
            Sampling decision
        """
        if not attributes:
            attributes = {}

        # Always sample errors
        if any(key.startswith("error") for key in attributes.keys()):
            return self.error_sampler.should_sample(
                context, trace_id, name, kind, attributes, links, trace_state
            )

        # Sample high-cost operations more frequently
        ai_cost = attributes.get("turn.total_cost", 0)
        if isinstance(ai_cost, (int, float)) and ai_cost > 1.0:
            return self.high_cost_sampler.should_sample(
                context, trace_id, name, kind, attributes, links, trace_state
            )

        # Sample slow operations more frequently
        duration = attributes.get("turn.duration_seconds", 0)
        if isinstance(duration, (int, float)) and duration > 10.0:
            return self.slow_operation_sampler.should_sample(
                context, trace_id, name, kind, attributes, links, trace_state
            )

        # Default sampling for normal operations
        return self.default_sampler.should_sample(
            context, trace_id, name, kind, attributes, links, trace_state
        )

    def get_description(self) -> str:
        """Get sampler description."""
        return f"IntelligentSampler(default_rate={self.default_rate})"


class NovelEngineTracer:
    """
    Novel Engine distributed tracer with intelligent instrumentation.

    Provides comprehensive tracing capabilities for turn orchestration:
    - Root span coverage for complete turn execution
    - Phase-level spans with detailed context
    - Cross-context trace propagation
    - Performance correlation with metrics
    """

    def __init__(self, config: NovelEngineTracingConfig):
        """
        Initialize Novel Engine tracer.

        Args:
            config: Tracing configuration
        """
        self.config = config
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._initialize_tracing()

        logger.info(f"NovelEngineTracer initialized for {config.service_name}")

    def _initialize_tracing(self) -> None:
        """Initialize OpenTelemetry tracing with exporters and sampling."""

        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
                "environment": self.config.environment,
                "component": "turn_orchestration",
            }
        )

        # Create tracer provider with intelligent sampling
        sampler = ParentBased(
            root=IntelligentSampler(self.config.sampling_rate)
        )

        self.tracer_provider = TracerProvider(
            resource=resource, sampler=sampler
        )

        # Add exporters
        if self.config.jaeger_endpoint:
            # JaegerExporter parameter compatibility fix
            try:
                # Try newer parameter name first
                jaeger_exporter = JaegerExporter(
                    collector_endpoint=self.config.jaeger_endpoint
                )
            except TypeError:
                # Fallback to older parameter name
                try:
                    jaeger_exporter = JaegerExporter(
                        endpoint=self.config.jaeger_endpoint
                    )
                except TypeError:
                    # Final fallback with minimal parameters
                    jaeger_exporter = JaegerExporter()
                    logger.warning(
                        "Using default Jaeger exporter configuration due to parameter incompatibility"
                    )

            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            logger.info(
                f"Jaeger exporter configured: {self.config.jaeger_endpoint}"
            )

        if self.config.otlp_endpoint:
            try:
                # OTLP exporter configuration with error handling
                otlp_exporter = OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint
                )
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info(
                    f"OTLP exporter configured: {self.config.otlp_endpoint}"
                )
            except Exception as e:
                logger.warning(f"Failed to configure OTLP exporter: {e}")
                # Continue without OTLP if it fails
                pass

        if self.config.enable_console_exporter:
            try:
                from opentelemetry.exporter.console import ConsoleSpanExporter

                console_exporter = ConsoleSpanExporter()
                self.tracer_provider.add_span_processor(
                    SimpleSpanProcessor(console_exporter)
                )
                logger.info("Console exporter enabled for debugging")
            except ImportError as e:
                logger.warning(f"Console exporter not available: {e}")
                # Continue without console exporter if not available
                pass

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer instance
        self.tracer = trace.get_tracer(
            instrumenting_module_name=__name__,
            instrumenting_library_version="1.0.0",
        )

    def start_turn_span(
        self,
        turn_id: UUID,
        participants: List[str],
        configuration: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> trace.Span:
        """
        Start root span for turn execution.

        Args:
            turn_id: Unique turn identifier
            participants: List of participants
            configuration: Turn configuration
            user_context: Optional user context for security tracing

        Returns:
            Root span for turn execution
        """
        if self.tracer is None:
            raise RuntimeError("Tracer not initialized")

        span = self.tracer.start_span(
            name="novel_engine.turn_execution", kind=trace.SpanKind.SERVER
        )

        # Set core turn attributes
        span.set_attribute("turn.id", str(turn_id))
        span.set_attribute("turn.participants.count", len(participants))
        span.set_attribute("turn.participants", ",".join(participants))
        span.set_attribute(
            "turn.ai_enabled",
            configuration.get("ai_integration_enabled", False),
        )
        span.set_attribute(
            "turn.narrative_depth",
            configuration.get("narrative_analysis_depth", "standard"),
        )
        span.set_attribute(
            "turn.max_execution_time_ms",
            configuration.get("max_execution_time_ms", 60000),
        )

        # Add user context if available (for security tracing)
        if user_context:
            span.set_attribute(
                "user.id", user_context.get("user_id", "anonymous")
            )
            span.set_attribute(
                "user.roles", ",".join(user_context.get("roles", []))
            )

        # Set baggage for cross-context propagation
        baggage.set_baggage("turn.id", str(turn_id))
        baggage.set_baggage("turn.participants_count", str(len(participants)))

        logger.debug(f"Started root turn span: {turn_id}")
        return span

    def start_phase_span(
        self,
        phase_name: str,
        turn_id: UUID,
        phase_order: int,
        parent_span: Optional[trace.Span] = None,
    ) -> trace.Span:
        """
        Start span for individual phase execution.

        Args:
            phase_name: Name of the phase
            turn_id: Turn identifier
            phase_order: Order of phase in pipeline
            parent_span: Parent span (turn execution span)

        Returns:
            Phase execution span
        """
        if self.tracer is None:
            raise RuntimeError("Tracer not initialized")

        # Create span name
        span_name = f"novel_engine.phase.{phase_name}"

        # Start span with parent context
        if parent_span:
            with trace.use_span(parent_span):
                span = self.tracer.start_span(
                    name=span_name, kind=trace.SpanKind.INTERNAL
                )
        else:
            span = self.tracer.start_span(
                name=span_name, kind=trace.SpanKind.INTERNAL
            )

        # Set phase attributes
        span.set_attribute("phase.name", phase_name)
        span.set_attribute("phase.order", phase_order)
        span.set_attribute("turn.id", str(turn_id))

        # Get turn context from baggage
        turn_participants = baggage.get_baggage("turn.participants_count")
        if turn_participants:
            span.set_attribute(
                "turn.participants_count", str(turn_participants)
            )

        logger.debug(f"Started phase span: {phase_name} for turn {turn_id}")
        return span

    def record_phase_result(
        self,
        span: trace.Span,
        success: bool,
        events_processed: int,
        events_generated: int,
        ai_cost: float = 0.0,
        ai_requests: int = 0,
        error_details: Optional[str] = None,
    ) -> None:
        """
        Record phase execution results in span.

        Args:
            span: Phase span
            success: Whether phase succeeded
            events_processed: Number of events processed
            events_generated: Number of events generated
            ai_cost: AI service cost for phase
            ai_requests: Number of AI requests made
            error_details: Error details if phase failed
        """
        span.set_attribute("phase.success", success)
        span.set_attribute("phase.events_processed", events_processed)
        span.set_attribute("phase.events_generated", events_generated)

        if ai_cost > 0:
            span.set_attribute("phase.ai_cost", ai_cost)
            span.set_attribute("phase.ai_requests", ai_requests)

        if not success:
            span.set_status(
                trace.Status(
                    trace.StatusCode.ERROR,
                    error_details or "Phase execution failed",
                )
            )
            if error_details:
                span.set_attribute("phase.error", error_details)
        else:
            span.set_status(trace.Status(trace.StatusCode.OK))

    def record_turn_result(
        self,
        span: trace.Span,
        success: bool,
        execution_time_seconds: float,
        total_ai_cost: float,
        phases_completed: List[str],
        error_details: Optional[str] = None,
    ) -> None:
        """
        Record turn execution results in root span.

        Args:
            span: Turn execution span
            success: Whether turn succeeded
            execution_time_seconds: Total execution time
            total_ai_cost: Total AI service cost
            phases_completed: List of completed phases
            error_details: Error details if turn failed
        """
        span.set_attribute("turn.success", success)
        span.set_attribute(
            "turn.execution_time_seconds", execution_time_seconds
        )
        span.set_attribute("turn.total_cost", total_ai_cost)
        span.set_attribute("turn.phases_completed", ",".join(phases_completed))
        span.set_attribute(
            "turn.completion_percentage", len(phases_completed) / 5.0
        )

        if not success:
            span.set_status(
                trace.Status(
                    trace.StatusCode.ERROR,
                    error_details or "Turn execution failed",
                )
            )
            if error_details:
                span.set_attribute("turn.error", error_details)
        else:
            span.set_status(trace.Status(trace.StatusCode.OK))

    def record_cross_context_call(
        self,
        span: trace.Span,
        target_context: str,
        operation: str,
        success: bool,
        duration_seconds: float,
    ) -> None:
        """
        Record cross-context service call in span.

        Args:
            span: Current span
            target_context: Target context name
            operation: Operation performed
            success: Whether call succeeded
            duration_seconds: Call duration
        """
        span.add_event(
            name="cross_context_call",
            attributes={
                "call.target_context": target_context,
                "call.operation": operation,
                "call.success": success,
                "call.duration_seconds": duration_seconds,
            },
        )

    def get_trace_context(self) -> Dict[str, str]:
        """
        Get current trace context for propagation.

        Returns:
            Trace context headers for HTTP propagation
        """
        carrier: Dict[str, str] = {}
        propagate.inject(carrier)
        return carrier

    def set_trace_context(self, carrier: Dict[str, str]) -> None:
        """
        Set trace context from propagated headers.

        Args:
            carrier: Trace context headers
        """
        propagate.extract(carrier)


def trace_async_operation(operation_name: str, **span_attributes):
    """
    Decorator for tracing async operations.

    Args:
        operation_name: Name of the operation
        **span_attributes: Additional span attributes

    Returns:
        Decorated async function with tracing
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)

            with tracer.start_as_current_span(
                name=operation_name, attributes=span_attributes
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(
                        trace.Status(trace.StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


@asynccontextmanager
async def trace_context(
    operation_name: str, **attributes
) -> AsyncGenerator[trace.Span, None]:
    """
    Async context manager for tracing operations.

    Args:
        operation_name: Name of the operation
        **attributes: Span attributes

    Yields:
        Active span for the operation
    """
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span(
        name=operation_name, attributes=attributes
    ) as span:
        try:
            yield span
            span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


# Global tracer instance
_global_tracer: Optional[NovelEngineTracer] = None


def initialize_tracing(
    config: Optional[NovelEngineTracingConfig] = None,
) -> NovelEngineTracer:
    """
    Initialize global Novel Engine tracer.

    Args:
        config: Optional tracing configuration

    Returns:
        Initialized tracer instance
    """
    global _global_tracer

    if _global_tracer is None:
        if config is None:
            config = NovelEngineTracingConfig()
        _global_tracer = NovelEngineTracer(config)

    return _global_tracer


def get_tracer() -> Optional[NovelEngineTracer]:
    """
    Get global Novel Engine tracer.

    Returns:
        Global tracer instance or None if not initialized
    """
    return _global_tracer
