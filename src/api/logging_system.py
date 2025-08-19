#!/usr/bin/env python3
"""
Comprehensive Logging and Observability System.

Provides structured logging, distributed tracing, and comprehensive observability
for production API operations with security and performance monitoring.
"""

import logging
import json
import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import traceback
import sys
from contextlib import contextmanager
from collections import deque

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

class LogLevel(str, Enum):
    """Enhanced log levels."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"
    AUDIT = "AUDIT"

class LogCategory(str, Enum):
    """Log categorization for better organization."""
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_ACTION = "user_action"
    BUSINESS_LOGIC = "business_logic"
    INTEGRATION = "integration"
    ERROR = "error"

@dataclass
class LogContext:
    """Structured log context information."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    environment: str = "development"
    api_version: Optional[str] = None
    additional_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StructuredLogEntry:
    """Structured log entry for consistent formatting."""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    logger_name: str
    context: LogContext
    duration_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    security_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "logger": self.logger_name,
            "context": asdict(self.context),
            "duration_ms": self.duration_ms,
            "error_details": self.error_details,
            "performance_metrics": self.performance_metrics,
            "security_context": self.security_context
        }
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)

class PerformanceTracker:
    """Track performance metrics for operations."""
    
    def __init__(self):
        self.active_operations: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start_operation(self, operation_id: str) -> str:
        """Start tracking an operation."""
        with self._lock:
            self.active_operations[operation_id] = time.time()
        return operation_id
    
    def end_operation(self, operation_id: str) -> Optional[float]:
        """End tracking an operation and return duration in milliseconds."""
        with self._lock:
            start_time = self.active_operations.pop(operation_id, None)
            if start_time:
                return (time.time() - start_time) * 1000
        return None

class SecurityLogger:
    """Specialized logging for security events."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.security_events = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def log_security_event(
        self,
        event_type: str,
        severity: LogLevel,
        message: str,
        context: LogContext,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log a security event with proper context."""
        
        security_context = {
            "event_type": event_type,
            "severity": severity.value,
            "client_ip": context.additional_fields.get("client_ip"),
            "user_agent": context.additional_fields.get("user_agent"),
            "endpoint": context.additional_fields.get("endpoint"),
            "method": context.additional_fields.get("method"),
            "details": details or {}
        }
        
        log_entry = StructuredLogEntry(
            timestamp=datetime.now(),
            level=severity,
            category=LogCategory.SECURITY,
            message=message,
            logger_name="security",
            context=context,
            security_context=security_context
        )
        
        # Store security event
        with self._lock:
            self.security_events.append(log_entry)
        
        # Log to main logger
        self.logger.log(
            getattr(logging, severity.value),
            log_entry.to_json()
        )
    
    def get_recent_security_events(self, limit: int = 100) -> List[StructuredLogEntry]:
        """Get recent security events."""
        with self._lock:
            return list(self.security_events)[-limit:]

class AuditLogger:
    """Specialized logging for audit trails."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.audit_trail = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def log_audit_event(
        self,
        action: str,
        resource: str,
        context: LogContext,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event."""
        
        audit_context = {
            "action": action,
            "resource": resource,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "user_id": context.user_id,
            "session_id": context.session_id,
            "details": details or {}
        }
        
        log_entry = StructuredLogEntry(
            timestamp=datetime.now(),
            level=LogLevel.AUDIT,
            category=LogCategory.USER_ACTION,
            message=f"AUDIT: {action} on {resource} - {outcome}",
            logger_name="audit",
            context=context,
            additional_fields=audit_context
        )
        
        # Store audit event
        with self._lock:
            self.audit_trail.append(log_entry)
        
        # Log to main logger
        self.logger.info(log_entry.to_json())

