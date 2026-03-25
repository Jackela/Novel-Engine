"""Tests for the logging configuration module.

This module contains comprehensive tests for the logging configuration
and related functionality.
"""


import structlog
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.shared.infrastructure.logging.config import (
    LoggingContext,
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    unbind_context,
)
from src.shared.infrastructure.middleware.correlation_middleware import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    get_correlation_id,
    get_correlation_id_from_context,
    get_request_id,
)
from src.shared.infrastructure.middleware.logging_middleware import LoggingMiddleware
from src.shared.infrastructure.middleware.metrics_middleware import MetricsMiddleware


class TestLoggingConfiguration:
    """Test cases for logging configuration."""

    def test_configure_logging_default(self):
        """Test logging configuration with default parameters."""
        # Should not raise any exceptions
        configure_logging(log_level="INFO", json_format=False)
        logger = get_logger("test")
        assert logger is not None
        # structlog.get_logger returns a BoundLoggerLazyProxy until first use
        # Check that it has the expected interface
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def test_configure_logging_json_format(self):
        """Test logging configuration with JSON format."""
        configure_logging(log_level="DEBUG", json_format=True)
        logger = get_logger("test_json")
        assert logger is not None

    def test_configure_logging_different_levels(self):
        """Test logging configuration with different log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            configure_logging(log_level=level, json_format=False)
            logger = get_logger(f"test_{level.lower()}")
            assert logger is not None

    def test_get_logger_with_name(self):
        """Test getting logger with explicit name."""
        configure_logging()
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"

    def test_get_logger_without_name(self):
        """Test getting logger without explicit name."""
        configure_logging()
        logger = get_logger()
        assert logger is not None


class TestLoggingContext:
    """Test cases for logging context management."""

    def setup_method(self):
        """Clear context before each test."""
        clear_context()
        configure_logging()

    def test_bind_context(self):
        """Test binding context variables."""
        bind_context(correlation_id="test-123", user_id="user-456")
        ctx = structlog.contextvars.get_contextvars()
        assert ctx.get("correlation_id") == "test-123"
        assert ctx.get("user_id") == "user-456"

    def test_clear_context(self):
        """Test clearing context variables."""
        bind_context(correlation_id="test-123")
        clear_context()
        ctx = structlog.contextvars.get_contextvars()
        assert "correlation_id" not in ctx

    def test_unbind_context(self):
        """Test unbinding specific context variables."""
        bind_context(
            correlation_id="test-123", user_id="user-456", request_id="req-789"
        )
        unbind_context("user_id")
        ctx = structlog.contextvars.get_contextvars()
        assert "user_id" not in ctx
        assert ctx.get("correlation_id") == "test-123"
        assert ctx.get("request_id") == "req-789"

    def test_logging_context_manager(self):
        """Test LoggingContext context manager."""
        # Set initial context
        bind_context(initial_var="initial_value")

        # Use context manager to temporarily add more context
        with LoggingContext(correlation_id="ctx-123", request_id="req-456"):
            ctx = structlog.contextvars.get_contextvars()
            assert ctx.get("correlation_id") == "ctx-123"
            assert ctx.get("request_id") == "req-456"
            assert ctx.get("initial_var") == "initial_value"

        # After exiting context manager, temporary variables should be cleared
        # but initial context should be restored
        ctx = structlog.contextvars.get_contextvars()
        assert "correlation_id" not in ctx
        assert "request_id" not in ctx
        assert ctx.get("initial_var") == "initial_value"

    def test_nested_logging_context(self):
        """Test nested LoggingContext managers."""
        with LoggingContext(outer="outer_value"):
            with LoggingContext(inner="inner_value"):
                ctx = structlog.contextvars.get_contextvars()
                assert ctx.get("outer") == "outer_value"
                assert ctx.get("inner") == "inner_value"

            # After inner context exits
            ctx = structlog.contextvars.get_contextvars()
            assert ctx.get("outer") == "outer_value"
            assert "inner" not in ctx


class TestCorrelationIdMiddleware:
    """Test cases for correlation ID middleware."""

    def test_correlation_id_middleware_generates_id(self):
        """Test that middleware generates correlation ID if not provided."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert CORRELATION_ID_HEADER in response.headers
        assert REQUEST_ID_HEADER in response.headers
        # Validate UUID format
        correlation_id = response.headers[CORRELATION_ID_HEADER]
        assert len(correlation_id) == 36  # UUID v4 length

    def test_correlation_id_middleware_uses_provided_id(self):
        """Test that middleware uses provided correlation ID from header."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        provided_id = "custom-correlation-id-123"
        response = client.get("/test", headers={CORRELATION_ID_HEADER: provided_id})

        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == provided_id

    def test_correlation_id_in_request_state(self):
        """Test that correlation ID is stored in request state."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        def test_endpoint(request: Request):
            return {
                "correlation_id": get_correlation_id(request),
                "request_id": get_request_id(request),
            }

        client = TestClient(app)
        provided_id = "state-test-123"
        response = client.get("/test", headers={CORRELATION_ID_HEADER: provided_id})

        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == provided_id
        assert len(data["request_id"]) == 8  # Request ID is truncated UUID

    def test_get_correlation_id_fallback(self):
        """Test get_correlation_id fallback when state is not set."""
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.state = MagicMock()
        # Simulate missing correlation_id attribute
        del mock_request.state.correlation_id

        correlation_id = get_correlation_id(mock_request)
        assert len(correlation_id) == 36  # Should generate new UUID

    def test_get_correlation_id_from_context(self):
        """Test getting correlation ID from logging context."""
        clear_context()
        configure_logging()

        # Initially should be None
        assert get_correlation_id_from_context() is None

        # Bind context and check again
        bind_context(correlation_id="ctx-from-context")
        assert get_correlation_id_from_context() == "ctx-from-context"


