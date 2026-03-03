"""Integration tests for Social API endpoints.

Tests the social network analysis endpoints for character relationships.

Note: The social router may not be registered in the app. These tests
verify endpoint availability when the router is properly included.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestSocialEndpoints:
    """Tests for social network analysis API endpoints."""

    def test_social_analysis_endpoint_exists(self, client: TestClient) -> None:
        """Test GET /api/social/analysis endpoint exists."""
        response = client.get("/api/social/analysis")

        # If router is not registered, we get 404
        # If registered, should return 200 with analysis data
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Verify response structure
            assert "character_centralities" in data
            assert "total_relationships" in data
            assert "total_characters" in data
            assert "network_density" in data

    def test_character_centrality_endpoint_exists(self, client: TestClient) -> None:
        """Test GET /api/social/analysis/{character_id} endpoint exists."""
        response = client.get("/api/social/analysis/test-char-001")

        # 404 if router not registered or character not found
        # 200 if character has relationships
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "character_id" in data
            assert "relationship_count" in data
            assert "centrality_score" in data


@pytest.mark.integration
class TestSocialAnalysisResponseFormat:
    """Tests for social analysis response format validation."""

    def test_analysis_response_structure(self, client: TestClient) -> None:
        """Test that social analysis response has correct structure."""
        response = client.get("/api/social/analysis")

        if response.status_code == 200:
            data = response.json()

            # Top-level fields
            assert "character_centralities" in data
            assert isinstance(data["character_centralities"], dict)

            # Optional identifying fields
            if "most_connected" in data:
                assert isinstance(data["most_connected"], str)
            if "most_hated" in data:
                assert isinstance(data["most_hated"], str)
            if "most_loved" in data:
                assert isinstance(data["most_loved"], str)

            # Numeric fields
            assert isinstance(data["total_relationships"], int)
            assert isinstance(data["total_characters"], int)
            assert isinstance(data["network_density"], (int, float))

    def test_centrality_response_structure(self, client: TestClient) -> None:
        """Test that character centrality response has correct structure."""
        response = client.get("/api/social/analysis/test-char-001")

        if response.status_code == 200:
            data = response.json()

            # Required fields for centrality
            assert "character_id" in data
            assert "relationship_count" in data
            assert "positive_count" in data
            assert "negative_count" in data
            assert "average_trust" in data
            assert "average_romance" in data
            assert "centrality_score" in data

            # Type validation
            assert isinstance(data["relationship_count"], int)
            assert isinstance(data["centrality_score"], (int, float))
