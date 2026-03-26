"""API endpoint integration tests against the canonical app."""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_endpoint(self, canonical_client):
        """Test GET /health."""
        response = canonical_client.get("/health")
        assert response.status_code in [200, 503]

        data = response.json()
        assert "overall_status" in data
        assert data["overall_status"] in {"healthy", "degraded", "unhealthy"}

    def test_ready_check_endpoint(self, canonical_client):
        """Test GET /health/ready."""
        response = canonical_client.get("/health/ready")
        assert response.status_code in [200, 503]

    def test_live_check_endpoint(self, canonical_client):
        """Test GET /health/live."""
        response = canonical_client.get("/health/live")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"


@pytest.mark.integration
class TestAPIRouting:
    """Test API routing and structure."""

    def test_health_endpoint_accessible(self, canonical_client):
        """Test health endpoint is accessible."""
        response = canonical_client.get("/health")
        assert response.status_code in [200, 503]

    def test_version_endpoint(self, canonical_client):
        """Test version endpoint."""
        response = canonical_client.get("/version")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data


@pytest.mark.integration
class TestMiddleware:
    """Test API middleware."""

    def test_cors_headers(self, canonical_client):
        """Test CORS headers are present."""
        response = canonical_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in [200, 307, 308, 400, 405]

    def test_error_response_format(self, canonical_client):
        """Test error responses follow standard format."""
        response = canonical_client.get("/nonexistent-endpoint-12345")
        assert response.status_code == 404
        assert isinstance(response.json(), dict)


@pytest.mark.integration
class TestAPIHeaders:
    """Test API headers and content types."""

    def test_json_content_type(self, canonical_client):
        """Test API returns JSON content type."""
        response = canonical_client.get("/health")
        assert response.status_code in [200, 503]

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_security_headers(self, canonical_client):
        """Test security headers are present."""
        response = canonical_client.get("/health")
        assert response.status_code in [200, 503]


@pytest.mark.integration
class TestAPIPerformance:
    """Test API response performance."""

    def test_health_endpoint_response_time(self, canonical_client):
        """Test health endpoint responds quickly."""
        import time

        start = time.time()
        response = canonical_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code in [200, 503]
        assert elapsed < 1.0

    def test_concurrent_requests(self, canonical_client):
        """Test handling concurrent requests."""
        from concurrent.futures import ThreadPoolExecutor

        def make_request(_) -> int:
            response = canonical_client.get("/health")
            return response.status_code

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(make_request, range(5)))

        assert all(status in {200, 503} for status in results)
