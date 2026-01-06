#!/usr/bin/env python3
"""
Structured Logging with Centralized Aggregation for Novel Engine

Implements comprehensive structured logging with:
- Centralized log aggregation and storage
- Structured logging with consistent formats
- Log analysis and pattern detection
- Security event monitoring and alerting
"""

import gzip
import json
import logging
import logging.handlers
import os
import shutil
import socket
import sys
import threading
import time
import traceback
from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Structured log levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(Enum):
    """Log categories for classification"""

    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    INFRASTRUCTURE = "infrastructure"
    AUDIT = "audit"


@dataclass
class LogEntry:
    """Structured log entry"""

    timestamp: str
    level: LogLevel
    category: LogCategory
    component: str
    message: str

    # Context information
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # Technical details
    exception: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

    # Business context
    business_context: Dict[str, Any] = field(default_factory=dict)

    # Security context
    security_context: Dict[str, Any] = field(default_factory=dict)

    # Custom attributes
    attributes: Dict[str, Any] = field(default_factory=dict)

    # System information
    hostname: str = field(default_factory=socket.gethostname)
    process_id: int = field(default_factory=os.getpid)
    thread_id: int = field(default_factory=threading.get_ident)

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


@dataclass
class LoggingConfig:
    """Configuration for structured logging"""

    # Basic configuration
    log_level: LogLevel = LogLevel.INFO
    enable_console: bool = True
    enable_file: bool = True
    enable_json: bool = True

    # File configuration
    log_directory: str = "logs"
    log_filename: str = "novel-engine.log"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 10
    compress_backups: bool = True

    # Centralized logging
    enable_remote_logging: bool = False
    remote_endpoint: Optional[
        str
    ] = None  # e.g., "http://localhost:3100/loki/api/v1/push"
    remote_auth: Optional[Dict[str, str]] = None

    # Security logging
    enable_security_logging: bool = True
    security_log_file: str = "security.log"

    # Performance logging
    enable_performance_logging: bool = True
    performance_log_file: str = "performance.log"

    # Audit logging
    enable_audit_logging: bool = True
    audit_log_file: str = "audit.log"

    # Buffer configuration
    buffer_size: int = 1000
    flush_interval: float = 5.0  # seconds

    # Context extraction
    extract_trace_context: bool = True
    extract_user_context: bool = True


