#!/usr/bin/env python3
"""
Structured Logging System
==========================

Enterprise-grade structured logging with performance monitoring and audit trails.
"""

import asyncio
import json
import logging
import logging.handlers
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class LogLevel(Enum):
    """Enhanced log levels for structured logging."""

    TRACE = "TRACE"  # Detailed execution flow
    DEBUG = "DEBUG"  # Debug information
    INFO = "INFO"  # General information
    SUCCESS = "SUCCESS"  # Success operations
    WARNING = "WARNING"  # Warning conditions
    ERROR = "ERROR"  # Error conditions
    CRITICAL = "CRITICAL"  # Critical failures
    AUDIT = "AUDIT"  # Audit trail
    PERFORMANCE = "PERFORMANCE"  # Performance metrics
    SECURITY = "SECURITY"  # Security events


class LogCategory(Enum):
    """Log categories for organization and filtering."""

    SYSTEM = "system"  # System operations
    APPLICATION = "application"  # Application logic
    SECURITY = "security"  # Security events
    PERFORMANCE = "performance"  # Performance metrics
    AUDIT = "audit"  # Audit trails
    USER = "user"  # User actions
    API = "api"  # API requests/responses
    DATABASE = "database"  # Database operations
    INTEGRATION = "integration"  # External integrations
    BUSINESS = "business"  # Business logic


@dataclass
class LogContext:
    """Context information for structured logging."""

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: str
    level: LogLevel
    category: LogCategory
    message: str
    context: LogContext
    duration_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "context": asdict(self.context),
            "duration_ms": self.duration_ms,
            "error_details": self.error_details,
            "performance_metrics": self.performance_metrics,
        }


class PerformanceTracker:
    """Tracks performance metrics for operations."""

    def __init__(self, operation: str, context: Optional[LogContext] = None):
        """Initialize performance tracker."""
        self.operation = operation
        self.context = context or LogContext()
        self.start_time = time.time()
        self.metrics: Dict[str, Any] = {}

    def add_metric(self, name: str, value: Any) -> None:
        """Add a performance metric."""
        self.metrics[name] = value

    def finish(self, logger: "StructuredLogger") -> float:
        """Finish tracking and log performance metrics."""
        duration = (time.time() - self.start_time) * 1000  # Convert to ms

        logger.performance(
            f"Operation '{self.operation}' completed",
            context=self.context,
            duration_ms=duration,
            performance_metrics=self.metrics,
        )

        return duration

    def __enter__(self) -> "PerformanceTracker":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        # Get logger from thread local or create new one
        logger = getattr(threading.current_thread(), "_structured_logger", None)
        if logger:
            self.finish(logger)


