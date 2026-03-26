"""Tests for health check endpoints.

Tests the API health endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.apps.api.health import (
    _get_health_checker,
    health_router,
    set_connection_pool,
    set_honcho_client,
)
from src.shared.infrastructure.health.health_checker import HealthChecker


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(health_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_200_when_empty(self, client):
        """Test health endpoint returns 200 when no components registered."""
        # Reset health checker to ensure clean state
        import src.apps.api.health as health_module

        health_module._health_checker = None

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data

    def test_health_returns_json(self, client):
        """Test health endpoint returns JSON."""
        import src.apps.api.health as health_module

        health_module._health_checker = None

        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"


class TestLivenessEndpoint:
    """Test /health/live endpoint."""

    def test_liveness_returns_alive(self, client):
        """Test liveness probe returns 'alive'."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestReadinessEndpoint:
    """Test /health/ready endpoint."""

    def test_readiness_without_database(self, client):
        """Test readiness returns not_ready when no database."""
        import src.apps.api.health as health_module

        health_module._health_checker = None
        health_module._connection_pool = None

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "Database" in data["reason"]

    def test_readiness_with_mock_database(self, client):
        """Test readiness with mocked database."""
        from unittest.mock import AsyncMock, MagicMock

        import src.apps.api.health as health_module

        # Reset state
        health_module._health_checker = None

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.is_initialized = True
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_pool.acquire.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        )

        # Set the pool
        health_module._connection_pool = mock_pool

        # Make request and verify readiness
        response = client.get("/health/ready")

        # Database is healthy, so should be ready
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_readiness_returns_503_when_not_ready(self, client):
        """Test readiness returns 503 when not ready."""
        import src.apps.api.health as health_module

        health_module._health_checker = None
        health_module._connection_pool = None

        response = client.get("/health/ready")

        assert response.status_code == 503


class TestDetailedHealthEndpoint:
    """Test /health/detailed endpoint."""

    def test_detailed_health_alias(self, client):
        """Test detailed health is alias for health."""
        import src.apps.api.health as health_module

        health_module._health_checker = None

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "timestamp" in data
        assert "components" in data


class TestVersionEndpoint:
    """Test /version endpoint."""

    def test_version_endpoint(self, client):
        """Test version endpoint."""
        response = client.get("/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "name" in data
        assert "environment" in data
        assert "python_version" in data


class TestHealthCheckerIntegration:
    """Integration tests for health checker."""

    @pytest.mark.asyncio
    async def test_get_health_checker_creates_new_instance(self):
        """Test that _get_health_checker creates a new instance."""
        import src.apps.api.health as health_module

        # Reset
        health_module._health_checker = None

        checker = await _get_health_checker()

        assert isinstance(checker, HealthChecker)
        assert health_module._health_checker is checker

    def test_set_connection_pool(self):
        """Test setting connection pool."""
        from unittest.mock import MagicMock

        import src.apps.api.health as health_module

        mock_pool = MagicMock()

        set_connection_pool(mock_pool)

        assert health_module._connection_pool is mock_pool

    def test_set_honcho_client(self):
        """Test setting Honcho client."""
        from unittest.mock import MagicMock

        import src.apps.api.health as health_module

        mock_client = MagicMock()

        set_honcho_client(mock_client)

        assert health_module._honcho_client is mock_client