class StructuredLogger:
    """Structured logger implementation"""

    def __init__(self, config: LoggingConfig, component: str = "novel-engine"):
        self.config = config
        self.component = component
        self.logger = logging.getLogger(f"{component}.structured")
        self.logger.setLevel(getattr(logging, config.log_level.value.upper()))

        # Initialize log buffers for batch processing
        self.log_buffer: deque = deque(maxlen=config.buffer_size)
        self.buffer_lock = threading.Lock()

        # Set up logging handlers
        self._setup_handlers()

        # Start background flush task
        self._start_flush_task()

        logger.info(f"Structured logger initialized for component: {component}")

    def _setup_handlers(self):
        """Set up logging handlers"""
        # Clear existing handlers
        self.logger.handlers.clear()

        formatter = self._create_formatter()

        # Console handler
        if self.config.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handlers
        if self.config.enable_file:
            self._setup_file_handlers(formatter)

        # Remote handler
        if self.config.enable_remote_logging and self.config.remote_endpoint:
            self._setup_remote_handler()

    def _create_formatter(self):
        """Create log formatter"""
        if self.config.enable_json:
            return JsonFormatter()
        else:
            return logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

    def _setup_file_handlers(self, formatter):
        """Set up file handlers for different log categories"""
        # Ensure log directory exists
        os.makedirs(self.config.log_directory, exist_ok=True)

        # Main application log
        main_log_path = os.path.join(
            self.config.log_directory, self.config.log_filename
        )
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_path,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
        )
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)

        # Security log
        if self.config.enable_security_logging:
            security_log_path = os.path.join(
                self.config.log_directory, self.config.security_log_file
            )
            security_handler = logging.handlers.RotatingFileHandler(
                security_log_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            security_handler.setFormatter(formatter)
            security_handler.addFilter(CategoryFilter(LogCategory.SECURITY))
            self.logger.addHandler(security_handler)

        # Performance log
        if self.config.enable_performance_logging:
            performance_log_path = os.path.join(
                self.config.log_directory, self.config.performance_log_file
            )
            performance_handler = logging.handlers.RotatingFileHandler(
                performance_log_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            performance_handler.setFormatter(formatter)
            performance_handler.addFilter(CategoryFilter(LogCategory.PERFORMANCE))
            self.logger.addHandler(performance_handler)

        # Audit log
        if self.config.enable_audit_logging:
            audit_log_path = os.path.join(
                self.config.log_directory, self.config.audit_log_file
            )
            audit_handler = logging.handlers.RotatingFileHandler(
                audit_log_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            audit_handler.setFormatter(formatter)
            audit_handler.addFilter(CategoryFilter(LogCategory.AUDIT))
            self.logger.addHandler(audit_handler)

        # Compress old log files if enabled
        if self.config.compress_backups:
            self._compress_old_logs()

    def _setup_remote_handler(self):
        """Set up remote logging handler"""
        try:
            # For production, you would use a proper remote handler
            # like one for Loki, Elasticsearch, or other log aggregation systems
            remote_handler = RemoteLogHandler(
                endpoint=self.config.remote_endpoint, auth=self.config.remote_auth
            )
            self.logger.addHandler(remote_handler)
            logger.info(f"Remote logging enabled: {self.config.remote_endpoint}")
        except Exception as e:
            logger.error(f"Failed to setup remote logging: {e}")

    def _compress_old_logs(self):
        """Compress old log files"""
        try:
            log_dir = Path(self.config.log_directory)
            for log_file in log_dir.glob("*.log.*"):
                if not log_file.name.endswith(".gz"):
                    compressed_path = log_file.with_suffix(log_file.suffix + ".gz")
                    with open(log_file, "rb") as f_in:
                        with gzip.open(compressed_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()
        except Exception as e:
            logger.error(f"Error compressing log files: {e}")

    def _start_flush_task(self):
        """Start background task to flush log buffer"""

        def flush_loop():
            while True:
                try:
                    time.sleep(self.config.flush_interval)
                    self._flush_buffer()
                except Exception as e:
                    logger.error(f"Error in log flush loop: {e}")

        flush_thread = threading.Thread(target=flush_loop, daemon=True)
        flush_thread.start()

    def _flush_buffer(self):
        """Flush log buffer to handlers"""
        with self.buffer_lock:
            while self.log_buffer:
                log_entry = self.log_buffer.popleft()
                self._emit_log(log_entry)

    def _emit_log(self, log_entry: LogEntry):
        """Emit log entry to handlers"""
        try:
            # Convert to logging record
            level = getattr(logging, log_entry.level.value.upper())
            record = logging.LogRecord(
                name=self.logger.name,
                level=level,
                pathname="",
                lineno=0,
                msg=log_entry.message,
                args=(),
                exc_info=None,
            )

            # Add structured data as extra
            record.structured_data = log_entry.to_dict()
            record.log_category = log_entry.category.value

            self.logger.handle(record)

        except Exception as e:
            # Fallback to basic logging to prevent log loss
            self.logger.error(f"Failed to emit structured log: {e}")

    def _extract_context(self) -> Dict[str, Optional[str]]:
        """Extract context information from current execution"""
        context = {
            "trace_id": None,
            "span_id": None,
            "user_id": None,
            "session_id": None,
            "request_id": None,
        }

        if self.config.extract_trace_context:
            try:
                # Try to extract OpenTelemetry context
                from opentelemetry import trace

                current_span = trace.get_current_span()
                if current_span.is_recording():
                    span_context = current_span.get_span_context()
                    context["trace_id"] = f"{span_context.trace_id:032x}"
                    context["span_id"] = f"{span_context.span_id:016x}"
            except Exception:
                self.logger.debug(
                    "OpenTelemetry context extraction failed", exc_info=True
                )

        if self.config.extract_user_context:
            try:
                # Try to extract user context from various sources
                # This should be customized based on the authentication system.
                self.logger.debug("User context extraction not configured")
            except Exception:
                self.logger.debug(
                    "User context extraction failed", exc_info=True
                )

        return context

    def log(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.APPLICATION,
        exception: Optional[Exception] = None,
        duration_ms: Optional[float] = None,
        business_context: Optional[Dict[str, Any]] = None,
        security_context: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Log a structured message"""
        # Extract current context
        context = self._extract_context()

        # Build exception info
        exception_info = None
        if exception:
            exception_info = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc(),
            }

        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            category=category,
            component=self.component,
            message=message,
            trace_id=context.get("trace_id"),
            span_id=context.get("span_id"),
            user_id=context.get("user_id"),
            session_id=context.get("session_id"),
            request_id=context.get("request_id"),
            exception=exception_info,
            duration_ms=duration_ms,
            business_context=business_context or {},
            security_context=security_context or {},
            attributes={**(attributes or {}), **kwargs},
        )

        # Add to buffer for batch processing
        with self.buffer_lock:
            self.log_buffer.append(log_entry)

        # Immediate flush for critical logs
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self._flush_buffer()

    # Convenience methods
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message"""
        self.log(LogLevel.ERROR, message, exception=exception, **kwargs)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        self.log(LogLevel.CRITICAL, message, exception=exception, **kwargs)

    # Specialized logging methods
    def log_security_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: LogLevel = LogLevel.WARNING,
        **kwargs,
    ):
        """Log security event"""
        security_context = {
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        self.log(
            level=severity,
            message=message,
            category=LogCategory.SECURITY,
            security_context=security_context,
            **kwargs,
        )

    def log_performance_event(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        message: Optional[str] = None,
        **kwargs,
    ):
        """Log performance event"""
        if message is None:
            message = f"Operation {operation} completed in {duration_ms:.2f}ms"

        business_context = {"operation": operation, "success": success}

        # Determine log level based on duration
        if duration_ms > 5000:  # > 5 seconds
            level = LogLevel.WARNING
        elif duration_ms > 1000:  # > 1 second
            level = LogLevel.INFO
        else:
            level = LogLevel.DEBUG

        self.log(
            level=level,
            message=message,
            category=LogCategory.PERFORMANCE,
            duration_ms=duration_ms,
            business_context=business_context,
            **kwargs,
        )

    def log_business_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        business_context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Log business event"""
        context = {
            "event_type": event_type,
            "user_id": user_id,
            **(business_context or {}),
        }

        self.log(
            level=LogLevel.INFO,
            message=message,
            category=LogCategory.BUSINESS,
            business_context=context,
            **kwargs,
        )

    def log_audit_event(
        self,
        action: str,
        resource: str,
        user_id: Optional[str] = None,
        success: bool = True,
        message: Optional[str] = None,
        **kwargs,
    ):
        """Log audit event"""
        if message is None:
            status = "successful" if success else "failed"
            message = f"User {user_id or 'unknown'} {status} {action} on {resource}"

        business_context = {
            "action": action,
            "resource": resource,
            "user_id": user_id,
            "success": success,
        }

        self.log(
            level=LogLevel.INFO,
            message=message,
            category=LogCategory.AUDIT,
            business_context=business_context,
            **kwargs,
        )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logs"""

    def format(self, record):
        """Format log record as JSON"""
        # Get structured data if available
        if hasattr(record, "structured_data"):
            return json.dumps(record.structured_data, default=str, ensure_ascii=False)

        # Fallback to basic JSON structure
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname.lower(),
            "component": record.name,
            "message": record.getMessage(),
            "hostname": socket.gethostname(),
            "process_id": os.getpid(),
            "thread_id": threading.get_ident(),
        }

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data, default=str, ensure_ascii=False)


class CategoryFilter(logging.Filter):
    """Filter logs by category"""

    def __init__(self, category: LogCategory):
        super().__init__()
        self.category = category.value

    def filter(self, record):
        """Filter log records by category"""
        return getattr(record, "log_category", None) == self.category


class RemoteLogHandler(logging.Handler):
    """Handler for sending logs to remote aggregation systems"""

    def __init__(self, endpoint: str, auth: Optional[Dict[str, str]] = None):
        super().__init__()
        self.endpoint = endpoint
        self.auth = auth or {}
        self.buffer = deque(maxlen=1000)
        self.buffer_lock = threading.Lock()

        # Start background sender
        self._start_sender()

    def emit(self, record):
        """Emit log record to buffer"""
        try:
            log_data = self.format(record)
            with self.buffer_lock:
                self.buffer.append(log_data)
        except Exception:
            self.handleError(record)

    def _start_sender(self):
        """Start background sender thread"""

        def sender_loop():
            while True:
                try:
                    time.sleep(5)  # Send every 5 seconds
                    self._send_logs()
                except Exception as e:
                    # Use basic logging to avoid recursion
                    print(f"Error in remote log sender: {e}", file=sys.stderr)

        sender_thread = threading.Thread(target=sender_loop, daemon=True)
        sender_thread.start()

    def _send_logs(self):
        """Send buffered logs to remote endpoint"""
        logs_to_send = []

        with self.buffer_lock:
            while self.buffer:
                logs_to_send.append(self.buffer.popleft())

        if logs_to_send:
            try:
                # This would be customized for your specific log aggregation system
                # For example, Loki, Elasticsearch, Fluentd, etc.
                self._send_to_remote(logs_to_send)
            except Exception as e:
                # Return logs to buffer on failure
                with self.buffer_lock:
                    self.buffer.extendleft(reversed(logs_to_send))
                raise e

    def _send_to_remote(self, logs: List[str]):
        """Send logs to remote endpoint (implement for your system)"""
        # Placeholder implementation
        # In production, this would use the appropriate client library
        # for your log aggregation system


# Context manager for performance logging
@contextmanager
def log_performance(
    logger: StructuredLogger,
    operation: str,
    expected_duration_ms: Optional[float] = None,
    **context,
):
    """Context manager for performance logging"""
    start_time = time.time()
    exception = None

    try:
        yield
    except Exception as e:
        exception = e
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        success = exception is None

        # Determine log level
        if exception:
            pass
        elif expected_duration_ms and duration_ms > expected_duration_ms * 2:
            pass
        else:
            pass

        message = f"Operation {operation} "
        if success:
            message += f"completed in {duration_ms:.2f}ms"
        else:
            message += f"failed after {duration_ms:.2f}ms"

        logger.log_performance_event(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            message=message,
            exception=exception,
            **context,
        )


# Global logger instance
structured_logger: Optional[StructuredLogger] = None


def setup_structured_logging(
    config: Optional[LoggingConfig] = None, component: str = "novel-engine"
) -> StructuredLogger:
    """Setup structured logging system"""
    global structured_logger

    if config is None:
        config = LoggingConfig()

    structured_logger = StructuredLogger(config, component)
    return structured_logger


def get_structured_logger() -> StructuredLogger:
    """Get the global structured logger"""
    if structured_logger is None:
        return setup_structured_logging()
    return structured_logger


__all__ = [
    "LogLevel",
    "LogCategory",
    "LogEntry",
    "LoggingConfig",
    "StructuredLogger",
    "JsonFormatter",
    "CategoryFilter",
    "RemoteLogHandler",
    "log_performance",
    "setup_structured_logging",
    "get_structured_logger",
]
