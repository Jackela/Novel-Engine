"""Integration tests for Health API endpoints.

Tests the health check endpoints for liveness, readiness, and detailed health checks.
"""

import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestHealthLivenessEndpoint:
    """Tests for the /health/live liveness probe endpoint."""

    def test_liveness_returns_200(self, client: TestClient) -> None:
        """Test that /health/live returns 200 status."""
        response = client.get("/api/health/live")

        assert response.status_code == 200

    def test_liveness_response_format(self, client: TestClient) -> None:
        """Test that liveness response has correct format."""
        response = client.get("/api/health/live")

        assert response.status_code == 200
        data = response.json()

        # Should have status field
        assert "status" in data
        assert data["status"] == "ok"

    def test_liveness_no_external_dependencies(self, client: TestClient) -> None:
        """Test that liveness probe has no external dependencies.

        The liveness probe should respond quickly without checking
        external services like databases.
        """
        response = client.get("/api/health/live")

        # Should always return 200 if the app is running
        assert response.status_code == 200

        # Response should be simple
        data = response.json()
        assert len(data) <= 2  # Only status field (and possibly timestamp)


@pytest.mark.integration
class TestHealthReadinessEndpoint:
    """Tests for the /health/ready readiness probe endpoint."""

    def test_readiness_returns_200_or_503(self, client: TestClient) -> None:
        """Test that /health/ready returns 200 or 503 status."""
        response = client.get("/api/health/ready")

        # Should return 200 if all services healthy, 503 if any unhealthy
        assert response.status_code in [200, 503]

    def test_readiness_response_format(self, client: TestClient) -> None:
        """Test that readiness response has correct format."""
        response = client.get("/api/health/ready")

        # Parse response whether 200 or 503
        if response.status_code == 200:
            data = response.json()

            # Should have status and checks
            assert "status" in data
            assert "checks" in data
            assert isinstance(data["checks"], dict)
        else:
            # 503 returns error detail
            data = response.json()
            assert "detail" in data or "status" in data

    def test_readiness_checks_all_services(self, client: TestClient) -> None:
        """Test that readiness checks all expected services."""
        response = client.get("/api/health/ready")

        if response.status_code == 200:
            data = response.json()
            checks = data.get("checks", {})

            # Should check all major services
            expected_services = ["chromadb", "postgres", "redis", "llm"]

            for service in expected_services:
                assert service in checks, f"Missing health check for {service}"

                # Each check should have status and message
                check = checks[service]
                assert "status" in check
                assert "message" in check

    def test_readiness_service_status_values(self, client: TestClient) -> None:
        """Test that service status values are valid."""
        response = client.get("/api/health/ready")

        if response.status_code == 200:
            data = response.json()
            checks = data.get("checks", {})

            valid_statuses = ["ok", "error", "not_configured", "not_installed"]

            for service, check in checks.items():
                assert check["status"] in valid_statuses, (
                    f"Invalid status '{check['status']}' for {service}"
                )

    def test_readiness_not_configured_is_healthy(self, client: TestClient) -> None:
        """Test that not_configured services are treated as healthy.

        Services that are not configured should not cause 503.
        """
        response = client.get("/api/health/ready")

        if response.status_code == 200:
            data = response.json()
            checks = data.get("checks", {})

            # All not_configured services should have ok status in overall check
            for service, check in checks.items():
                if check["message"] == "not_configured":
                    assert check["status"] == "ok"


@pytest.mark.integration
class TestHealthDetailedEndpoint:
    """Tests for the /health detailed health check endpoint."""

    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        """Test that /health returns 200 status."""
        response = client.get("/api/health")

        assert response.status_code == 200

    def test_health_response_format(self, client: TestClient) -> None:
        """Test that health response has correct format."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "status" in data
        assert "api" in data
        assert "timestamp" in data
        assert "version" in data
        assert "config" in data

    def test_health_status_values(self, client: TestClient) -> None:
        """Test that health status values are valid."""
        response = client.get("/api/health")

        data = response.json()

        # Status should be healthy or degraded
        assert data["status"] in ["healthy", "degraded"]

        # API should be running
        assert data["api"] == "running"

    def test_health_includes_uptime(self, client: TestClient) -> None:
        """Test that health response includes uptime."""
        response = client.get("/api/health")

        data = response.json()

        # Uptime should be present and non-negative
        assert "uptime" in data
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0

    def test_health_includes_version(self, client: TestClient) -> None:
        """Test that health response includes version."""
        response = client.get("/api/health")

        data = response.json()

        assert "version" in data
        assert isinstance(data["version"], str)


@pytest.mark.integration
class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_200(self, client: TestClient) -> None:
        """Test that root endpoint returns 200."""
        response = client.get("/api/")

        assert response.status_code == 200

    def test_root_response_format(self, client: TestClient) -> None:
        """Test that root response has correct format."""
        response = client.get("/api/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "status" in data
        assert "timestamp" in data

    def test_root_status_is_ok(self, client: TestClient) -> None:
        """Test that root status is ok."""
        response = client.get("/api/")

        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.integration
class TestChromaDBHealthEndpoint:
    """Tests for the /health/chromadb specific health check."""

    def test_chromadb_health_returns_200_or_status(self, client: TestClient) -> None:
        """Test that ChromaDB health check returns appropriate status."""
        response = client.get("/api/health/chromadb")

        # Should return 200 with status info (even if not installed)
        assert response.status_code == 200

    def test_chromadb_health_response_format(self, client: TestClient) -> None:
        """Test that ChromaDB health response has correct format."""
        response = client.get("/api/health/chromadb")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "status" in data
        assert "message" in data
        assert "timestamp" in data

    def test_chromadb_health_status_values(self, client: TestClient) -> None:
        """Test that ChromaDB health status values are valid."""
        response = client.get("/api/health/chromadb")

        data = response.json()

        valid_statuses = ["healthy", "unhealthy", "not_installed", "error"]
        assert data["status"] in valid_statuses

    def test_chromadb_health_includes_details(self, client: TestClient) -> None:
        """Test that ChromaDB health includes details when available."""
        response = client.get("/api/health/chromadb")

        data = response.json()

        # If healthy or unhealthy, should have details
        if data["status"] in ["healthy", "unhealthy"]:
            assert "details" in data
            assert "persist_dir" in data["details"]


@pytest.mark.integration
class TestHealthCheckResponseFormat:
    """Tests for health check response format consistency."""

    def test_all_endpoints_return_json(self, client: TestClient) -> None:
        """Test that all health endpoints return valid JSON."""
        endpoints = [
            "/api/health/live",
            "/api/health/ready",
            "/api/health",
            "/api/",
            "/api/health/chromadb",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

    def test_timestamps_are_iso_format(self, client: TestClient) -> None:
        """Test that timestamps are in ISO format."""
        response = client.get("/api/health")

        data = response.json()
        timestamp = data.get("timestamp", "")

        # ISO format should contain 'T' separator
        assert "T" in timestamp or "-" in timestamp
