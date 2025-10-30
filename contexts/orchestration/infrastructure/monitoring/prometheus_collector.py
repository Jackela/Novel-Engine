#!/usr/bin/env python3
"""
Prometheus Metrics Collector

Comprehensive business metrics collection for Novel Engine Turn Orchestration system.
Implements the core KPIs requested in M10: llm_cost_per_req and turn_duration_seconds,
along with extended metrics for complete observability.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
    )
except ImportError as prometheus_error:  # pragma: no cover - exercised in dependency-light env
    logging.getLogger(__name__).warning(
        "prometheus_client unavailable (%s); using no-op collectors.", prometheus_error
    )

    class _NoOpMetric:
        def __init__(self, *_, **__):
            pass

        def labels(self, *_, **__):
            return self

        def inc(self, *_, **__):
            return self

        def dec(self, *_, **__):
            return self

        def observe(self, *_, **__):
            return self

        def set(self, *_, **__):
            return self

        def info(self, *_, **__):
            return self

        def time(self):
            class _Timer:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Timer()

    class CollectorRegistry:  # type: ignore[override]
        def __init__(self, *_, **__):
            pass

    Counter = Gauge = Histogram = Info = _NoOpMetric  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest(_registry) -> bytes:
        return b""

logger = logging.getLogger(__name__)


class PrometheusMetricsCollector:
    """
    Comprehensive Prometheus metrics collector for Novel Engine turn orchestration.

    Provides enterprise-grade monitoring with business KPIs, performance metrics,
    and operational observability integrated with the existing PerformanceTracker.

    Key Features:
    - Core business metrics: llm_cost_per_req, turn_duration_seconds
    - Phase-level performance tracking
    - AI integration cost and efficiency monitoring
    - Saga pattern compensation tracking
    - Resource utilization monitoring
    - Error tracking and alerting
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize Prometheus metrics collector.

        Args:
            registry: Optional custom registry (defaults to global registry)
        """
        self.registry = registry or CollectorRegistry()
        self._initialize_core_metrics()
        self._initialize_business_metrics()
        self._initialize_operational_metrics()

        logger.info(
            "PrometheusMetricsCollector initialized with comprehensive metric suite"
        )

    def _initialize_core_metrics(self) -> None:
        """Initialize core business metrics requested in M10 milestone."""

        # Core KPI 1: LLM cost per request (requested metric)
        self.llm_cost_per_request = Gauge(
            "novel_engine_llm_cost_per_request_dollars",
            "AI/LLM cost per turn execution request in USD",
            ["phase", "model_type", "success", "narrative_depth"],
            registry=self.registry,
        )

        # Core KPI 2: Turn duration (requested metric)
        self.turn_duration_seconds = Histogram(
            "novel_engine_turn_duration_seconds",
            "Turn execution duration in seconds",
            ["phase", "participants_count", "ai_enabled", "success"],
            buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0, 120.0, float("inf")],
            registry=self.registry,
        )

        # Total turns executed counter
        self.turns_total = Counter(
            "novel_engine_turns_total",
            "Total number of turn executions",
            ["status", "participants_range", "ai_enabled"],
            registry=self.registry,
        )

        # Currently active turns
        self.turns_active = Gauge(
            "novel_engine_turns_active",
            "Number of currently executing turns",
            registry=self.registry,
        )

    def _initialize_business_metrics(self) -> None:
        """Initialize extended business metrics for comprehensive monitoring."""

        # Phase-specific performance metrics
        self.phase_duration_seconds = Histogram(
            "novel_engine_phase_duration_seconds",
            "Individual phase execution duration",
            ["phase_type", "success", "participants_count"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")],
            registry=self.registry,
        )

        self.phase_events_processed = Counter(
            "novel_engine_phase_events_processed_total",
            "Total events processed by phase",
            ["phase_type", "event_type", "success"],
            registry=self.registry,
        )

        # AI integration metrics
        self.ai_requests_total = Counter(
            "novel_engine_ai_requests_total",
            "Total AI/LLM requests made",
            ["provider", "model", "phase", "status"],
            registry=self.registry,
        )

        self.ai_token_usage_total = Counter(
            "novel_engine_ai_token_usage_total",
            "Total AI tokens consumed",
            ["provider", "model", "token_type"],
            registry=self.registry,
        )

        self.ai_cost_total = Counter(
            "novel_engine_ai_cost_total_dollars",
            "Total AI service costs in USD",
            ["provider", "model", "phase"],
            registry=self.registry,
        )

        # AI efficiency metrics
        self.ai_cost_efficiency = Gauge(
            "novel_engine_ai_cost_efficiency_events_per_dollar",
            "AI cost efficiency: events processed per dollar spent",
            ["phase", "model"],
            registry=self.registry,
        )

        # Saga pattern metrics
        self.compensations_total = Counter(
            "novel_engine_compensations_total",
            "Total compensation actions executed",
            ["compensation_type", "success", "rollback_reason"],
            registry=self.registry,
        )

        self.compensation_duration_seconds = Histogram(
            "novel_engine_compensation_duration_seconds",
            "Compensation action execution duration",
            ["compensation_type"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, float("inf")],
            registry=self.registry,
        )

        # Business outcome metrics
        self.turn_success_rate = Gauge(
            "novel_engine_turn_success_rate",
            "Turn execution success rate (rolling window)",
            ["time_window"],
            registry=self.registry,
        )

        self.narrative_quality_score = Histogram(
            "novel_engine_narrative_quality_score",
            "AI-generated narrative quality score (0-1)",
            ["phase", "depth"],
            buckets=[0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
            registry=self.registry,
        )

    def _initialize_operational_metrics(self) -> None:
        """Initialize operational and resource metrics."""

        # Resource utilization
        self.memory_usage_bytes = Gauge(
            "novel_engine_memory_usage_bytes",
            "Memory usage during turn execution",
            ["component"],
            registry=self.registry,
        )

        self.cpu_usage_percent = Gauge(
            "novel_engine_cpu_usage_percent",
            "CPU usage percentage during operations",
            ["component"],
            registry=self.registry,
        )

        self.concurrent_operations = Gauge(
            "novel_engine_concurrent_operations",
            "Number of concurrent operations",
            ["operation_type"],
            registry=self.registry,
        )

        # Cross-context integration metrics
        self.cross_context_calls_total = Counter(
            "novel_engine_cross_context_calls_total",
            "Total cross-context service calls",
            ["target_context", "operation", "status"],
            registry=self.registry,
        )

        self.cross_context_call_duration_seconds = Histogram(
            "novel_engine_cross_context_call_duration_seconds",
            "Cross-context call duration",
            ["target_context", "operation"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, float("inf")],
            registry=self.registry,
        )

        # Error tracking
        self.errors_total = Counter(
            "novel_engine_errors_total",
            "Total errors by type and severity",
            ["error_type", "severity", "component"],
            registry=self.registry,
        )

        self.error_recovery_attempts = Counter(
            "novel_engine_error_recovery_attempts_total",
            "Error recovery attempts",
            ["error_type", "recovery_strategy", "success"],
            registry=self.registry,
        )

        # Performance baselines
        self.performance_baseline_info = Info(
            "novel_engine_performance_baselines",
            "Performance baseline targets for alerting",
            registry=self.registry,
        )

        # Set baseline information
        self.performance_baseline_info.info(
            {
                "target_execution_time_ms": "25000",
                "target_success_rate": "0.95",
                "target_cost_per_turn": "2.00",
                "target_ai_efficiency": "0.8",
            }
        )

    # Metrics Recording Methods

    def record_turn_start(
        self,
        turn_id: UUID,
        participants_count: int,
        ai_enabled: bool,
        configuration: Dict[str, Any],
    ) -> None:
        """
        Record turn execution start.

        Args:
            turn_id: Unique turn identifier
            participants_count: Number of participants in turn
            ai_enabled: Whether AI integration is enabled
            configuration: Turn configuration details
        """
        # Increment active turns
        self.turns_active.inc()

        logger.debug(
            f"Turn {turn_id} started - participants: {participants_count}, AI: {ai_enabled}"
        )

    def record_turn_completion(
        self,
        turn_id: UUID,
        participants_count: int,
        ai_enabled: bool,
        success: bool,
        execution_time_seconds: float,
        total_ai_cost: Decimal,
        phase_results: Dict[str, Any],
    ) -> None:
        """
        Record turn execution completion with comprehensive metrics.

        Args:
            turn_id: Unique turn identifier
            participants_count: Number of participants
            ai_enabled: Whether AI integration was enabled
            success: Whether turn execution was successful
            execution_time_seconds: Total execution time
            total_ai_cost: Total AI service costs
            phase_results: Individual phase execution results
        """
        # Core business metrics
        participants_range = self._get_participants_range(participants_count)

        # Record turn duration (Core KPI)
        self.turn_duration_seconds.labels(
            phase="complete",
            participants_count=participants_range,
            ai_enabled=str(ai_enabled).lower(),
            success=str(success).lower(),
        ).observe(execution_time_seconds)

        # Record LLM cost per request (Core KPI)
        if ai_enabled and total_ai_cost > 0:
            self.llm_cost_per_request.labels(
                phase="total",
                model_type="gpt-4",  # Could be derived from actual model used
                success=str(success).lower(),
                narrative_depth="standard",  # Could be from configuration
            ).set(float(total_ai_cost))

        # Turn completion counter
        self.turns_total.labels(
            status="success" if success else "error",
            participants_range=participants_range,
            ai_enabled=str(ai_enabled).lower(),
        ).inc()

        # Decrement active turns
        self.turns_active.dec()

        # Record phase-specific metrics if available
        for phase_name, phase_result in phase_results.items():
            self._record_phase_metrics(
                phase_name=phase_name,
                phase_result=phase_result,
                participants_count=participants_count,
            )

        logger.info(
            f"Turn {turn_id} completed - success: {success}, "
            f"duration: {execution_time_seconds:.2f}s, cost: ${total_ai_cost:.2f}"
        )

    def record_phase_execution(
        self,
        phase_name: str,
        participants_count: int,
        success: bool,
        execution_time_seconds: float,
        events_processed: int,
        events_generated: int,
        ai_cost: Decimal = Decimal("0"),
        ai_requests: int = 0,
        ai_tokens: int = 0,
    ) -> None:
        """
        Record individual phase execution metrics.

        Args:
            phase_name: Name of the executed phase
            participants_count: Number of participants
            success: Whether phase execution was successful
            execution_time_seconds: Phase execution time
            events_processed: Number of events processed
            events_generated: Number of events generated
            ai_cost: AI service cost for this phase
            ai_requests: Number of AI requests made
            ai_tokens: Number of AI tokens consumed
        """
        participants_range = self._get_participants_range(participants_count)

        # Phase duration
        self.phase_duration_seconds.labels(
            phase_type=phase_name,
            success=str(success).lower(),
            participants_count=participants_range,
        ).observe(execution_time_seconds)

        # Events processed
        if events_processed > 0:
            self.phase_events_processed.labels(
                phase_type=phase_name,
                event_type="processed",
                success=str(success).lower(),
            ).inc(events_processed)

        if events_generated > 0:
            self.phase_events_processed.labels(
                phase_type=phase_name,
                event_type="generated",
                success=str(success).lower(),
            ).inc(events_generated)

        # AI metrics
        if ai_cost > 0:
            self.ai_cost_total.labels(
                provider="openai", model="gpt-4", phase=phase_name
            ).inc(float(ai_cost))

            # AI efficiency calculation
            if events_processed > 0 and ai_cost > 0:
                efficiency = events_processed / float(ai_cost)
                self.ai_cost_efficiency.labels(phase=phase_name, model="gpt-4").set(
                    efficiency
                )

        if ai_requests > 0:
            self.ai_requests_total.labels(
                provider="openai",
                model="gpt-4",
                phase=phase_name,
                status="success" if success else "error",
            ).inc(ai_requests)

        if ai_tokens > 0:
            self.ai_token_usage_total.labels(
                provider="openai", model="gpt-4", token_type="total"
            ).inc(ai_tokens)

    def record_compensation_execution(
        self,
        compensation_type: str,
        success: bool,
        execution_time_seconds: float,
        rollback_reason: str = "unknown",
    ) -> None:
        """
        Record saga compensation execution.

        Args:
            compensation_type: Type of compensation action
            success: Whether compensation was successful
            execution_time_seconds: Compensation execution time
            rollback_reason: Reason for rollback requirement
        """
        self.compensations_total.labels(
            compensation_type=compensation_type,
            success=str(success).lower(),
            rollback_reason=rollback_reason,
        ).inc()

        self.compensation_duration_seconds.labels(
            compensation_type=compensation_type
        ).observe(execution_time_seconds)

    def record_error(
        self,
        error_type: str,
        severity: str,
        component: str,
        recovery_attempted: bool = False,
        recovery_success: bool = False,
    ) -> None:
        """
        Record error occurrence and recovery attempts.

        Args:
            error_type: Classification of error
            severity: Error severity level
            component: Component where error occurred
            recovery_attempted: Whether error recovery was attempted
            recovery_success: Whether recovery was successful
        """
        self.errors_total.labels(
            error_type=error_type, severity=severity, component=component
        ).inc()

        if recovery_attempted:
            self.error_recovery_attempts.labels(
                error_type=error_type,
                recovery_strategy="automatic",
                success=str(recovery_success).lower(),
            ).inc()

    def record_resource_usage(
        self, component: str, memory_bytes: int, cpu_percent: float
    ) -> None:
        """
        Record resource utilization metrics.

        Args:
            component: Component name
            memory_bytes: Memory usage in bytes
            cpu_percent: CPU usage percentage
        """
        self.memory_usage_bytes.labels(component=component).set(memory_bytes)
        self.cpu_usage_percent.labels(component=component).set(cpu_percent)

    def record_cross_context_call(
        self,
        target_context: str,
        operation: str,
        success: bool,
        duration_seconds: float,
    ) -> None:
        """
        Record cross-context service calls.

        Args:
            target_context: Target context name
            operation: Operation performed
            success: Whether call was successful
            duration_seconds: Call duration
        """
        self.cross_context_calls_total.labels(
            target_context=target_context,
            operation=operation,
            status="success" if success else "error",
        ).inc()

        self.cross_context_call_duration_seconds.labels(
            target_context=target_context, operation=operation
        ).observe(duration_seconds)

    def update_success_rate(self, time_window: str, success_rate: float) -> None:
        """
        Update success rate gauge for alerting.

        Args:
            time_window: Time window for success rate calculation
            success_rate: Success rate (0-1)
        """
        self.turn_success_rate.labels(time_window=time_window).set(success_rate)

    def get_metrics_data(self) -> str:
        """
        Get Prometheus metrics data for /metrics endpoint.

        Returns:
            Metrics data in Prometheus format
        """
        return generate_latest(self.registry)

    def get_metrics_content_type(self) -> str:
        """
        Get content type for metrics response.

        Returns:
            Prometheus metrics content type
        """
        return CONTENT_TYPE_LATEST

    # Helper methods

    def _get_participants_range(self, count: int) -> str:
        """
        Convert participants count to range for metrics labeling.

        Args:
            count: Number of participants

        Returns:
            Participants count range string
        """
        if count == 1:
            return "1"
        elif count <= 3:
            return "2-3"
        elif count <= 5:
            return "4-5"
        elif count <= 10:
            return "6-10"
        else:
            return "10+"

    def _record_phase_metrics(
        self, phase_name: str, phase_result: Dict[str, Any], participants_count: int
    ) -> None:
        """
        Record metrics from phase result data.

        Args:
            phase_name: Name of the phase
            phase_result: Phase execution result data
            participants_count: Number of participants
        """
        success = phase_result.get("success", False)
        duration_ms = phase_result.get("execution_time_ms", 0)
        events_processed = phase_result.get("events_processed", 0)
        events_generated = phase_result.get("events_generated", 0)
        ai_cost = Decimal(str(phase_result.get("ai_cost", 0)))

        self.record_phase_execution(
            phase_name=phase_name,
            participants_count=participants_count,
            success=success,
            execution_time_seconds=duration_ms / 1000,
            events_processed=events_processed,
            events_generated=events_generated,
            ai_cost=ai_cost,
        )
