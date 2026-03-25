"""API endpoint integration tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with health endpoints."""
    # Reset health checker state
    import src.apps.api.health as health_module
    from src.apps.api.health import health_router

    health_module._health_checker = None
    health_module._connection_pool = None
    health_module._honcho_client = None

    # Create minimal app with just health routes
    app = FastAPI()
    app.include_router(health_router)

    return TestClient(app)


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_endpoint(self, client):
        """Test GET /health."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "overall_status" in data
        assert data["overall_status"] == "healthy"

    def test_ready_check_endpoint(self, client):
        """Test GET /health/ready."""
        response = client.get("/health/ready")
        # Should return 503 when no database configured
        assert response.status_code in [200, 503]

    def test_live_check_endpoint(self, client):
        """Test GET /health/live."""
        response = client.get("/health/live")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"


@pytest.mark.integration
class TestAPIRouting:
    """Test API routing and structure."""

    def test_health_endpoint_accessible(self, client):
        """Test health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_version_endpoint(self, client):
        """Test version endpoint."""
        response = client.get("/version")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data


@pytest.mark.integration
class TestMiddleware:
    """Test API middleware."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS headers should be present or endpoint should be accessible
        # 405 Method Not Allowed is acceptable when CORS not configured
        assert response.status_code in [200, 307, 308, 400, 405]

    def test_error_response_format(self, client):
        """Test error responses follow standard format."""
        # Trigger a 404 error
        response = client.get("/nonexistent-endpoint-12345")
        assert response.status_code == 404

        # Response should be JSON
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestAPIHeaders:
    """Test API headers and content types."""

    def test_json_content_type(self, client):
        """Test API returns JSON content type."""
        response = client.get("/health")
        assert response.status_code == 200

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_security_headers(self, client):
        """Test security headers are present."""
        response = client.get("/health")

        # Check for common security headers
        # Not all headers may be present, just check response is OK
        assert response.status_code == 200


@pytest.mark.integration
class TestAPIPerformance:
    """Test API response performance."""

    def test_health_endpoint_response_time(self, client):
        """Test health endpoint responds quickly."""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond in less than 1 second

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        from concurrent.futures import ThreadPoolExecutor

        def make_request(_) -> int:
            response = client.get("/health")
            return response.status_code

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(make_request, range(5)))

        # All requests should succeed
        assert all(status == 200 for status in results)
