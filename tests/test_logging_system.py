#!/usr/bin/env python3
"""
StructuredLogger Test Suite
===========================

Comprehensive unit tests for the structured logging system.
Tests logging functionality, context management, and performance tracking.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.logging_system import (
    LogContext,
    LoggerFactory,
    PerformanceTracker,
    StructuredFormatter,
    StructuredLogger,
)


class TestLogContext:
    """Test LogContext functionality."""

    @pytest.mark.unit
    def test_log_context_creation(self):
        """Test LogContext creation and defaults."""
        context = LogContext()

        assert context.correlation_id is not None
        assert len(context.correlation_id) > 0  # Should be UUID
        assert context.session_id is None
        assert context.user_id is None
        assert isinstance(context.metadata, dict)

    @pytest.mark.unit
    def test_log_context_with_values(self):
        """Test LogContext with provided values."""
        context = LogContext(
            session_id="test_session",
            user_id="test_user",
            component="test_component",
            operation="test_operation",
        )

        assert context.session_id == "test_session"
        assert context.user_id == "test_user"
        assert context.component == "test_component"
        assert context.operation == "test_operation"


class TestStructuredLogger:
    """Test StructuredLogger functionality."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def logger_config(self, temp_log_dir):
        """Create logger configuration."""
        return {
            "level": "DEBUG",
            "log_dir": temp_log_dir,
            "console_format": "readable",
            "enable_audit": True,
        }

    @pytest.fixture
    def structured_logger(self, logger_config):
        """Create structured logger for testing."""
        return StructuredLogger("test_logger", logger_config)

    @pytest.mark.unit
    def test_structured_logger_initialization(self, structured_logger):
        """Test structured logger initialization."""
        assert structured_logger.name == "test_logger"
        assert len(structured_logger._logger.handlers) > 0
        assert len(structured_logger._context_stack) == 0
        assert len(structured_logger.performance_metrics) == 0

    @pytest.mark.unit
    def test_context_management(self, structured_logger):
        """Test logging context management."""
        context = LogContext(component="test_component")

        # Push context
        structured_logger.push_context(context)
        assert len(structured_logger._context_stack) == 1
        assert structured_logger.get_current_context() == context

        # Pop context
        popped_context = structured_logger.pop_context()
        assert popped_context == context
        assert len(structured_logger._context_stack) == 0

    @pytest.mark.unit
    def test_basic_logging(self, structured_logger):
        """Test basic logging functionality."""
        # Test different log levels
        structured_logger.trace("Trace message")
        structured_logger.debug("Debug message")
        structured_logger.info("Info message")
        structured_logger.success("Success message")
        structured_logger.warning("Warning message")
        structured_logger.error("Error message")
        structured_logger.critical("Critical message")

        # Should not raise exceptions
        assert True

    @pytest.mark.unit
    def test_logging_with_context(self, structured_logger):
        """Test logging with context."""
        context = LogContext(
            component="test_component",
            operation="test_operation",
            session_id="test_session",
        )

        structured_logger.push_context(context)
        structured_logger.info("Message with context")

        # Context should be applied to log entry
        current_context = structured_logger.get_current_context()
        assert current_context.component == "test_component"

    @pytest.mark.unit
    def test_error_logging(self, structured_logger):
        """Test error logging with exception details."""
        test_exception = ValueError("Test exception")

        structured_logger.error("Error occurred", error=test_exception)
        structured_logger.critical("Critical error", error=test_exception)

        # Should not raise exceptions
        assert True

    @pytest.mark.unit
    def test_performance_tracking(self, structured_logger):
        """Test performance tracking functionality."""
        tracker = structured_logger.track_performance("test_operation")

        assert isinstance(tracker, PerformanceTracker)
        assert tracker.operation == "test_operation"

    @pytest.mark.asyncio
    async def test_performance_context_manager(self, structured_logger):
        """Test performance tracking context manager."""
        with structured_logger.track_performance("async_operation") as tracker:
            await asyncio.sleep(0.01)  # Simulate work
            tracker.add_metric("items_processed", 100)

        # Performance metric should be recorded
        assert len(structured_logger.performance_metrics) > 0

    @pytest.mark.unit
    def test_audit_logging(self, structured_logger):
        """Test audit logging functionality."""
        context = LogContext(user_id="test_user", session_id="audit_session")
        structured_logger.audit("User action performed", context=context)

        # Audit entry should be recorded
        assert len(structured_logger.audit_trail) > 0

    @pytest.mark.unit
    def test_security_logging(self, structured_logger):
        """Test security logging functionality."""
        context = LogContext(user_id="test_user")
        structured_logger.security("Security event detected", context=context)

        # Should not raise exceptions
        assert True

    @pytest.mark.unit
    def test_logger_statistics(self, structured_logger):
        """Test logger statistics."""
        # Add some activity
        structured_logger.info("Test message")
        structured_logger.performance("Performance test", duration_ms=100)

        stats = structured_logger.get_log_statistics()

        assert "performance_entries" in stats
        assert "audit_entries" in stats
        assert "context_stack_depth" in stats
        assert "handlers_configured" in stats


