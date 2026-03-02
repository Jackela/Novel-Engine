"""Integration tests for Dialogue API endpoints.

Tests character dialogue generation including voice synthesis based on
character psychology, traits, and speaking style.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Dialogue API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestDialogueGenerationEndpoint:
    """Tests for POST /api/dialogue/generate endpoint."""

    def test_generate_dialogue_minimal(self, client):
        """Test dialogue generation with minimal parameters."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-001",
                "context": "The character enters a tavern",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "dialogue" in data
        assert "character_id" in data
        assert data["character_id"] == "char-001"

    def test_generate_dialogue_with_mood(self, client):
        """Test dialogue generation with mood parameter."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-002",
                "context": "A friend betrayed them",
                "mood": "angry",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "dialogue" in data
        assert "tone" in data

    def test_generate_dialogue_with_overrides(self, client):
        """Test dialogue generation with psychology overrides."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-003",
                "context": "Negotiating a deal",
                "psychology_override": {
                    "openness": 0.8,
                    "conscientiousness": 0.2,
                    "extraversion": 0.5,
                    "agreeableness": 0.3,
                    "neuroticism": 0.6,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "dialogue" in data

    def test_generate_dialogue_with_traits(self, client):
        """Test dialogue generation with trait overrides."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-004",
                "context": "Teaching a student",
                "traits_override": ["wise", "patient", "encouraging"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "dialogue" in data

    def test_generate_dialogue_with_speaking_style(self, client):
        """Test dialogue generation with speaking style override."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-005",
                "context": "Addressing a crowd",
                "speaking_style_override": "Boisterous and loud",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "dialogue" in data


class TestDialogueValidation:
    """Tests for dialogue endpoint validation."""

    def test_generate_dialogue_missing_character_id(self, client):
        """Test dialogue generation without character_id returns 422."""
        response = client.post(
            "/api/dialogue/generate",
            json={"context": "Test context"},
        )

        assert response.status_code == 422

    def test_generate_dialogue_missing_context(self, client):
        """Test dialogue generation without context returns 422."""
        response = client.post(
            "/api/dialogue/generate",
            json={"character_id": "char-001"},
        )

        assert response.status_code == 422

    def test_generate_dialogue_empty_context(self, client):
        """Test dialogue generation with empty context."""
        # The schema likely allows empty context, but behavior should be tested
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-001",
                "context": "",
            },
        )

        # May succeed with empty response or fail validation
        assert response.status_code in [200, 422]


class TestDialogueResponseStructure:
    """Tests for dialogue response structure."""

    def test_response_includes_all_fields(self, client):
        """Test that response includes all expected fields."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-structure",
                "context": "Testing response structure",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields
        expected_fields = [
            "dialogue",
            "tone",
            "internal_thought",
            "body_language",
            "character_id",
            "error",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_response_character_id_matches_request(self, client):
        """Test that response character_id matches request."""
        character_id = "unique-char-id-12345"
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": character_id,
                "context": "Testing ID matching",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["character_id"] == character_id


class TestDialogueMoodVariations:
    """Tests for various mood inputs."""

    @pytest.mark.parametrize(
        "mood",
        [
            "happy",
            "sad",
            "angry",
            "fearful",
            "excited",
            "calm",
            "nervous",
            "confident",
        ],
    )
    def test_generate_dialogue_with_various_moods(self, client, mood):
        """Test dialogue generation with various moods."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": f"char-mood-{mood}",
                "context": f"Testing {mood} mood",
                "mood": mood,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "dialogue" in data


class TestDialogueComplexContexts:
    """Tests for complex context scenarios."""

    def test_generate_dialogue_long_context(self, client):
        """Test dialogue generation with long context."""
        long_context = """
        The character stands at the edge of a cliff, overlooking the vast expanse of the kingdom below.
        Smoke rises from distant villages, and the sounds of battle echo from the valley.
        They must make a decision that will affect thousands of lives.
        The weight of leadership presses heavily upon their shoulders.
        """

        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-long-context",
                "context": long_context,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "dialogue" in data

    def test_generate_dialogue_special_characters(self, client):
        """Test dialogue generation with special characters in context."""
        response = client.post(
            "/api/dialogue/generate",
            json={
                "character_id": "char-special",
                "context": "The character says: 'Hello! How are you?' <smiles>",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "dialogue" in data