class TestLoggingMiddleware:
    """Test cases for logging middleware."""

    def test_logging_middleware_successful_request(self):
        """Test logging middleware logs successful requests."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Middleware should complete without errors

    def test_logging_middleware_with_query_params(self):
        """Test logging middleware handles query parameters."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/test")
        def test_endpoint(param: str = "default"):
            return {"param": param}

        client = TestClient(app)
        response = client.get("/test?param=test_value&other=123")

        assert response.status_code == 200

    def test_logging_middleware_error_handling(self):
        """Test logging middleware handles errors correctly."""
        from fastapi import HTTPException

        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/error")
        def error_endpoint():
            raise HTTPException(status_code=500, detail="Test error")

        client = TestClient(app)
        response = client.get("/error")

        assert response.status_code == 500
        # Middleware should log the error before re-raising


class TestMetricsMiddleware:
    """Test cases for metrics middleware."""

    def test_metrics_middleware_records_request(self):
        """Test that metrics middleware records requests."""
        from fastapi import HTTPException


        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        # Add HTTP exception handler with proper Response
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Metrics should be recorded (we can't easily verify without prometheus client)

    def test_metrics_middleware_different_status_codes(self):
        """Test metrics middleware with different status codes."""
        from fastapi import HTTPException

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/success")
        def success_endpoint():
            return {"status": "ok"}

        @app.get("/not-found")
        def not_found_endpoint():
            raise HTTPException(status_code=404, detail="Not found")

        client = TestClient(app)

        # Test successful request
        response = client.get("/success")
        assert response.status_code == 200

        # Test not found
        response = client.get("/not-found")
        assert response.status_code == 404


class TestIntegration:
    """Integration tests for logging and middleware."""

    def test_full_middleware_stack(self):
        """Test all middleware working together."""
        configure_logging()
        clear_context()

        app = FastAPI()
        # Add middleware in correct order (reverse of execution order)
        app.add_middleware(MetricsMiddleware)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        def test_endpoint(request: Request):
            # Access request state
            correlation_id = get_correlation_id(request)
            return {
                "status": "ok",
                "correlation_id": correlation_id,
            }

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert CORRELATION_ID_HEADER in response.headers
        assert REQUEST_ID_HEADER in response.headers
        data = response.json()
        assert data["status"] == "ok"
        assert data["correlation_id"] == response.headers[CORRELATION_ID_HEADER]

    def test_middleware_with_provided_correlation_id(self):
        """Test middleware stack with user-provided correlation ID."""
        configure_logging()
        clear_context()

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        def test_endpoint():
            # Check context is properly set
            correlation_id = get_correlation_id_from_context()
            return {"correlation_id_from_context": correlation_id}

        client = TestClient(app)
        provided_id = "integration-test-123"
        response = client.get("/test", headers={CORRELATION_ID_HEADER: provided_id})

        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == provided_id
        data = response.json()
        assert data["correlation_id_from_context"] == provided_id


class TestLoggerUsage:
    """Test cases for logger usage patterns."""

    def setup_method(self):
        """Setup for each test."""
        configure_logging(log_level="DEBUG")
        clear_context()

    def test_logger_info(self):
        """Test logger info level."""
        logger = get_logger("test")
        # Should not raise
        logger.info("Test info message", extra_field="value")

    def test_logger_error(self):
        """Test logger error level."""
        logger = get_logger("test")
        # Should not raise
        logger.error("Test error message", error_code=500)

    def test_logger_with_bound_context(self):
        """Test logger with pre-bound context."""
        logger = get_logger("test")
        bound_logger = logger.bind(request_id="req-123")
        # Should not raise
        bound_logger.info("Message with bound context")

    def test_logger_with_exception(self):
        """Test logger with exception info."""
        logger = get_logger("test")
        try:
            raise ValueError("Test exception")
        except Exception:
            # Should not raise
            logger.exception("Exception occurred")
