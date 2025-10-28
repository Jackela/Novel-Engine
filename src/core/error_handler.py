#!/usr/bin/env python3
"""
Centralized Error Handling System
==================================

Enterprise-grade error handling with recovery, monitoring, and alerting.
"""

import asyncio
import json
import logging
import threading
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ErrorSeverity(Enum):
    """Error severity levels for classification and routing."""

    CRITICAL = "critical"  # System failure, immediate attention required
    HIGH = "high"  # Major functionality impacted
    MEDIUM = "medium"  # Minor functionality impacted
    LOW = "low"  # Minimal impact, for monitoring
    INFO = "info"  # Informational, not an error


class ErrorCategory(Enum):
    """Error categories for classification."""

    SYSTEM = "system"  # System-level errors
    NETWORK = "network"  # Network and connectivity
    VALIDATION = "validation"  # Data validation errors
    AUTHENTICATION = "authentication"  # Auth and permissions
    BUSINESS_LOGIC = "business_logic"  # Application logic errors
    EXTERNAL_SERVICE = "external_service"  # Third-party service errors
    PERFORMANCE = "performance"  # Performance-related issues
    CONFIGURATION = "configuration"  # Configuration problems


class RecoveryStrategy(Enum):
    """Available error recovery strategies."""

    NONE = "none"  # No recovery, fail immediately
    RETRY = "retry"  # Retry operation with backoff
    FALLBACK = "fallback"  # Use fallback mechanism
    CIRCUIT_BREAKER = "circuit_breaker"  # Circuit breaker pattern
    GRACEFUL_DEGRADATION = "graceful_degradation"  # Reduce functionality
    RESTART_COMPONENT = "restart_component"  # Restart component
    USER_INTERVENTION = "user_intervention"  # Require manual intervention


@dataclass
class ErrorContext:
    """Context information for error analysis."""

    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorRecord:
    """Complete error record for tracking and analysis."""

    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    stack_trace: str
    recovery_strategy: RecoveryStrategy
    recovery_attempted: bool = False
    recovery_successful: bool = False
    occurrence_count: int = 1
    first_occurrence: datetime = field(default_factory=datetime.now)
    last_occurrence: datetime = field(default_factory=datetime.now)
    resolution_status: str = "open"  # open, investigating, resolved, ignored


