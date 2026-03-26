"""Unified logging configuration.

This module provides centralized logging configuration using structlog
with support for structured logging, distributed tracing, and flexible output formats.
"""

import logging
import sys
from typing import Any

import structlog


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = False,
    service_name: str = "novel-engine",
    service_version: str = "0.1.0",
) -> None:
    """Configure unified logging for the application.

    This function sets up both standard library logging and structlog with
    consistent configuration. It supports both console and JSON output formats.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: Whether to use JSON format for logs (production) or
            console format (development).
        service_name: The service name for distributed tracing.
        service_version: The service version for distributed tracing.
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Shared processors for both sync and async contexts
    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add service context for distributed tracing
    def add_service_context(
        logger: structlog.typing.WrappedLogger,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Add service context for distributed tracing."""
        event_dict["service_name"] = service_name
        event_dict["service_version"] = service_version
        return event_dict

    shared_processors.append(add_service_context)

    # Choose renderer based on format
    if json_format:
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also configure contextvars for distributed tracing
    structlog.contextvars.merge_contextvars


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get structured logger instance.

    Args:
        name: The logger name. If None, uses the calling module name.

    Returns:
        A configured structlog BoundLogger instance.
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the current logging context.

    These variables will be included in all subsequent log entries
    within the same context (e.g., correlation_id, request_id).

    Args:
        **kwargs: Key-value pairs to bind to the context.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables from the current logging context."""
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys: str) -> None:
    """Unbind specific context variables from the current logging context.

    Args:
        *keys: Keys to unbind from the context.
    """
    structlog.contextvars.unbind_contextvars(*keys)


class LoggingContext:
    """Context manager for temporary logging context.

    Usage:
        with LoggingContext(correlation_id="abc123", user_id="user456"):
            logger.info("Processing request")  # Will include correlation_id and user_id
    """

    def __init__(self, **context_vars: Any):
        """Initialize the context manager with variables to bind.

        Args:
            **context_vars: Key-value pairs to bind to the context.
        """
        self.context_vars = context_vars
        self.previous_vars: dict[str, Any] | None = None

    def __enter__(self) -> "LoggingContext":
        """Enter the context and bind variables."""
        # Store current context for restoration
        self.previous_vars = dict(structlog.contextvars.get_contextvars())
        # Bind new variables
        structlog.contextvars.bind_contextvars(**self.context_vars)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and restore previous state."""
        clear_context()
        if self.previous_vars:
            structlog.contextvars.bind_contextvars(**self.previous_vars)


# Convenience re-exports for common logging patterns
__all__ = [
    "configure_logging",
    "get_logger",
    "bind_context",
    "clear_context",
    "unbind_context",
    "LoggingContext",
]