class StructuredLogger:
    """Main structured logging system."""
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        output_format: str = "json",
        log_file: Optional[str] = None
    ):
        self.name = name
        self.level = level
        self.output_format = output_format
        self.performance_tracker = PerformanceTracker()
        
        # Setup Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup formatters and handlers
        self._setup_handlers(log_file)
        
        # Specialized loggers
        self.security_logger = SecurityLogger(self.logger)
        self.audit_logger = AuditLogger(self.logger)
        
        # Thread-local storage for context
        self._context_storage = threading.local()
    
    def _setup_handlers(self, log_file: Optional[str]):
        """Setup log handlers with appropriate formatters."""
        
        if self.output_format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def set_context(self, context: LogContext):
        """Set logging context for current thread."""
        self._context_storage.context = context
    
    def get_context(self) -> LogContext:
        """Get current logging context."""
        return getattr(self._context_storage, 'context', LogContext())
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for temporary logging context."""
        old_context = self.get_context()
        new_context = LogContext(**{**asdict(old_context), **kwargs})
        self.set_context(new_context)
        try:
            yield new_context
        finally:
            self.set_context(old_context)
    
    def _create_log_entry(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        duration_ms: Optional[float] = None,
        error_details: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> StructuredLogEntry:
        """Create a structured log entry."""
        
        context = self.get_context()
        context.additional_fields.update(kwargs)
        
        return StructuredLogEntry(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            logger_name=self.name,
            context=context,
            duration_ms=duration_ms,
            error_details=error_details,
            performance_metrics=performance_metrics
        )
    
    def log(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        **kwargs
    ):
        """Log a message with structured format."""
        
        log_entry = self._create_log_entry(level, category, message, **kwargs)
        
        if self.output_format == "json":
            log_message = log_entry.to_json()
        else:
            log_message = message
        
        python_level = getattr(logging, level.value)
        self.logger.log(python_level, log_message)
    
    def trace(self, message: str, **kwargs):
        """Log trace level message."""
        self.log(LogLevel.TRACE, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info level message."""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log error level message with optional exception info."""
        
        error_details = None
        if exc_info:
            error_details = {
                "exception_type": type(exc_info).__name__,
                "exception_message": str(exc_info),
                "traceback": traceback.format_exc()
            }
        
        log_entry = self._create_log_entry(
            LogLevel.ERROR,
            LogCategory.ERROR,
            message,
            error_details=error_details,
            **kwargs
        )
        
        if self.output_format == "json":
            log_message = log_entry.to_json()
        else:
            log_message = message
        
        self.logger.error(log_message, exc_info=exc_info if exc_info else False)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log critical level message."""
        self.error(message, exc_info, **kwargs)
        self.log(LogLevel.CRITICAL, message, LogCategory.ERROR, **kwargs)
    
    def performance(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log performance metrics."""
        
        performance_metrics = {
            "operation": operation,
            "duration_ms": duration_ms,
            "details": details or {}
        }
        
        log_entry = self._create_log_entry(
            LogLevel.INFO,
            LogCategory.PERFORMANCE,
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            performance_metrics=performance_metrics
        )
        
        if self.output_format == "json":
            log_message = log_entry.to_json()
        else:
            log_message = f"Performance: {operation} completed in {duration_ms:.2f}ms"
        
        self.logger.info(log_message)
    
    @contextmanager
    def performance_context(self, operation: str):
        """Context manager for performance tracking."""
        operation_id = str(uuid.uuid4())
        self.performance_tracker.start_operation(operation_id)
        
        try:
            yield
        finally:
            duration_ms = self.performance_tracker.end_operation(operation_id)
            if duration_ms is not None:
                self.performance(operation, duration_ms)
    
    def security_event(
        self,
        event_type: str,
        severity: LogLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log a security event."""
        context = self.get_context()
        self.security_logger.log_security_event(
            event_type, severity, message, context, details
        )
    
    def audit_event(
        self,
        action: str,
        resource: str,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event."""
        context = self.get_context()
        self.audit_logger.log_audit_event(
            action, resource, context, outcome, details
        )

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    def __init__(self, app, logger: StructuredLogger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response with performance metrics."""
        
        # Generate request context
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        # Set logging context
        context = LogContext(
            request_id=request_id,
            component="api",
            operation=f"{request.method} {request.url.path}",
            api_version=getattr(request.state, 'api_version', None),
            additional_fields={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type")
            }
        )
        
        self.logger.set_context(context)
        
        # Log request
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            category=LogCategory.API
        )
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                category=LogCategory.API,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Log performance if slow
            if duration_ms > 1000:  # Log if request takes more than 1 second
                self.logger.performance(
                    f"{request.method} {request.url.path}",
                    duration_ms,
                    {"status_code": response.status_code}
                )
            
            return response
            
        except Exception as e:
            # Calculate duration for error case
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=e,
                category=LogCategory.ERROR,
                duration_ms=duration_ms
            )
            
            # Log security event for suspicious errors
            if isinstance(e, (ValueError, TypeError)):
                self.logger.security_event(
                    "request_error",
                    LogLevel.WARNING,
                    f"Suspicious request error: {str(e)}",
                    {"error_type": type(e).__name__, "error_message": str(e)}
                )
            
            raise

def setup_logging(
    app,
    log_level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
    output_format: str = "json"
) -> StructuredLogger:
    """Setup comprehensive logging system for the application."""
    
    # Create main logger
    logger = StructuredLogger(
        name="novel_engine",
        level=log_level,
        output_format=output_format,
        log_file=log_file
    )
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware, logger=logger)
    
    # Store logger in app state for access from endpoints
    app.state.logger = logger
    
    # Setup log endpoints
    @app.get("/api/v1/logs/health", tags=["Monitoring"])
    async def get_logging_health():
        """Get logging system health."""
        return {
            "status": "healthy",
            "logger_name": logger.name,
            "level": logger.level.value,
            "format": logger.output_format,
            "handlers_count": len(logger.logger.handlers)
        }
    
    @app.get("/api/v1/logs/security", tags=["Monitoring"])
    async def get_security_events(limit: int = 100):
        """Get recent security events."""
        events = logger.security_logger.get_recent_security_events(limit)
        return {
            "events": [event.to_dict() for event in events],
            "count": len(events)
        }
    
    logger.info("Logging system initialized successfully")
    return logger

__all__ = [
    'LogLevel', 'LogCategory', 'LogContext', 'StructuredLogEntry',
    'PerformanceTracker', 'SecurityLogger', 'AuditLogger', 'StructuredLogger',
    'LoggingMiddleware', 'setup_logging'
]