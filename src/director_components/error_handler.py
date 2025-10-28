"""
System Error Handler
====================

Comprehensive error handling, recovery, and monitoring system.
Provides error classification, recovery strategies, and system resilience.
"""

import asyncio
import hashlib
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type



class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    SYSTEM = "system"
    AGENT = "agent"
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    RESOURCE = "resource"
    LOGIC = "logic"
    EXTERNAL = "external"


class RecoveryStrategy(Enum):
    """Error recovery strategies."""

    IGNORE = "ignore"
    RETRY = "retry"
    FALLBACK = "fallback"
    RESTART = "restart"
    ESCALATE = "escalate"
    SHUTDOWN = "shutdown"


@dataclass
class ErrorPattern:
    """Pattern for error matching and classification."""

    pattern_id: str
    error_types: List[Type[Exception]]
    keywords: List[str]
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    escalation_threshold: int = 5


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    error_id: str
    timestamp: datetime
    exception: Exception
    context: Dict[str, Any]
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    recovery_attempts: int = 0
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class SystemErrorHandler:
    """
    Comprehensive system error handler.

    Features:
    - Error classification and severity assessment
    - Automatic recovery strategies
    - Error pattern learning
    - System health monitoring
    - Escalation procedures
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        # Error storage and tracking
        self._error_records: Dict[str, ErrorRecord] = {}
        self._error_patterns: Dict[str, ErrorPattern] = {}
        self._error_statistics: Dict[str, Any] = {}

        # Recovery functions
        self._recovery_functions: Dict[str, Callable] = {}
        self._fallback_functions: Dict[str, Callable] = {}

        # Configuration
        self._max_error_history = 1000
        self._health_check_interval = 300  # 5 minutes
        self._escalation_cooldown = 3600  # 1 hour

        # System health
        self._system_health = {
            "status": "healthy",
            "error_rate": 0.0,
            "last_critical_error": None,
            "recovery_success_rate": 1.0,
        }

        # Async tracking
        self._error_lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None

        # Error suppression (to prevent spam)
        self._suppressed_errors: Dict[str, datetime] = {}
        self._suppression_duration = 300  # 5 minutes

    async def initialize(self) -> bool:
        """Initialize error handler."""
        try:
            # Define default error patterns
            await self._define_default_error_patterns()

            # Initialize statistics
            self._error_statistics = {
                "total_errors": 0,
                "errors_by_category": {cat.value: 0 for cat in ErrorCategory},
                "errors_by_severity": {sev.value: 0 for sev in ErrorSeverity},
                "recovery_attempts": 0,
                "successful_recoveries": 0,
                "failed_recoveries": 0,
                "last_error_time": None,
            }

            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            self.logger.info("System error handler initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error handler initialization failed: {e}")
            return False

    async def handle_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle system error with classification and recovery.

        Args:
            error: Exception that occurred
            context: Context information about the error

        Returns:
            Dict containing error handling results
        """
        try:
            async with self._error_lock:
                # Generate error ID
                error_id = self._generate_error_id(error, context)

                # Check for error suppression
                if await self._is_error_suppressed(error_id):
                    return {"suppressed": True, "error_id": error_id}

                # Classify error
                classification = await self._classify_error(error, context)

                # Create error record
                error_record = ErrorRecord(
                    error_id=error_id,
                    timestamp=datetime.now(),
                    exception=error,
                    context=context,
                    category=classification["category"],
                    severity=classification["severity"],
                    recovery_strategy=classification["recovery_strategy"],
                )

                # Store error record
                self._error_records[error_id] = error_record

                # Update statistics
                self._update_error_statistics(error_record)

                # Log error
                await self._log_error(error_record)

                # Attempt recovery
                recovery_result = await self._attempt_recovery(error_record)

                # Update system health
                await self._update_system_health(error_record, recovery_result)

                # Check for escalation
                escalation_needed = await self._check_escalation(error_record)

                return {
                    "error_id": error_id,
                    "category": classification["category"].value,
                    "severity": classification["severity"].value,
                    "recovery_attempted": recovery_result["attempted"],
                    "recovery_successful": recovery_result["successful"],
                    "escalation_needed": escalation_needed,
                    "system_health": self._system_health["status"],
                }

        except Exception as handler_error:
            # Meta-error: error handler itself failed
            self.logger.critical(
                f"Error handler failed while handling error: {handler_error}"
            )
            return {"error": "error_handler_failure", "original_error": str(error)}

    async def recover_from_error(self, error_context: Dict[str, Any]) -> bool:
        """
        Attempt to recover from a specific error.

        Args:
            error_context: Error context information

        Returns:
            bool: True if recovery successful
        """
        try:
            error_id = error_context.get("error_id")
            if not error_id or error_id not in self._error_records:
                self.logger.warning(f"Cannot recover from unknown error: {error_id}")
                return False

            error_record = self._error_records[error_id]

            # Attempt recovery based on strategy
            recovery_result = await self._attempt_recovery(error_record)

            if recovery_result["successful"]:
                error_record.resolved = True
                error_record.resolution_time = datetime.now()
                self.logger.info(f"Successfully recovered from error {error_id}")
                return True
            else:
                self.logger.warning(f"Failed to recover from error {error_id}")
                return False

        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
            return False

    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        try:
            async with self._error_lock:
                # Calculate derived statistics
                total_errors = self._error_statistics["total_errors"]
                recovery_rate = 0.0
                if self._error_statistics["recovery_attempts"] > 0:
                    recovery_rate = (
                        self._error_statistics["successful_recoveries"]
                        / self._error_statistics["recovery_attempts"]
                    )

                # Recent error analysis
                recent_cutoff = datetime.now() - timedelta(hours=1)
                recent_errors = [
                    record
                    for record in self._error_records.values()
                    if record.timestamp > recent_cutoff
                ]

                # System health assessment
                health_status = self._assess_system_health()

                return {
                    "total_errors": total_errors,
                    "errors_by_category": self._error_statistics[
                        "errors_by_category"
                    ].copy(),
                    "errors_by_severity": self._error_statistics[
                        "errors_by_severity"
                    ].copy(),
                    "recovery_success_rate": recovery_rate,
                    "recent_error_count": len(recent_errors),
                    "system_health": health_status,
                    "error_patterns_learned": len(self._error_patterns),
                    "active_suppressions": len(self._suppressed_errors),
                    "last_error_time": self._error_statistics["last_error_time"],
                }

        except Exception as e:
            self.logger.error(f"Failed to get error statistics: {e}")
            return {"error": str(e)}

    async def register_recovery_function(
        self, error_category: str, recovery_func: Callable
    ) -> None:
        """Register a recovery function for specific error category."""
        self._recovery_functions[error_category] = recovery_func
        self.logger.info(f"Registered recovery function for category: {error_category}")

    async def register_fallback_function(
        self, context_key: str, fallback_func: Callable
    ) -> None:
        """Register a fallback function for specific context."""
        self._fallback_functions[context_key] = fallback_func
        self.logger.info(f"Registered fallback function for context: {context_key}")

    async def _define_default_error_patterns(self) -> None:
        """Define default error patterns for classification."""
        default_patterns = [
            ErrorPattern(
                pattern_id="connection_error",
                error_types=[ConnectionError, TimeoutError],
                keywords=["connection", "timeout", "network"],
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                retry_delay=2.0,
            ),
            ErrorPattern(
                pattern_id="validation_error",
                error_types=[ValueError, TypeError],
                keywords=["validation", "invalid", "type"],
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                recovery_strategy=RecoveryStrategy.FALLBACK,
            ),
            ErrorPattern(
                pattern_id="resource_error",
                error_types=[MemoryError, OSError],
                keywords=["memory", "resource", "disk"],
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.RESTART,
            ),
            ErrorPattern(
                pattern_id="critical_system_error",
                error_types=[SystemError, RuntimeError],
                keywords=["system", "critical", "fatal"],
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.ESCALATE,
                escalation_threshold=1,
            ),
        ]

        for pattern in default_patterns:
            self._error_patterns[pattern.pattern_id] = pattern

    async def _classify_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify error based on type and context."""
        error_type = type(error)
        error_message = str(error).lower()

        # Find matching pattern
        for pattern in self._error_patterns.values():
            # Check error type match
            if error_type in pattern.error_types:
                return {
                    "category": pattern.category,
                    "severity": pattern.severity,
                    "recovery_strategy": pattern.recovery_strategy,
                    "pattern_id": pattern.pattern_id,
                }

            # Check keyword match
            if any(keyword in error_message for keyword in pattern.keywords):
                return {
                    "category": pattern.category,
                    "severity": pattern.severity,
                    "recovery_strategy": pattern.recovery_strategy,
                    "pattern_id": pattern.pattern_id,
                }

        # Default classification for unknown errors
        return {
            "category": ErrorCategory.SYSTEM,
            "severity": ErrorSeverity.MEDIUM,
            "recovery_strategy": RecoveryStrategy.RETRY,
            "pattern_id": "unknown",
        }

    async def _attempt_recovery(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Attempt error recovery based on strategy."""
        recovery_result = {
            "attempted": True,
            "successful": False,
            "strategy": error_record.recovery_strategy.value,
            "attempts": 0,
        }

        try:
            error_record.recovery_attempts += 1
            self._error_statistics["recovery_attempts"] += 1

            if error_record.recovery_strategy == RecoveryStrategy.IGNORE:
                recovery_result["successful"] = True
                recovery_result["attempted"] = False

            elif error_record.recovery_strategy == RecoveryStrategy.RETRY:
                recovery_result = await self._retry_operation(error_record)

            elif error_record.recovery_strategy == RecoveryStrategy.FALLBACK:
                recovery_result = await self._fallback_operation(error_record)

            elif error_record.recovery_strategy == RecoveryStrategy.RESTART:
                recovery_result = await self._restart_component(error_record)

            elif error_record.recovery_strategy == RecoveryStrategy.ESCALATE:
                recovery_result = await self._escalate_error(error_record)

            elif error_record.recovery_strategy == RecoveryStrategy.SHUTDOWN:
                recovery_result = await self._shutdown_gracefully(error_record)

            if recovery_result["successful"]:
                self._error_statistics["successful_recoveries"] += 1
            else:
                self._error_statistics["failed_recoveries"] += 1

            return recovery_result

        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
            return {
                "attempted": True,
                "successful": False,
                "strategy": error_record.recovery_strategy.value,
                "error": str(e),
            }

    async def _retry_operation(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Retry the failed operation."""
        # Find the pattern for retry configuration
        pattern = None
        for p in self._error_patterns.values():
            if p.category == error_record.category:
                pattern = p
                break

        max_retries = pattern.max_retries if pattern else 3
        retry_delay = pattern.retry_delay if pattern else 1.0

        if error_record.recovery_attempts <= max_retries:
            # Exponential backoff
            delay = retry_delay * (2 ** (error_record.recovery_attempts - 1))
            await asyncio.sleep(delay)

            self.logger.info(
                f"Retrying operation for error {error_record.error_id} (attempt {error_record.recovery_attempts})"
            )

            # In a real implementation, this would re-execute the failed operation
            # For now, we simulate a 70% success rate for retries
            import random

            success = random.random() > 0.3

            return {
                "attempted": True,
                "successful": success,
                "strategy": "retry",
                "attempts": error_record.recovery_attempts,
                "delay": delay,
            }
        else:
            self.logger.warning(
                f"Max retries exceeded for error {error_record.error_id}"
            )
            return {
                "attempted": True,
                "successful": False,
                "strategy": "retry",
                "attempts": error_record.recovery_attempts,
                "reason": "max_retries_exceeded",
            }

    async def _fallback_operation(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Execute fallback operation."""
        context_key = error_record.context.get("operation", "default")

        if context_key in self._fallback_functions:
            try:
                fallback_func = self._fallback_functions[context_key]

                if asyncio.iscoroutinefunction(fallback_func):
                    result = await fallback_func(error_record.context)
                else:
                    result = fallback_func(error_record.context)

                self.logger.info(
                    f"Fallback operation successful for error {error_record.error_id}"
                )
                return {
                    "attempted": True,
                    "successful": True,
                    "strategy": "fallback",
                    "result": result,
                }

            except Exception as e:
                self.logger.error(f"Fallback operation failed: {e}")
                return {
                    "attempted": True,
                    "successful": False,
                    "strategy": "fallback",
                    "error": str(e),
                }
        else:
            self.logger.warning(
                f"No fallback function registered for context: {context_key}"
            )
            return {
                "attempted": False,
                "successful": False,
                "strategy": "fallback",
                "reason": "no_fallback_function",
            }

    async def _restart_component(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Restart affected component."""
        component = error_record.context.get("component", "unknown")

        self.logger.warning(
            f"Restarting component '{component}' due to error {error_record.error_id}"
        )

        # In a real implementation, this would restart the specific component
        # For now, we simulate component restart
        await asyncio.sleep(2.0)  # Simulate restart time

        return {
            "attempted": True,
            "successful": True,
            "strategy": "restart",
            "component": component,
            "restart_time": 2.0,
        }

    async def _escalate_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Escalate error to higher-level handling."""
        self.logger.critical(
            f"Escalating error {error_record.error_id}: {error_record.exception}"
        )

        # Update system health to degraded
        self._system_health["status"] = "degraded"
        self._system_health["last_critical_error"] = error_record.timestamp

        # In a real implementation, this might:
        # - Send alerts to administrators
        # - Trigger failover procedures
        # - Activate monitoring systems

        return {
            "attempted": True,
            "successful": True,  # Escalation itself is successful
            "strategy": "escalate",
            "escalation_time": datetime.now().isoformat(),
        }

    async def _shutdown_gracefully(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Initiate graceful shutdown."""
        self.logger.critical(
            f"Initiating graceful shutdown due to error {error_record.error_id}"
        )

        self._system_health["status"] = "shutting_down"

        # In a real implementation, this would trigger graceful shutdown
        # For now, we just log the intention

        return {
            "attempted": True,
            "successful": True,
            "strategy": "shutdown",
            "shutdown_initiated": datetime.now().isoformat(),
        }

    def _generate_error_id(self, error: Exception, context: Dict[str, Any]) -> str:
        """Generate unique error ID."""
        error_signature = (
            f"{type(error).__name__}_{str(error)}_{context.get('operation', 'unknown')}"
        )
        error_hash = hashlib.md5(error_signature.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"err_{timestamp}_{error_hash}"

    async def _is_error_suppressed(self, error_id: str) -> bool:
        """Check if error should be suppressed to prevent spam."""
        error_signature = error_id.split("_")[-1]  # Get hash part

        if error_signature in self._suppressed_errors:
            suppression_time = self._suppressed_errors[error_signature]
            if datetime.now() - suppression_time < timedelta(
                seconds=self._suppression_duration
            ):
                return True
            else:
                # Remove expired suppression
                del self._suppressed_errors[error_signature]

        # Add to suppression list
        self._suppressed_errors[error_signature] = datetime.now()
        return False

    def _update_error_statistics(self, error_record: ErrorRecord) -> None:
        """Update error statistics."""
        self._error_statistics["total_errors"] += 1
        self._error_statistics["errors_by_category"][error_record.category.value] += 1
        self._error_statistics["errors_by_severity"][error_record.severity.value] += 1
        self._error_statistics["last_error_time"] = error_record.timestamp.isoformat()

    async def _log_error(self, error_record: ErrorRecord) -> None:
        """Log error with appropriate level."""
        log_message = f"Error {error_record.error_id}: {error_record.exception}"

        # Get full traceback
        tb_str = "".join(
            traceback.format_exception(
                type(error_record.exception),
                error_record.exception,
                error_record.exception.__traceback__,
            )
        )

        log_data = {
            "error_id": error_record.error_id,
            "category": error_record.category.value,
            "severity": error_record.severity.value,
            "context": error_record.context,
            "traceback": tb_str,
        }

        if error_record.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra=log_data)
        elif error_record.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra=log_data)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra=log_data)
        else:
            self.logger.info(log_message, extra=log_data)

    async def _update_system_health(
        self, error_record: ErrorRecord, recovery_result: Dict[str, Any]
    ) -> None:
        """Update system health status."""
        # Calculate error rate (errors per hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [
            record
            for record in self._error_records.values()
            if record.timestamp > one_hour_ago
        ]

        self._system_health["error_rate"] = len(recent_errors)

        # Update recovery success rate
        if self._error_statistics["recovery_attempts"] > 0:
            self._system_health["recovery_success_rate"] = (
                self._error_statistics["successful_recoveries"]
                / self._error_statistics["recovery_attempts"]
            )

        # Determine overall health status
        if error_record.severity == ErrorSeverity.CRITICAL:
            self._system_health["status"] = "critical"
        elif self._system_health["error_rate"] > 20:  # More than 20 errors per hour
            self._system_health["status"] = "degraded"
        elif self._system_health["recovery_success_rate"] < 0.5:
            self._system_health["status"] = "degraded"
        else:
            self._system_health["status"] = "healthy"

    async def _check_escalation(self, error_record: ErrorRecord) -> bool:
        """Check if error needs escalation."""
        # Find pattern for escalation threshold
        pattern = None
        for p in self._error_patterns.values():
            if p.category == error_record.category:
                pattern = p
                break

        if not pattern:
            return False

        # Check if threshold reached
        similar_errors = [
            record
            for record in self._error_records.values()
            if (
                record.category == error_record.category
                and record.timestamp > datetime.now() - timedelta(hours=1)
            )
        ]

        return len(similar_errors) >= pattern.escalation_threshold

    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health."""
        return {
            "status": self._system_health["status"],
            "error_rate": self._system_health["error_rate"],
            "recovery_success_rate": self._system_health["recovery_success_rate"],
            "last_critical_error": (
                self._system_health["last_critical_error"].isoformat()
                if self._system_health["last_critical_error"]
                else None
            ),
            "total_error_records": len(self._error_records),
            "active_patterns": len(self._error_patterns),
        }

    async def _health_check_loop(self) -> None:
        """Periodic system health check."""
        try:
            while True:
                await asyncio.sleep(self._health_check_interval)

                # Cleanup old error records
                await self._cleanup_old_errors()

                # Clear expired suppressions
                current_time = datetime.now()
                expired_suppressions = [
                    signature
                    for signature, suppression_time in self._suppressed_errors.items()
                    if current_time - suppression_time
                    > timedelta(seconds=self._suppression_duration * 2)
                ]

                for signature in expired_suppressions:
                    del self._suppressed_errors[signature]

                self.logger.debug("System health check completed")

        except asyncio.CancelledError:
            self.logger.info("Health check loop cancelled")
        except Exception as e:
            self.logger.error(f"Health check loop error: {e}")

    async def _cleanup_old_errors(self) -> None:
        """Cleanup old error records."""
        if len(self._error_records) > self._max_error_history:
            # Keep most recent errors
            sorted_errors = sorted(
                self._error_records.items(), key=lambda x: x[1].timestamp, reverse=True
            )

            # Keep most recent errors
            keep_errors = dict(sorted_errors[: self._max_error_history])
            self._error_records = keep_errors

            self.logger.debug(
                f"Cleaned up old error records, kept {len(keep_errors)} most recent"
            )

    async def cleanup(self) -> None:
        """Cleanup error handler resources."""
        try:
            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Clear data structures
            self._error_records.clear()
            self._suppressed_errors.clear()

            self.logger.info("System error handler cleanup completed")

        except Exception as e:
            self.logger.error(f"Error handler cleanup error: {e}")
