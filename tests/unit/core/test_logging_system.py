"""
Unit tests for Structured Logging System

Tests cover:
- LogLevel and LogCategory enums
- LogContext dataclass
- LogEntry dataclass
- PerformanceTracker
- StructuredLogger
- StructuredFormatter
- AuditFilter
- LoggerFactory
- LoggingContext
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from unittest.mock import MagicMock

import pytest

from src.core.logging_system import (
    AuditFilter,
    LogCategory,
    LogContext,
    LogEntry,
    LoggerFactory,
    LoggingContext,
    LogLevel,
    PerformanceTracker,
    StructuredFormatter,
    StructuredLogger,
    get_logger,
    with_context,
)

pytestmark = pytest.mark.unit


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_values(self) -> None:
        """Test log level enum values."""
        assert LogLevel.TRACE.value == "TRACE"
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.SUCCESS.value == "SUCCESS"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"
        assert LogLevel.AUDIT.value == "AUDIT"
        assert LogLevel.PERFORMANCE.value == "PERFORMANCE"
        assert LogLevel.SECURITY.value == "SECURITY"

    def test_all_levels_defined(self) -> None:
        """Test that all expected levels are defined."""
        expected = {
            "TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING",
            "ERROR", "CRITICAL", "AUDIT", "PERFORMANCE", "SECURITY"
        }
        actual = {level.value for level in LogLevel}
        assert actual == expected


class TestLogCategory:
    """Tests for LogCategory enum."""

    def test_log_category_values(self) -> None:
        """Test log category enum values."""
        assert LogCategory.SYSTEM.value == "system"
        assert LogCategory.APPLICATION.value == "application"
        assert LogCategory.SECURITY.value == "security"
        assert LogCategory.PERFORMANCE.value == "performance"
        assert LogCategory.AUDIT.value == "audit"
        assert LogCategory.USER.value == "user"
        assert LogCategory.API.value == "api"
        assert LogCategory.DATABASE.value == "database"
        assert LogCategory.INTEGRATION.value == "integration"
        assert LogCategory.BUSINESS.value == "business"


class TestLogContext:
    """Tests for LogContext dataclass."""

    def test_default_context(self) -> None:
        """Test default log context creation."""
        context = LogContext()

        assert context.correlation_id is not None  # Auto-generated UUID
        assert len(context.correlation_id) == 36  # UUID format
        assert context.session_id is None
        assert context.user_id is None
        assert context.request_id is None
        assert context.component is None
        assert context.operation is None
        assert context.trace_id is None
        assert context.metadata == {}

    def test_custom_context(self) -> None:
        """Test log context with custom values."""
        context = LogContext(
            correlation_id="custom-123",
            session_id="session-456",
            user_id="user-789",
            request_id="req-abc",
            component="test-component",
            operation="test-operation",
            trace_id="trace-def",
            metadata={"key": "value"},
        )

        assert context.correlation_id == "custom-123"
        assert context.session_id == "session-456"
        assert context.user_id == "user-789"
        assert context.metadata == {"key": "value"}


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_log_entry_creation(self) -> None:
        """Test log entry creation."""
        context = LogContext()
        entry = LogEntry(
            timestamp="2024-01-15T10:30:00Z",
            level=LogLevel.INFO,
            category=LogCategory.APPLICATION,
            message="Test message",
            context=context,
        )

        assert entry.timestamp == "2024-01-15T10:30:00Z"
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"

    def test_log_entry_to_dict(self) -> None:
        """Test log entry serialization to dict."""
        context = LogContext(correlation_id="test-123")
        entry = LogEntry(
            timestamp="2024-01-15T10:30:00Z",
            level=LogLevel.INFO,
            category=LogCategory.APPLICATION,
            message="Test message",
            context=context,
            duration_ms=150.5,
            error_details={"type": "TestError"},
            performance_metrics={"cpu": 50},
        )

        data = entry.to_dict()

        assert data["timestamp"] == "2024-01-15T10:30:00Z"
        assert data["level"] == "INFO"
        assert data["category"] == "application"
        assert data["message"] == "Test message"
        assert data["duration_ms"] == 150.5
        assert data["error_details"] == {"type": "TestError"}


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""

    def test_tracker_initialization(self) -> None:
        """Test performance tracker initialization."""
        tracker = PerformanceTracker("test-operation")

        assert tracker.operation == "test-operation"
        assert tracker.start_time > 0
        assert tracker.metrics == {}

    def test_add_metric(self) -> None:
        """Test adding metrics."""
        tracker = PerformanceTracker("test-operation")
        tracker.add_metric("rows_processed", 100)
        tracker.add_metric("cache_hits", 50)

        assert tracker.metrics["rows_processed"] == 100
        assert tracker.metrics["cache_hits"] == 50

    def test_finish_logs_performance(self) -> None:
        """Test that finish logs performance metrics."""
        logger = MagicMock(spec=StructuredLogger)
        logger.performance = MagicMock()

        tracker = PerformanceTracker("test-operation")
        time.sleep(0.01)  # Small delay
        tracker.add_metric("rows", 100)

        duration = tracker.finish(logger)

        assert duration > 0
        logger.performance.assert_called_once()
        call_args = logger.performance.call_args
        assert "test-operation" in call_args[0][0]

    def test_context_manager(self) -> None:
        """Test performance tracker as context manager."""
        # Note: This test verifies the context manager structure
        # The actual logging would require thread-local setup
        tracker = PerformanceTracker("test-op")

        with tracker:
            time.sleep(0.001)

        # Context manager should complete without error
        assert True


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    def test_logger_initialization(self) -> None:
        """Test logger initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir, "level": "DEBUG"}
            logger = StructuredLogger("test-logger", config)

            assert logger.name == "test-logger"
            assert logger.config == config
            logger.close()

    def test_context_stack_operations(self) -> None:
        """Test context stack push/pop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            context1 = LogContext(correlation_id="ctx-1")
            context2 = LogContext(correlation_id="ctx-2")

            logger.push_context(context1)
            assert logger.get_current_context() == context1

            logger.push_context(context2)
            assert logger.get_current_context() == context2

            popped = logger.pop_context()
            assert popped == context2
            assert logger.get_current_context() == context1

            logger.pop_context()
            assert logger.get_current_context() is None

            logger.close()

    def test_trace_logging(self) -> None:
        """Test trace level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir, "level": "DEBUG"}
            logger = StructuredLogger("test", config)

            # Should not raise
            logger.trace("Trace message")

            logger.close()

    def test_debug_logging(self) -> None:
        """Test debug level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir, "level": "DEBUG"}
            logger = StructuredLogger("test", config)

            logger.debug("Debug message", category=LogCategory.SYSTEM)

            logger.close()

    def test_info_logging(self) -> None:
        """Test info level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.info("Info message", category=LogCategory.APPLICATION)

            logger.close()

    def test_success_logging(self) -> None:
        """Test success level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.success("Operation succeeded")

            logger.close()

    def test_warning_logging(self) -> None:
        """Test warning level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.warning("Warning message", category=LogCategory.SECURITY)

            logger.close()

    def test_error_logging(self) -> None:
        """Test error level logging with exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            error = ValueError("Test error")
            logger.error("Error occurred", error=error)

            logger.close()

    def test_critical_logging(self) -> None:
        """Test critical level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            error = RuntimeError("Critical error")
            logger.critical("Critical failure", error=error)

            logger.close()

    def test_audit_logging(self) -> None:
        """Test audit level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.audit("User action audited", context=LogContext(user_id="user-123"))

            # Verify audit trail
            audit_entries = logger.get_audit_trail()
            assert len(audit_entries) >= 1

            logger.close()

    def test_performance_logging(self) -> None:
        """Test performance level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.performance(
                "Query executed",
                duration_ms=150.5,
                performance_metrics={"rows": 100},
            )

            # Verify performance metrics stored
            assert len(logger.performance_metrics) >= 1

            logger.close()

    def test_security_logging(self) -> None:
        """Test security level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.security("Security event detected", category=LogCategory.SECURITY)

            logger.close()

    def test_performance_summary(self) -> None:
        """Test getting performance summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            # Add some performance entries
            logger.performance("op1", duration_ms=100)
            logger.performance("op1", duration_ms=200)
            logger.performance("op2", duration_ms=50)

            summary = logger.get_performance_summary()

            assert "total_operations" in summary
            assert summary["total_operations"] >= 3

            logger.close()

    def test_performance_summary_empty(self) -> None:
        """Test performance summary with no metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            summary = logger.get_performance_summary()

            assert "message" in summary
            assert summary["message"] == "No performance data available"

            logger.close()

    def test_performance_summary_result(self) -> None:
        """Test getting performance summary as Result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.performance("op1", duration_ms=100)

            result = logger.get_performance_summary_result()

            assert result.is_ok
            assert "total_operations" in result.value

            logger.close()

    def test_audit_trail_result(self) -> None:
        """Test getting audit trail as Result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            logger.audit("Test audit")

            result = logger.get_audit_trail_result(limit=10)

            assert result.is_ok
            assert isinstance(result.value, list)

            logger.close()

    def test_log_statistics(self) -> None:
        """Test getting log statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            stats = logger.get_log_statistics()

            assert "performance_entries" in stats
            assert "audit_entries" in stats
            assert "context_stack_depth" in stats

            logger.close()

    def test_log_statistics_result(self) -> None:
        """Test getting log statistics as Result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            result = logger.get_log_statistics_result()

            assert result.is_ok
            assert "performance_entries" in result.value

            logger.close()

    def test_time_operation_decorator_sync(self) -> None:
        """Test time operation decorator for sync function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            @logger.time_operation("sync-op")
            def test_func():
                return "result"

            result = test_func()
            assert result == "result"

            logger.close()

    def test_track_performance(self) -> None:
        """Test track_performance method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            tracker = logger.track_performance("test-op")
            assert tracker.operation == "test-op"

            logger.close()


class TestStructuredFormatter:
    """Tests for StructuredFormatter."""

    def test_json_format(self) -> None:
        """Test JSON formatting."""
        formatter = StructuredFormatter(format_type="json")

        record = MagicMock(spec=logging.LogRecord)
        record.structured_data = {
            "timestamp": "2024-01-15T10:30:00Z",
            "level": "INFO",
            "message": "Test",
        }

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["message"] == "Test"

    def test_readable_format(self) -> None:
        """Test readable format."""
        formatter = StructuredFormatter(format_type="readable")

        record = MagicMock(spec=logging.LogRecord)
        record.structured_data = {
            "timestamp": "2024-01-15T10:30:00Z",
            "level": "INFO",
            "message": "Test message",
            "context": {"component": "test"},
            "duration_ms": 150.5,
        }

        result = formatter.format(record)

        assert "INFO" in result
        assert "Test message" in result
        assert "150.5ms" in result

    def test_fallback_format(self) -> None:
        """Test fallback to standard format."""
        formatter = StructuredFormatter(format_type="readable")

        # Create a real LogRecord instead of a mock
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Standard message",
            args=(),
            exc_info=None,
        )

        # Should not raise
        result = formatter.format(record)
        assert isinstance(result, str)


class TestAuditFilter:
    """Tests for AuditFilter."""

    def test_audit_filter_passes_audit(self) -> None:
        """Test that audit records pass the filter."""
        filter_ = AuditFilter()

        record = MagicMock(spec=logging.LogRecord)
        record.structured_data = {
            "level": "AUDIT",
            "category": "application",
        }

        assert filter_.filter(record) is True

    def test_audit_filter_passes_audit_category(self) -> None:
        """Test that audit category records pass."""
        filter_ = AuditFilter()

        record = MagicMock(spec=logging.LogRecord)
        record.structured_data = {
            "level": "INFO",
            "category": "audit",
        }

        assert filter_.filter(record) is True

    def test_audit_filter_rejects_non_audit(self) -> None:
        """Test that non-audit records are rejected."""
        filter_ = AuditFilter()

        record = MagicMock(spec=logging.LogRecord)
        record.structured_data = {
            "level": "INFO",
            "category": "application",
        }

        assert filter_.filter(record) is False

    def test_audit_filter_rejects_no_structured_data(self) -> None:
        """Test that records without structured_data are rejected."""
        filter_ = AuditFilter()

        record = MagicMock(spec=logging.LogRecord)
        # No structured_data

        assert filter_.filter(record) is False


class TestLoggerFactory:
    """Tests for LoggerFactory."""

    def test_get_logger_creates_new(self) -> None:
        """Test getting a new logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = LoggerFactory.get_logger("factory-test-1", config)

            assert logger.name == "factory-test-1"
            logger.close()

    def test_get_logger_returns_existing(self) -> None:
        """Test that factory returns existing logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger1 = LoggerFactory.get_logger("factory-test-2", config)
            logger2 = LoggerFactory.get_logger("factory-test-2", config)

            assert logger1 is logger2
            logger1.close()

    def test_configure_defaults(self) -> None:
        """Test configuring default settings."""
        original_defaults = LoggerFactory._default_config.copy()

        try:
            LoggerFactory.configure_defaults({"level": "DEBUG"})
            assert LoggerFactory._default_config["level"] == "DEBUG"
        finally:
            # Restore original defaults
            LoggerFactory._default_config = original_defaults

    def test_get_all_loggers(self) -> None:
        """Test getting all created loggers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = LoggerFactory.get_logger("factory-test-3", config)

            all_loggers = LoggerFactory.get_all_loggers()
            assert "factory-test-3" in all_loggers

            logger.close()


