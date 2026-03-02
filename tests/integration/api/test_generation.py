"""Integration tests for Generation API endpoints.

Tests story generation triggers and result handling.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Generation API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestCharacterGenerationEndpoint:
    """Tests for POST /generation/character endpoint."""

    def test_generate_character_success(self, client):
        """Test generating a character card."""
        response = client.post(
            "/api/generation/character",
            json={
                "concept": "A brave warrior",
                "archetype": "hero",
                "tone": "epic",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "tagline" in data
        assert "bio" in data
        assert "visual_prompt" in data
        assert "traits" in data

    def test_generate_character_with_archetype(self, client):
        """Test generating a character with archetype."""
        response = client.post(
            "/api/generation/character",
            json={
                "concept": "A wise mentor",
                "archetype": "sage",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "traits" in data
        assert len(data["traits"]) > 0

    def test_generate_character_with_tone(self, client):
        """Test generating a character with tone parameter."""
        response = client.post(
            "/api/generation/character",
            json={
                "concept": "A dark rogue",
                "archetype": "scoundrel",
                "tone": "gritty",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "traits" in data

    def test_generate_character_with_all_params(self, client):
        """Test generating a character with all parameters."""
        response = client.post(
            "/api/generation/character",
            json={
                "concept": "A noble knight",
                "archetype": "hero",
                "tone": "epic",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "tagline" in data
        assert "bio" in data
        assert "visual_prompt" in data
        assert "traits" in data
        # Traits list should have at least one item
        assert len(data["traits"]) >= 1

    def test_generate_character_missing_concept(self, client):
        """Test generating character without concept returns 422."""
        response = client.post(
            "/api/generation/character",
            json={"archetype": "hero"},
        )

        assert response.status_code == 422

    def test_generate_character_missing_archetype(self, client):
        """Test generating character without archetype returns 422."""
        response = client.post(
            "/api/generation/character",
            json={"concept": "A hero"},
        )

        assert response.status_code == 422

    def test_generate_character_empty_json(self, client):
        """Test generating character with empty JSON body."""
        response = client.post(
            "/api/generation/character",
            json={},
        )

        assert response.status_code == 422


class TestCharacterProfileGenerationEndpoint:
    """Tests for POST /generation/character-profile endpoint."""

    def test_generate_character_profile_success(self, client):
        """Test generating a detailed character profile."""
        response = client.post(
            "/api/generation/character-profile",
            json={
                "name": "Elena the Wise",
                "archetype": "sage",
                "context": "A powerful wizard from an ancient order",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert data["name"] == "Elena the Wise"
        assert "archetype" in data
        assert "aliases" in data
        assert "traits" in data
        assert "appearance" in data
        assert "backstory" in data
        assert "motivations" in data
        assert "quirks" in data

    def test_generate_character_profile_minimal(self, client):
        """Test generating a character profile with minimal required params."""
        response = client.post(
            "/api/generation/character-profile",
            json={
                "name": "Simple Character",
                "archetype": "hero",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "aliases" in data
        assert "traits" in data
        assert "appearance" in data

    def test_generate_character_profile_all_fields(self, client):
        """Test that all expected fields are in response."""
        response = client.post(
            "/api/generation/character-profile",
            json={
                "name": "Complete Character",
                "archetype": "merchant",
                "context": "Running a shop",
            },
        )

        assert response.status_code == 200
        data = response.json()

        expected_fields = [
            "name",
            "aliases",
            "archetype",
            "traits",
            "appearance",
            "backstory",
            "motivations",
            "quirks",
        ]

        for field in expected_fields:
            assert field in data
            # Check type based on field
            if field in ["aliases", "traits", "motivations", "quirks"]:
                assert isinstance(data[field], list)
            elif field in ["name", "archetype", "appearance", "backstory"]:
                assert isinstance(data[field], str)


class TestCharacterProfileGenerationValidation:
    """Tests for character profile generation endpoint validation."""

    def test_generate_character_profile_missing_name(self, client):
        """Test generating character profile without name returns 422."""
        response = client.post(
            "/api/generation/character-profile",
            json={
                "archetype": "sage",
                "context": "No name provided",
            },
        )

        assert response.status_code == 422

    def test_generate_character_profile_missing_archetype(self, client):
        """Test generating character profile without archetype returns 422."""
        response = client.post(
            "/api/generation/character-profile",
            json={
                "name": "No Archetype",
                "context": "Missing archetype",
            },
        )

        assert response.status_code == 422

    def test_generate_character_profile_with_context(self, client):
        """Test generating character profile with context."""
        response = client.post(
            "/api/generation/character-profile",
            json={
                "name": "Marcus the Brave",
                "archetype": "warrior",
                "context": "Battle-hardened veteran protecting a kingdom",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "Marcus the Brave"
        assert "backstory" in data
        # The generated backstory should exist
        assert len(data["backstory"]) > 0
