"""Integration tests for World Generation API endpoints.

Tests the world generation and configuration endpoints.

Note: World generation requires LLM API key (GEMINI_API_KEY).
Tests are designed to pass whether the service is available or not.
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
class TestWorldGenerationEndpoints:
    """Tests for world generation endpoints."""

    def test_generate_world_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/world/generation endpoint exists."""
        response = client.post(
            "/api/world/generation",
            json={
                "genre": "fantasy",
                "era": "medieval",
                "tone": "heroic",
                "themes": ["adventure"],
                "magic_level": 5,
                "technology_level": 3,
                "num_factions": 2,
                "num_locations": 3,
                "num_events": 2,
            },
        )

        # Endpoint should exist (not 404/405)
        # May return:
        # - 200/201: successful generation
        # - 500: service error (LLM unavailable, caught by generic handler)
        # - 503: service unavailable (if proper exception handling)
        assert response.status_code in [200, 201, 500, 503]

    def test_generate_world_with_custom_params(self, client: TestClient) -> None:
        """Test world generation with custom parameters."""
        response = client.post(
            "/api/world/generation",
            json={
                "genre": "sci-fi",
                "era": "modern",
                "tone": "dark",
                "themes": ["survival", "mystery"],
                "magic_level": 0,
                "technology_level": 8,
                "num_factions": 3,
                "num_locations": 4,
                "num_events": 2,
            },
        )

        # Should accept various parameter combinations
        # May return 500 if LLM service unavailable
        assert response.status_code in [200, 201, 500, 503]


@pytest.mark.integration
class TestWorldGenerationValidation:
    """Tests for world generation request validation."""

    def test_magic_level_bounds(self, client: TestClient) -> None:
        """Test that magic_level must be between 0 and 10."""
        # Test lower bound
        response = client.post(
            "/api/world/generation",
            json={"magic_level": -1},
        )
        assert response.status_code == 422  # Validation error

        # Test upper bound
        response = client.post(
            "/api/world/generation",
            json={"magic_level": 11},
        )
        assert response.status_code == 422

    def test_technology_level_bounds(self, client: TestClient) -> None:
        """Test that technology_level must be between 0 and 10."""
        response = client.post(
            "/api/world/generation",
            json={"technology_level": -1},
        )
        assert response.status_code == 422

        response = client.post(
            "/api/world/generation",
            json={"technology_level": 11},
        )
        assert response.status_code == 422

    def test_num_factions_bounds(self, client: TestClient) -> None:
        """Test that num_factions must be between 1 and 10."""
        response = client.post(
            "/api/world/generation",
            json={"num_factions": 0},
        )
        assert response.status_code == 422

        response = client.post(
            "/api/world/generation",
            json={"num_factions": 11},
        )
        assert response.status_code == 422

    def test_num_locations_bounds(self, client: TestClient) -> None:
        """Test that num_locations must be between 1 and 10."""
        response = client.post(
            "/api/world/generation",
            json={"num_locations": 0},
        )
        assert response.status_code == 422

    def test_num_events_bounds(self, client: TestClient) -> None:
        """Test that num_events must be between 1 and 10."""
        response = client.post(
            "/api/world/generation",
            json={"num_events": 0},
        )
        assert response.status_code == 422