class TestLoggingContext:
    """Tests for LoggingContext context manager."""

    def test_context_manager(self) -> None:
        """Test logging context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)
            context = LogContext(correlation_id="ctx-123")

            with LoggingContext(logger, context):
                assert logger.get_current_context() == context

            # Context should be popped after exit
            assert logger.get_current_context() is None

            logger.close()

    def test_context_manager_exception(self) -> None:
        """Test context manager with exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)
            context = LogContext(correlation_id="ctx-123")

            try:
                with LoggingContext(logger, context):
                    assert logger.get_current_context() == context
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Context should still be popped
            assert logger.get_current_context() is None

            logger.close()


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_logger(self) -> None:
        """Test get_logger convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = get_logger("convenience-test", config)

            assert isinstance(logger, StructuredLogger)
            assert logger.name == "convenience-test"

            logger.close()

    def test_with_context(self) -> None:
        """Test with_context convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            context = with_context(
                logger,
                correlation_id="ctx-123",
                user_id="user-456",
                custom_key="custom-value",
            )

            assert isinstance(context, LoggingContext)

            with context:
                current = logger.get_current_context()
                assert current.correlation_id == "ctx-123"
                assert current.user_id == "user-456"
                assert current.metadata["custom_key"] == "custom-value"

            logger.close()


class TestLogLevelMapping:
    """Tests for log level mapping."""

    def test_map_to_standard_level(self) -> None:
        """Test mapping custom levels to standard logging levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            assert logger._map_to_standard_level(LogLevel.TRACE) == logging.DEBUG
            assert logger._map_to_standard_level(LogLevel.DEBUG) == logging.DEBUG
            assert logger._map_to_standard_level(LogLevel.INFO) == logging.INFO
            assert logger._map_to_standard_level(LogLevel.WARNING) == logging.WARNING
            assert logger._map_to_standard_level(LogLevel.ERROR) == logging.ERROR
            assert logger._map_to_standard_level(LogLevel.CRITICAL) == logging.CRITICAL
            assert logger._map_to_standard_level(LogLevel.AUDIT) == logging.INFO
            assert logger._map_to_standard_level(LogLevel.PERFORMANCE) == logging.INFO

            logger.close()

    def test_unknown_level_defaults_to_info(self) -> None:
        """Test that unknown levels default to INFO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"log_dir": tmpdir}
            logger = StructuredLogger("test", config)

            # Create a fake level
            fake_level = MagicMock()
            assert logger._map_to_standard_level(fake_level) == logging.INFO  # type: ignore

            logger.close()