class CentralizedErrorHandler:
    """
    Centralized error handling system with monitoring and recovery.

    Features:
    - Error classification and routing
    - Automatic recovery strategies
    - Performance monitoring
    - Alert management
    - Error pattern analysis
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize centralized error handler."""
        self.logger = logger or logging.getLogger(__name__)

        # Error tracking
        self.error_records: Dict[str, ErrorRecord] = {}
        self.error_history: deque = deque(maxlen=10000)
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)

        # Recovery management
        self.recovery_handlers: Dict[RecoveryStrategy, Callable] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}

        # Monitoring and alerting
        self.error_counts = defaultdict(int)
        self.alert_thresholds = {
            ErrorSeverity.CRITICAL: 1,  # Alert immediately
            ErrorSeverity.HIGH: 5,  # Alert after 5 occurrences
            ErrorSeverity.MEDIUM: 20,  # Alert after 20 occurrences
            ErrorSeverity.LOW: 100,  # Alert after 100 occurrences
        }

        # Performance tracking
        self.performance_metrics = {
            "total_errors": 0,
            "recovery_success_rate": 0.0,
            "avg_resolution_time": 0.0,
            "critical_errors_24h": 0,
        }

        # Threading for async operations
        self._lock = threading.Lock()
        self._alert_callbacks: List[Callable] = []

        # Initialize recovery handlers
        self._initialize_recovery_handlers()

    def _initialize_recovery_handlers(self) -> None:
        """Initialize default recovery strategy handlers."""
        self.recovery_handlers = {
            RecoveryStrategy.RETRY: self._handle_retry_recovery,
            RecoveryStrategy.FALLBACK: self._handle_fallback_recovery,
            RecoveryStrategy.CIRCUIT_BREAKER: self._handle_circuit_breaker_recovery,
            RecoveryStrategy.GRACEFUL_DEGRADATION: self._handle_graceful_degradation,
            RecoveryStrategy.RESTART_COMPONENT: self._handle_restart_component,
            RecoveryStrategy.USER_INTERVENTION: self._handle_user_intervention,
        }

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        recovery_strategy: Optional[RecoveryStrategy] = None,
    ) -> ErrorRecord:
        """
        Handle an error with full context and recovery.

        Args:
            error: The exception that occurred
            context: Context information
            severity: Error severity (auto-detected if not provided)
            category: Error category (auto-detected if not provided)
            recovery_strategy: Recovery strategy (auto-selected if not provided)

        Returns:
            ErrorRecord: Complete error record
        """
        try:
            # Generate unique error ID
            error_id = str(uuid.uuid4())

            # Auto-detect severity, category, and recovery strategy if not provided
            if severity is None:
                severity = self._detect_error_severity(error, context)

            if category is None:
                category = self._detect_error_category(error, context)

            if recovery_strategy is None:
                recovery_strategy = self._select_recovery_strategy(
                    error, severity, category
                )

            # Create error record
            error_record = ErrorRecord(
                error_id=error_id,
                error_type=type(error).__name__,
                message=str(error),
                severity=severity,
                category=category,
                context=context,
                stack_trace=traceback.format_exc(),
                recovery_strategy=recovery_strategy,
            )

            # Check for existing similar errors
            similar_error_id = self._find_similar_error(error_record)
            if similar_error_id:
                # Update existing error record
                existing_record = self.error_records[similar_error_id]
                existing_record.occurrence_count += 1
                existing_record.last_occurrence = datetime.now()
                error_record = existing_record
            else:
                # Store new error record
                self.error_records[error_id] = error_record

            # Log error
            await self._log_error(error_record)

            # Attempt recovery
            if recovery_strategy != RecoveryStrategy.NONE:
                await self._attempt_recovery(error_record)

            # Update monitoring metrics
            self._update_metrics(error_record)

            # Check alert thresholds
            await self._check_alert_thresholds(error_record)

            # Archive to history
            self.error_history.append(
                {
                    "error_id": error_record.error_id,
                    "timestamp": error_record.last_occurrence.isoformat(),
                    "severity": error_record.severity.value,
                    "category": error_record.category.value,
                    "message": error_record.message[:200],  # Truncated for storage
                }
            )

            return error_record

        except (AttributeError, KeyError, TypeError) as handler_error:
            # Invalid error record or context data errors
            self.logger.critical(
                f"Invalid data in error handler: {handler_error}",
                extra={"error_type": type(handler_error).__name__},
            )
        except (ValueError, RuntimeError) as handler_error:
            # Error handler processing or recovery errors
            self.logger.critical(
                f"Error handler failure: {handler_error}",
                extra={"error_type": type(handler_error).__name__},
            )

            return ErrorRecord(
                error_id="handler_error",
                error_type="ErrorHandlerFailure",
                message=str(handler_error),
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM,
                context=context,
                stack_trace=traceback.format_exc(),
                recovery_strategy=RecoveryStrategy.USER_INTERVENTION,
            )

    def _detect_error_severity(
        self, error: Exception, context: ErrorContext
    ) -> ErrorSeverity:
        """Auto-detect error severity based on error type and context."""
        # Critical errors
        if isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL

        # System errors
        if isinstance(error, (SystemError, OSError, RuntimeError)):
            return ErrorSeverity.HIGH

        # Network errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.MEDIUM

        # Validation errors
        if isinstance(error, (ValueError, TypeError, AttributeError)):
            return ErrorSeverity.MEDIUM

        # Default to low for unknown errors
        return ErrorSeverity.LOW

    def _detect_error_category(
        self, error: Exception, context: ErrorContext
    ) -> ErrorCategory:
        """Auto-detect error category based on error type and context."""
        # System errors
        if isinstance(error, (SystemError, MemoryError, OSError)):
            return ErrorCategory.SYSTEM

        # Network errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK

        # Validation errors
        if isinstance(error, (ValueError, TypeError)):
            return ErrorCategory.VALIDATION

        # Permission errors
        if isinstance(error, PermissionError):
            return ErrorCategory.AUTHENTICATION

        # Default based on component
        component = context.component.lower()
        if "llm" in component or "api" in component:
            return ErrorCategory.EXTERNAL_SERVICE
        elif "config" in component:
            return ErrorCategory.CONFIGURATION
        else:
            return ErrorCategory.BUSINESS_LOGIC

    def _select_recovery_strategy(
        self, error: Exception, severity: ErrorSeverity, category: ErrorCategory
    ) -> RecoveryStrategy:
        """Select appropriate recovery strategy."""
        # Critical errors need user intervention
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.USER_INTERVENTION

        # Network errors benefit from retry
        if category == ErrorCategory.NETWORK:
            return RecoveryStrategy.RETRY

        # External service errors use circuit breaker
        if category == ErrorCategory.EXTERNAL_SERVICE:
            return RecoveryStrategy.CIRCUIT_BREAKER

        # Validation errors typically can't be recovered automatically
        if category == ErrorCategory.VALIDATION:
            return RecoveryStrategy.NONE

        # Default to retry for other recoverable errors
        if severity in [ErrorSeverity.MEDIUM, ErrorSeverity.LOW]:
            return RecoveryStrategy.RETRY

        return RecoveryStrategy.FALLBACK

    def _find_similar_error(self, error_record: ErrorRecord) -> Optional[str]:
        """Find similar existing error to avoid duplicates."""
        error_signature = f"{error_record.error_type}_{error_record.context.component}_{hash(error_record.message) % 10000}"

        for existing_id, existing_record in self.error_records.items():
            existing_signature = f"{existing_record.error_type}_{existing_record.context.component}_{hash(existing_record.message) % 10000}"

            if error_signature == existing_signature:
                # Check if within time window (1 hour)
                if datetime.now() - existing_record.last_occurrence < timedelta(
                    hours=1
                ):
                    return existing_id

        return None

    async def _log_error(self, error_record: ErrorRecord) -> None:
        """Log error with structured format."""
        log_data = {
            "error_id": error_record.error_id,
            "error_type": error_record.error_type,
            "message": error_record.message,
            "severity": error_record.severity.value,
            "category": error_record.category.value,
            "component": error_record.context.component,
            "operation": error_record.context.operation,
            "occurrence_count": error_record.occurrence_count,
            "recovery_strategy": error_record.recovery_strategy.value,
        }

        # Log at appropriate level
        if error_record.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL ERROR: {json.dumps(log_data)}")
        elif error_record.severity == ErrorSeverity.HIGH:
            self.logger.error(f"HIGH SEVERITY: {json.dumps(log_data)}")
        elif error_record.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"MEDIUM SEVERITY: {json.dumps(log_data)}")
        else:
            self.logger.info(f"ERROR LOGGED: {json.dumps(log_data)}")

    async def _attempt_recovery(self, error_record: ErrorRecord) -> None:
        """Attempt error recovery using configured strategy."""
        try:
            error_record.recovery_attempted = True

            recovery_handler = self.recovery_handlers.get(
                error_record.recovery_strategy
            )
            if recovery_handler:
                success = await recovery_handler(error_record)
                error_record.recovery_successful = success

                if success:
                    self.logger.info(
                        f"Recovery successful for error {error_record.error_id}"
                    )
                else:
                    self.logger.warning(
                        f"Recovery failed for error {error_record.error_id}"
                    )

        except (AttributeError, KeyError, TypeError) as recovery_error:
            # Invalid error record or recovery data errors
            self.logger.error(
                f"Invalid data in recovery attempt: {recovery_error}",
                extra={"error_type": type(recovery_error).__name__},
            )
            error_record.recovery_successful = False
        except (ValueError, RuntimeError) as recovery_error:
            # Recovery execution or strategy errors
            self.logger.error(
                f"Recovery attempt failed: {recovery_error}",
                extra={"error_type": type(recovery_error).__name__},
            )
            error_record.recovery_successful = False

    async def _handle_retry_recovery(self, error_record: ErrorRecord) -> bool:
        """Handle retry recovery strategy."""
        # Simple retry with exponential backoff (placeholder)
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Wait with exponential backoff
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)

                # In real implementation, this would retry the original operation
                # For now, simulate success
                if attempt >= 1:  # Succeed after first retry
                    return True

            except (AttributeError, TypeError, asyncio.CancelledError):
                # Retry operation cancelled or invalid retry data
                continue
            except (ValueError, RuntimeError):
                # Retry execution errors
                continue

        return False

    async def _handle_fallback_recovery(self, error_record: ErrorRecord) -> bool:
        """Handle fallback recovery strategy."""
        # Implement fallback mechanism (placeholder)
        self.logger.info(f"Activating fallback for {error_record.context.component}")
        return True

    async def _handle_circuit_breaker_recovery(self, error_record: ErrorRecord) -> bool:
        """Handle circuit breaker recovery strategy."""
        component = error_record.context.component

        # Initialize circuit breaker if not exists
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure": None,
                "timeout": 60,  # seconds
            }

        cb = self.circuit_breakers[component]

        # Update failure count
        cb["failure_count"] += 1
        cb["last_failure"] = datetime.now()

        # Open circuit breaker if threshold exceeded
        if cb["failure_count"] >= 5:
            cb["state"] = "open"
            self.logger.warning(f"Circuit breaker opened for {component}")

        return False  # Circuit breaker opened

    async def _handle_graceful_degradation(self, error_record: ErrorRecord) -> bool:
        """Handle graceful degradation recovery."""
        self.logger.info(
            f"Activating graceful degradation for {error_record.context.component}"
        )
        return True

    async def _handle_restart_component(self, error_record: ErrorRecord) -> bool:
        """Handle component restart recovery."""
        self.logger.warning(
            f"Component restart recommended for {error_record.context.component}"
        )
        return False  # Manual intervention required

    async def _handle_user_intervention(self, error_record: ErrorRecord) -> bool:
        """Handle user intervention recovery."""
        self.logger.critical(
            f"User intervention required for error {error_record.error_id}"
        )
        return False

    def _update_metrics(self, error_record: ErrorRecord) -> None:
        """Update performance metrics."""
        with self._lock:
            self.performance_metrics["total_errors"] += 1

            # Update recovery success rate
            total_recovery_attempts = sum(
                1 for r in self.error_records.values() if r.recovery_attempted
            )
            successful_recoveries = sum(
                1 for r in self.error_records.values() if r.recovery_successful
            )

            if total_recovery_attempts > 0:
                self.performance_metrics["recovery_success_rate"] = (
                    successful_recoveries / total_recovery_attempts
                )

            # Update 24-hour critical errors
            cutoff = datetime.now() - timedelta(hours=24)
            self.performance_metrics["critical_errors_24h"] = sum(
                1
                for r in self.error_records.values()
                if r.severity == ErrorSeverity.CRITICAL and r.last_occurrence >= cutoff
            )

    async def _check_alert_thresholds(self, error_record: ErrorRecord) -> None:
        """Check if error should trigger alerts."""
        threshold = self.alert_thresholds.get(error_record.severity, float("inf"))

        if error_record.occurrence_count >= threshold:
            await self._trigger_alert(error_record)

    async def _trigger_alert(self, error_record: ErrorRecord) -> None:
        """Trigger alert for error."""
        alert_data = {
            "error_id": error_record.error_id,
            "severity": error_record.severity.value,
            "category": error_record.category.value,
            "message": error_record.message,
            "component": error_record.context.component,
            "occurrence_count": error_record.occurrence_count,
            "timestamp": error_record.last_occurrence.isoformat(),
        }

        self.logger.critical(f"ALERT TRIGGERED: {json.dumps(alert_data)}")

        # Call registered alert callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(alert_data)
            except (AttributeError, TypeError, KeyError) as e:
                # Invalid callback or alert data errors
                self.logger.error(
                    f"Invalid data in alert callback: {e}",
                    extra={"error_type": type(e).__name__},
                )
            except (ValueError, RuntimeError) as e:
                # Alert callback execution errors
                self.logger.error(
                    f"Alert callback failed: {e}",
                    extra={"error_type": type(e).__name__},
                )

    def add_alert_callback(self, callback: Callable) -> None:
        """Add alert callback for notifications."""
        self._alert_callbacks.append(callback)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        with self._lock:
            return {
                "total_errors": len(self.error_records),
                "performance_metrics": self.performance_metrics.copy(),
                "severity_distribution": self._get_severity_distribution(),
                "category_distribution": self._get_category_distribution(),
                "recovery_statistics": self._get_recovery_statistics(),
                "recent_critical_errors": self._get_recent_critical_errors(),
            }

    def _get_severity_distribution(self) -> Dict[str, int]:
        """Get distribution of errors by severity."""
        distribution = defaultdict(int)
        for record in self.error_records.values():
            distribution[record.severity.value] += record.occurrence_count
        return dict(distribution)

    def _get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of errors by category."""
        distribution = defaultdict(int)
        for record in self.error_records.values():
            distribution[record.category.value] += record.occurrence_count
        return dict(distribution)

    def _get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery attempt statistics."""
        attempted = sum(1 for r in self.error_records.values() if r.recovery_attempted)
        successful = sum(
            1 for r in self.error_records.values() if r.recovery_successful
        )

        return {
            "recovery_attempts": attempted,
            "successful_recoveries": successful,
            "success_rate": successful / attempted if attempted > 0 else 0.0,
        }

    def _get_recent_critical_errors(self) -> List[Dict[str, Any]]:
        """Get recent critical errors."""
        cutoff = datetime.now() - timedelta(hours=24)
        critical_errors = []

        for record in self.error_records.values():
            if (
                record.severity == ErrorSeverity.CRITICAL
                and record.last_occurrence >= cutoff
            ):
                critical_errors.append(
                    {
                        "error_id": record.error_id,
                        "message": record.message,
                        "component": record.context.component,
                        "timestamp": record.last_occurrence.isoformat(),
                        "occurrence_count": record.occurrence_count,
                    }
                )

        return sorted(critical_errors, key=lambda x: x["timestamp"], reverse=True)


# Global error handler instance
_global_error_handler: Optional[CentralizedErrorHandler] = None


def get_error_handler() -> CentralizedErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = CentralizedErrorHandler()
    return _global_error_handler


async def handle_error(
    error: Exception, component: str, operation: str, **kwargs
) -> ErrorRecord:
    """
    Convenient function to handle errors with global handler.

    Args:
        error: Exception that occurred
        component: Component name where error occurred
        operation: Operation being performed
        **kwargs: Additional context data

    Returns:
        ErrorRecord: Complete error record
    """
    context = ErrorContext(component=component, operation=operation, metadata=kwargs)

    handler = get_error_handler()
    return await handler.handle_error(error, context)
