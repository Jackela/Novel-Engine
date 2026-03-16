"""
Tests for health check endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.apps.api.health import (
    health_router,
    HealthStatus,
    DetailedHealthStatus,
    ComponentStatus,
    _get_uptime,
)


@pytest.fixture
def client():
    """Create test client with health router."""
    app = FastAPI()
    app.include_router(health_router)
    return TestClient(app)


class TestHealthCheck:
    """Test basic health check endpoint."""

    def test_health_status_model(self):
        """Test HealthStatus model."""
        status = HealthStatus(
            status="healthy",
            version="2.0.0",
            timestamp="2024-01-01T00:00:00",
            environment="test",
            uptime_seconds=100.0,
        )
        assert status.status == "healthy"
        assert status.version == "2.0.0"

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert "timestamp" in data
        assert "environment" in data
        assert "uptime_seconds" in data

    def test_health_response_content_type(self, client):
        """Test health check returns JSON."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestLivenessProbe:
    """Test Kubernetes liveness probe."""

    def test_liveness_probe(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestReadinessProbe:
    """Test Kubernetes readiness probe."""

    def test_readiness_probe(self, client):
        """Test readiness probe endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "components" in data
        assert isinstance(data["components"], list)

    def test_readiness_components(self, client):
        """Test readiness probe includes component checks."""
        response = client.get("/health/ready")
        data = response.json()

        # Check for expected components
        component_names = [c["name"] for c in data["components"]]
        assert "database" in component_names
        assert "cache" in component_names


class TestDetailedHealth:
    """Test detailed health check."""

    def test_detailed_health_endpoint(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "version" in data

    def test_detailed_health_status_model(self):
        """Test DetailedHealthStatus model."""
        status = DetailedHealthStatus(
            status="healthy",
            version="2.0.0",
            timestamp="2024-01-01T00:00:00",
            environment="test",
            uptime_seconds=100.0,
            components=[],
        )
        assert status.status == "healthy"


class TestComponentStatus:
    """Test ComponentStatus model."""

    def test_component_status_creation(self):
        """Test creating component status."""
        component = ComponentStatus(
            name="database",
            status="healthy",
            healthy=True,
            response_time_ms=10.5,
            details={"type": "postgresql"},
        )
        assert component.name == "database"
        assert component.healthy is True
        assert component.details["type"] == "postgresql"

    def test_component_status_default_details(self):
        """Test component status with default details."""
        component = ComponentStatus(
            name="cache",
            status="healthy",
            healthy=True,
            response_time_ms=5.0,
        )
        assert component.details == {}


class TestVersionEndpoint:
    """Test version endpoint."""

    def test_version_endpoint(self, client):
        """Test version endpoint."""
        response = client.get("/version")
        assert response.status_code == 200

        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["name"] == "Novel Engine API"
        assert "python_version" in data
        assert "environment" in data


class TestUptime:
    """Test uptime calculation."""

    def test_get_uptime(self):
        """Test uptime calculation is positive."""
        uptime = _get_uptime()
        assert uptime >= 0

    def test_uptime_increases(self):
        """Test uptime increases over time."""
        import time

        uptime1 = _get_uptime()
        time.sleep(0.01)
        uptime2 = _get_uptime()
        assert uptime2 > uptime1