class TestPerformanceTracker:
    """Test PerformanceTracker functionality."""

    @pytest.mark.unit
    def test_performance_tracker_creation(self):
        """Test PerformanceTracker creation."""
        context = LogContext(component="test_component")
        tracker = PerformanceTracker("test_operation", context)

        assert tracker.operation == "test_operation"
        assert tracker.context == context
        assert isinstance(tracker.start_time, float)

    @pytest.mark.unit
    def test_performance_tracker_metrics(self):
        """Test performance tracker metrics."""
        tracker = PerformanceTracker("test_operation")

        tracker.add_metric("items_processed", 50)
        tracker.add_metric("cache_hits", 25)

        assert tracker.metrics["items_processed"] == 50
        assert tracker.metrics["cache_hits"] == 25


class TestStructuredFormatter:
    """Test StructuredFormatter functionality."""

    @pytest.mark.unit
    def test_json_formatter(self):
        """Test JSON output formatting."""
        formatter = StructuredFormatter(format_type="json")

        # Create mock log record
        record = Mock()
        record.structured_data = {
            "timestamp": "2023-01-01T00:00:00",
            "level": "INFO",
            "message": "Test message",
            "context": {"component": "test"},
        }

        result = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"

    @pytest.mark.unit
    def test_readable_formatter(self):
        """Test readable output formatting."""
        formatter = StructuredFormatter(format_type="readable")

        # Create mock log record
        record = Mock()
        record.structured_data = {
            "timestamp": "2023-01-01T00:00:00",
            "level": "INFO",
            "message": "Test message",
            "context": {"component": "test_component"},
        }

        result = formatter.format(record)

        # Should be readable format
        assert "2023-01-01T00:00:00" in result
        assert "INFO" in result
        assert "test_component" in result
        assert "Test message" in result

    @pytest.mark.unit
    def test_formatter_with_none_component(self):
        """Test formatter handling None component (fixed issue)."""
        formatter = StructuredFormatter(format_type="readable")

        record = Mock()
        record.structured_data = {
            "timestamp": "2023-01-01T00:00:00",
            "level": "INFO",
            "message": "Test message",
            "context": {"component": None},  # None component
        }

        # Should not raise TypeError
        result = formatter.format(record)
        assert "unknown" in result  # Should default to 'unknown'


class TestLoggerFactory:
    """Test LoggerFactory functionality."""

    @pytest.mark.unit
    def test_get_logger(self):
        """Test logger factory get_logger method."""
        logger1 = LoggerFactory.get_logger("test_logger1")
        logger2 = LoggerFactory.get_logger("test_logger1")  # Same name

        # Should return same instance for same name
        assert logger1 is logger2
        assert isinstance(logger1, StructuredLogger)

    @pytest.mark.unit
    def test_configure_defaults(self):
        """Test default configuration."""
        LoggerFactory.configure_defaults({"level": "DEBUG"})

        logger = LoggerFactory.get_logger("configured_logger")
        assert logger.config["level"] == "DEBUG"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