class StructuredLogger:
    """
    Structured logging with context, performance tracking, and audit trails.

    Features:
    - Structured JSON logging
    - Context propagation
    - Performance tracking
    - Audit trail support
    - Multiple output formats
    - Log aggregation and analytics
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize structured logger."""
        self.name = name
        self.config = config or {}

        # Core logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, self.config.get("level", "INFO")))

        # Context management
        self._context_stack: List[LogContext] = []
        self._thread_local = threading.local()

        # Performance tracking
        self.performance_metrics: deque = deque(maxlen=10000)
        self.operation_stats = defaultdict(list)

        # Audit trail
        self.audit_trail: deque = deque(maxlen=50000)

        # Formatters and handlers
        self._setup_handlers()

        # Thread local logger reference
        threading.current_thread()._structured_logger = self

    def _setup_handlers(self) -> None:
        """Setup log handlers based on configuration."""
        if self._logger.handlers:
            return  # Already configured

        # Console handler with structured format
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = StructuredFormatter(
            format_type=self.config.get("console_format", "readable")
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

        # File handler for structured logs
        log_dir = Path(self.config.get("log_dir", "logs"))
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{self.name}.jsonl",
            maxBytes=self.config.get("max_file_size", 10 * 1024 * 1024),  # 10MB
            backupCount=self.config.get("backup_count", 5),
        )

        file_formatter = StructuredFormatter(format_type="json")
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

        # Audit file handler
        if self.config.get("enable_audit", True):
            audit_handler = logging.handlers.RotatingFileHandler(
                log_dir / f"{self.name}_audit.jsonl",
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=10,
            )
            audit_handler.addFilter(AuditFilter())
            audit_handler.setFormatter(StructuredFormatter(format_type="json"))
            self._logger.addHandler(audit_handler)

    def push_context(self, context: LogContext) -> None:
        """Push context onto context stack."""
        self._context_stack.append(context)

    def pop_context(self) -> Optional[LogContext]:
        """Pop context from context stack."""
        return self._context_stack.pop() if self._context_stack else None

    def get_current_context(self) -> Optional[LogContext]:
        """Get current context."""
        return self._context_stack[-1] if self._context_stack else None

    def _log(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.APPLICATION,
        context: Optional[LogContext] = None,
        duration_ms: Optional[float] = None,
        error_details: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal logging method."""
        # Use provided context or current context
        log_context = context or self.get_current_context() or LogContext()

        # Create structured log entry
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            category=category,
            message=message,
            context=log_context,
            duration_ms=duration_ms,
            error_details=error_details,
            performance_metrics=performance_metrics,
        )

        # Store for analytics
        if level == LogLevel.PERFORMANCE:
            self.performance_metrics.append(entry.to_dict())

        if level == LogLevel.AUDIT or category == LogCategory.AUDIT:
            self.audit_trail.append(entry.to_dict())

        # Log using standard logger
        log_level = self._map_to_standard_level(level)
        extra = {"structured_data": entry.to_dict()}
        self._logger.log(log_level, message, extra=extra)

    def _map_to_standard_level(self, level: LogLevel) -> int:
        """Map custom log levels to standard logging levels."""
        mapping = {
            LogLevel.TRACE: logging.DEBUG,
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.SUCCESS: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
            LogLevel.AUDIT: logging.INFO,
            LogLevel.PERFORMANCE: logging.INFO,
            LogLevel.SECURITY: logging.WARNING,
        }
        return mapping.get(level, logging.INFO)

    # Convenience methods for different log levels

    def trace(self, message: str, **kwargs) -> None:
        """Log trace level message."""
        self._log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug level message."""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info level message."""
        self._log(LogLevel.INFO, message, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        """Log success message."""
        self._log(LogLevel.SUCCESS, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message with optional exception details."""
        error_details = None
        if error:
            error_details = {
                "type": type(error).__name__,
                "message": str(error),
                "args": error.args,
            }

        self._log(LogLevel.ERROR, message, error_details=error_details, **kwargs)

    def critical(
        self, message: str, error: Optional[Exception] = None, **kwargs
    ) -> None:
        """Log critical message with optional exception details."""
        error_details = None
        if error:
            error_details = {
                "type": type(error).__name__,
                "message": str(error),
                "args": error.args,
            }

        self._log(LogLevel.CRITICAL, message, error_details=error_details, **kwargs)

    def audit(self, message: str, **kwargs) -> None:
        """Log audit trail message."""
        kwargs["category"] = LogCategory.AUDIT
        self._log(LogLevel.AUDIT, message, **kwargs)

    def performance(self, message: str, **kwargs) -> None:
        """Log performance metric."""
        kwargs["category"] = LogCategory.PERFORMANCE
        self._log(LogLevel.PERFORMANCE, message, **kwargs)

    def security(self, message: str, **kwargs) -> None:
        """Log security event."""
        kwargs["category"] = LogCategory.SECURITY
        self._log(LogLevel.SECURITY, message, **kwargs)

    # Performance tracking methods

    def track_performance(
        self, operation: str, context: Optional[LogContext] = None
    ) -> PerformanceTracker:
        """Create performance tracker for operation."""
        return PerformanceTracker(operation, context or self.get_current_context())

    def time_operation(self, operation: str, context: Optional[LogContext] = None):
        """Decorator/context manager for timing operations."""

        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                with self.track_performance(operation, context):
                    return await func(*args, **kwargs)

            def sync_wrapper(*args, **kwargs):
                with self.track_performance(operation, context):
                    return func(*args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    # Analytics and reporting

    def get_performance_summary(
        self, operation_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get performance metrics summary."""
        relevant_metrics = []

        for entry in self.performance_metrics:
            if operation_filter is None or operation_filter in entry.get(
                "context", {}
            ).get("operation", ""):
                relevant_metrics.append(entry)

        if not relevant_metrics:
            return {"message": "No performance data available"}

        durations = [m.get("duration_ms", 0) for m in relevant_metrics]

        return {
            "operation_filter": operation_filter,
            "total_operations": len(relevant_metrics),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "total_duration_ms": sum(durations),
        }

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit trail entries."""
        return list(self.audit_trail)[-limit:]

    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging system statistics."""
        return {
            "performance_entries": len(self.performance_metrics),
            "audit_entries": len(self.audit_trail),
            "context_stack_depth": len(self._context_stack),
            "handlers_configured": len(self._logger.handlers),
            "current_log_level": self._logger.level,
        }


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logs."""

    def __init__(self, format_type: str = "json"):
        """Initialize formatter."""
        super().__init__()
        self.format_type = format_type

    def format(self, record: logging.LogRecord) -> str:
        """Format log record."""
        if hasattr(record, "structured_data"):
            if self.format_type == "json":
                return json.dumps(record.structured_data)
            else:
                # Readable format for console
                data = record.structured_data
                timestamp = data.get("timestamp", "")
                level = data.get("level", "")
                component = data.get("context", {}).get("component") or "unknown"
                message = data.get("message", "")

                # Ensure component is a string for formatting
                component_str = str(component) if component is not None else "unknown"

                base_msg = f"[{timestamp}] {level:12} {component_str:15} {message}"

                # Add duration if available
                if data.get("duration_ms"):
                    base_msg += f" ({data['duration_ms']:.1f}ms)"

                return base_msg
        else:
            # Fallback to standard formatting
            return super().format(record)


class AuditFilter(logging.Filter):
    """Filter for audit trail logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter audit records."""
        if hasattr(record, "structured_data"):
            data = record.structured_data
            return data.get("level") == "AUDIT" or data.get("category") == "audit"
        return False


class LoggerFactory:
    """Factory for creating structured loggers."""

    _loggers: Dict[str, StructuredLogger] = {}
    _default_config: Dict[str, Any] = {
        "level": "INFO",
        "console_format": "readable",
        "log_dir": "logs",
        "max_file_size": 10 * 1024 * 1024,
        "backup_count": 5,
        "enable_audit": True,
    }

    @classmethod
    def get_logger(
        cls, name: str, config: Optional[Dict[str, Any]] = None
    ) -> StructuredLogger:
        """Get or create structured logger."""
        if name not in cls._loggers:
            final_config = cls._default_config.copy()
            if config:
                final_config.update(config)

            cls._loggers[name] = StructuredLogger(name, final_config)

        return cls._loggers[name]

    @classmethod
    def configure_defaults(cls, config: Dict[str, Any]) -> None:
        """Configure default settings for all loggers."""
        cls._default_config.update(config)

    @classmethod
    def get_all_loggers(cls) -> Dict[str, StructuredLogger]:
        """Get all created loggers."""
        return cls._loggers.copy()


# Context manager for logging context
class LoggingContext:
    """Context manager for structured logging context."""

    def __init__(self, logger: StructuredLogger, context: LogContext):
        """Initialize logging context."""
        self.logger = logger
        self.context = context

    def __enter__(self) -> LogContext:
        """Enter context."""
        self.logger.push_context(self.context)
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        self.logger.pop_context()


# Convenience functions
def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """Get structured logger instance."""
    return LoggerFactory.get_logger(name, config)


def with_context(logger: StructuredLogger, **context_data) -> LoggingContext:
    """Create logging context with given data."""
    context = LogContext()
    for key, value in context_data.items():
        if hasattr(context, key):
            setattr(context, key, value)
        else:
            context.metadata[key] = value

    return LoggingContext(logger, context)
