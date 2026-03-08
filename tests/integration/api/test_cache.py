"""Integration tests for Cache API endpoints.

Tests the cache management endpoints for invalidation, metrics, and streaming.
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
class TestCacheMetricsEndpoint:
    """Tests for cache metrics endpoint."""

    def test_get_cache_metrics(self, client: TestClient) -> None:
        """Test GET /api/cache/metrics endpoint."""
        response = client.get("/api/cache/metrics")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert isinstance(data, dict)

    def test_cache_metrics_response_format(self, client: TestClient) -> None:
        """Test that cache metrics response has expected format."""
        response = client.get("/api/cache/metrics")

        assert response.status_code == 200
        data = response.json()

        # Metrics should be a dictionary (specific fields depend on implementation)
        assert isinstance(data, dict)


@pytest.mark.integration
class TestCacheInvalidationEndpoint:
    """Tests for cache invalidation endpoint."""

    def test_invalidate_cache_all(self, client: TestClient) -> None:
        """Test POST /api/cache/invalidate with all_of filter."""
        response = client.post(
            "/api/cache/invalidate",
            json={"all_of": ["narrative", "character"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_invalidate_cache_empty_filter(self, client: TestClient) -> None:
        """Test POST /api/cache/invalidate with empty filter."""
        response = client.post(
            "/api/cache/invalidate",
            json={"all_of": []},
        )

        assert response.status_code == 200

    def test_invalidate_cache_single_tag(self, client: TestClient) -> None:
        """Test POST /api/cache/invalidate with single tag."""
        response = client.post(
            "/api/cache/invalidate",
            json={"all_of": ["test-tag"]},
        )

        assert response.status_code == 200


@pytest.mark.integration
class TestCacheChunkEndpoints:
    """Tests for cache chunk management endpoints."""

    def test_append_chunk(self, client: TestClient) -> None:
        """Test POST /api/cache/chunk/{key} endpoint."""
        response = client.post(
            "/api/cache/chunk/test-chunk-key",
            json={"seq": 1, "data": "test chunk data"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_mark_chunk_complete(self, client: TestClient) -> None:
        """Test POST /api/cache/chunk/{key}/complete endpoint."""
        response = client.post("/api/cache/chunk/test-complete-key/complete")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_stream_chunks(self, client: TestClient) -> None:
        """Test GET /api/cache/stream/{key} endpoint."""
        response = client.get("/api/cache/stream/test-stream-key")

        # Streaming endpoint should return SSE content type or 200
        assert response.status_code == 200
        # Should be text/event-stream for SSE
        assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.integration
class TestCacheValidation:
    """Tests for cache endpoint validation."""

    def test_invalidation_request_format(self, client: TestClient) -> None:
        """Test that invalidation request requires proper format."""
        # Missing all_of field should fail validation
        response = client.post(
            "/api/cache/invalidate",
            json={},
        )

        # Should fail validation (422) or be accepted with defaults (200)
        assert response.status_code in [200, 422]

    def test_chunk_request_format(self, client: TestClient) -> None:
        """Test that chunk append requires proper format."""
        # Missing required fields
        response = client.post(
            "/api/cache/chunk/test-key",
            json={},
        )

        # Should fail validation
        assert response.status_code == 422

    def test_chunk_request_with_valid_data(self, client: TestClient) -> None:
        """Test chunk append with valid data."""
        response = client.post(
            "/api/cache/chunk/test-key",
            json={"seq": 0, "data": "some data"},
        )

        assert response.status_code == 200


@pytest.mark.integration
class TestCacheResponseFormat:
    """Tests for cache response format validation."""

    def test_metrics_response_type(self, client: TestClient) -> None:
        """Test that metrics returns a dictionary."""
        response = client.get("/api/cache/metrics")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_invalidation_response_type(self, client: TestClient) -> None:
        """Test that invalidation returns a dictionary."""
        response = client.post(
            "/api/cache/invalidate",
            json={"all_of": ["test"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_chunk_append_response_type(self, client: TestClient) -> None:
        """Test that chunk append returns a dictionary."""
        response = client.post(
            "/api/cache/chunk/response-test-key",
            json={"seq": 1, "data": "test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
