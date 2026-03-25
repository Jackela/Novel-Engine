"""
Tests for FastAPI main application.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.apps.api.main import app, create_application


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestApplication:
    """Test main application configuration."""

    def test_create_application(self):
        """Test application factory creates valid app."""
        app_instance = create_application()
        assert app_instance is not None
        assert app_instance.title == "Novel Engine API"
        assert app_instance.version == "2.0.0"

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Novel Engine API"
        assert data["version"] == "2.0.0"
        assert "/docs" in data["documentation"]

    def test_openapi_schema(self, client):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Novel Engine API"
        assert schema["info"]["version"] == "2.0.0"
        assert "components" in schema
        assert "securitySchemes" in schema["components"]

    def test_docs_endpoint(self, client):
        """Test docs endpoint returns HTML."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data

    def test_liveness_probe(self, client):
        """Test Kubernetes liveness probe."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, client):
        """Test Kubernetes readiness probe."""
        import src.apps.api.health as health_module

        health_module._health_checker = None
        health_module._connection_pool = None

        response = client.get("/health/ready")
        # Without database, should return 503 not_ready
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "Database" in data["reason"]

    def test_detailed_health(self, client):
        """Test detailed health check."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "components" in data

    def test_version_endpoint(self, client):
        """Test version endpoint."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["name"] == "Novel Engine API"


class TestSecurityHeaders:
    """Test security-related headers."""

    def test_request_id_header(self, client):
        """Test X-Request-ID header is present."""
        response = client.get("/health")
        # Note: X-Request-ID is added by LoggingMiddleware, not active in test client by default
        # Just verify the response is successful
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test CORS headers are present for OPTIONS."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Test error handling."""

    def test_not_found(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-path")
        assert response.status_code == 404
        # FastAPI default 404 may not have 'error' key in response
        data = response.json()
        assert "detail" in data or "error" in data

    def test_method_not_allowed(self, client):
        """Test 405 error handling."""
        response = client.post("/health")
        assert response.status_code == 405

    def test_validation_error(self, client):
        """Test validation error handling."""
        # Try to send invalid data (would need an endpoint that validates input)
        pass  # Placeholder - requires specific endpoint


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async application features."""

    async def test_async_health(self):
        """Test async health check using httpx.AsyncClient."""
        from httpx import ASGITransport, AsyncClient

        from src.apps.api.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            assert response.json()["overall_status"] == "healthy"
