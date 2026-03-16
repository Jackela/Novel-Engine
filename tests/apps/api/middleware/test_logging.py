"""
Tests for logging middleware.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import time

from src.apps.api.middleware.logging import (
    LoggingMiddleware,
    logging_middleware,
    RequestContext,
)


class TestLoggingMiddleware:
    """Test logging middleware."""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test logging successful request."""
        from starlette.middleware.base import BaseHTTPMiddleware
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"test": True}

        # Add middleware
        app.add_middleware(LoggingMiddleware)

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_failed_request(self):
        """Test logging failed request."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/error")
        def error_endpoint():
            raise ValueError("Test error")

        # Add middleware
        app.add_middleware(LoggingMiddleware)

        client = TestClient(app)
        # Middleware catches exceptions and returns 500
        with pytest.raises(ValueError):
            client.get("/error")


class TestLoggingMiddlewareFunction:
    """Test logging middleware function."""

    @pytest.mark.asyncio
    async def test_logging_middleware_success(self):
        """Test logging middleware function."""

        class MockRequest:
            method = "GET"
            url = type("URL", (), {"path": "/health", "query": ""})()
            state = Mock()

        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            response.headers = {}
            return response

        with patch("src.apps.api.middleware.logging.logger") as mock_logger:
            mock_logger.ainfo = AsyncMock()

            response = await logging_middleware(MockRequest(), mock_call_next)
            assert response.status_code == 200
            assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_logging_middleware_error(self):
        """Test logging middleware with error."""

        class MockRequest:
            method = "GET"
            url = type("URL", (), {"path": "/error", "query": ""})()
            state = Mock()

        async def mock_call_next(request):
            raise RuntimeError("Error")

        with patch("src.apps.api.middleware.logging.logger") as mock_logger:
            mock_logger.ainfo = AsyncMock()
            mock_logger.aerror = AsyncMock()

            with pytest.raises(RuntimeError):
                await logging_middleware(MockRequest(), mock_call_next)


class TestRequestContext:
    """Test request context manager."""

    def test_request_context(self):
        """Test request context binding."""
        with patch("src.apps.api.middleware.logging.logger") as mock_logger:
            mock_logger.bind.return_value = Mock()

            with RequestContext(request_id="abc123", user="test") as ctx:
                assert ctx is not None
