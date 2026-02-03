#!/usr/bin/env python3
"""
Character API Integration Tests

Tests the Character API endpoints with full request/response validation.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from src.api.character_api import (
    CharacterAPI,
    CharacterCreationRequest,
    CharacterUpdateRequest,
    CharacterResponse,
    CharacterListResponse,
)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    orchestrator = MagicMock()
    orchestrator.active_agents = {}
    orchestrator.database = MagicMock()
    return orchestrator


@pytest.fixture
def character_api(mock_orchestrator):
    """Create a CharacterAPI instance with mock orchestrator."""
    api = CharacterAPI(mock_orchestrator)
    return api


@pytest.fixture
def sample_character_request():
    """Sample character creation request data."""
    return CharacterCreationRequest(
        agent_id="test_hero_001",
        name="Test Hero",
        background_summary="A brave adventurer from the northern lands",
        personality_traits="brave, curious, kind",
        current_mood=7,
        dominant_emotion="happy",
        energy_level=8,
        stress_level=3,
        skills={"combat": 0.8, "magic": 0.5},
        relationships={"ally_1": 0.9},
        current_location="tavern",
        inventory=["sword", "shield"],
        metadata={"origin": "test"},
    )


@pytest.mark.integration
class TestCharacterCreationRequest:
    """Tests for CharacterCreationRequest validation."""

    def test_valid_request_creation(self, sample_character_request):
        """Test that valid request data creates a request object."""
        assert sample_character_request.agent_id == "test_hero_001"
        assert sample_character_request.name == "Test Hero"
        assert sample_character_request.current_mood == 7

    def test_agent_id_validation_alphanumeric(self):
        """Test that agent_id validates alphanumeric with hyphens/underscores."""
        request = CharacterCreationRequest(
            agent_id="valid-agent_123",
            name="Test",
        )
        assert request.agent_id == "valid-agent_123"

    def test_agent_id_validation_lowercase(self):
        """Test that agent_id is lowercased."""
        request = CharacterCreationRequest(
            agent_id="UPPERCASE_ID",
            name="Test",
        )
        assert request.agent_id == "uppercase_id"

    def test_agent_id_validation_invalid_chars(self):
        """Test that invalid agent_id characters raise error."""
        with pytest.raises(ValueError, match="alphanumeric"):
            CharacterCreationRequest(
                agent_id="invalid@id!",
                name="Test",
            )

    def test_skill_values_validation_valid(self):
        """Test that valid skill values pass validation."""
        request = CharacterCreationRequest(
            agent_id="test",
            name="Test",
            skills={"combat": 0.0, "magic": 1.0, "stealth": 0.5},
        )
        assert request.skills["combat"] == 0.0
        assert request.skills["magic"] == 1.0

    def test_skill_values_validation_out_of_range(self):
        """Test that skill values outside 0-1 raise error."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            CharacterCreationRequest(
                agent_id="test",
                name="Test",
                skills={"combat": 1.5},
            )

    def test_mood_range_validation(self):
        """Test that mood values are within 1-10 range."""
        request = CharacterCreationRequest(
            agent_id="test",
            name="Test",
            current_mood=1,
        )
        assert request.current_mood == 1

        request = CharacterCreationRequest(
            agent_id="test",
            name="Test",
            current_mood=10,
        )
        assert request.current_mood == 10

    def test_name_length_validation(self):
        """Test that name length constraints are enforced."""
        # Too short
        with pytest.raises(ValueError):
            CharacterCreationRequest(
                agent_id="test",
                name="A",  # min_length=2
            )


@pytest.mark.integration
class TestCharacterAPI:
    """Integration tests for CharacterAPI class."""

    def test_api_initialization(self, mock_orchestrator):
        """Test that API initializes correctly."""
        api = CharacterAPI(mock_orchestrator)
        assert api.orchestrator == mock_orchestrator

    def test_api_set_orchestrator(self, character_api):
        """Test that orchestrator can be set after initialization."""
        new_orchestrator = MagicMock()
        character_api.set_orchestrator(new_orchestrator)
        assert character_api.orchestrator == new_orchestrator


@pytest.mark.integration
class TestCharacterResponseModels:
    """Tests for response model serialization."""

    def test_character_response_serialization(self):
        """Test that CharacterResponse serializes correctly."""
        now = datetime.now()
        response = CharacterResponse(
            agent_id="hero_001",
            name="Hero Name",
            current_status="active",
            created_at=now,
            last_updated=now,
        )

        data = response.model_dump()
        assert data["agent_id"] == "hero_001"
        assert data["name"] == "Hero Name"
        assert data["current_status"] == "active"

    def test_character_list_response_serialization(self):
        """Test that CharacterListResponse serializes correctly."""
        now = datetime.now()
        characters = [
            CharacterResponse(
                agent_id="hero_001",
                name="Hero 1",
                current_status="active",
                created_at=now,
                last_updated=now,
            ),
            CharacterResponse(
                agent_id="hero_002",
                name="Hero 2",
                current_status="idle",
                created_at=now,
                last_updated=now,
            ),
        ]

        response = CharacterListResponse(characters=characters)
        data = response.model_dump()

        assert len(data["characters"]) == 2
        assert data["characters"][0]["agent_id"] == "hero_001"
        assert data["characters"][1]["agent_id"] == "hero_002"


@pytest.mark.integration
class TestCharacterUpdateRequest:
    """Tests for CharacterUpdateRequest validation."""

    def test_partial_update_request(self):
        """Test that partial updates are allowed."""
        request = CharacterUpdateRequest(name="New Name")
        assert request.name == "New Name"
        assert request.background_summary is None

    def test_full_update_request(self):
        """Test that full updates work."""
        request = CharacterUpdateRequest(
            name="Updated Name",
            background_summary="Updated background",
            personality_traits="updated, traits",
            skills={"new_skill": 0.7},
        )
        assert request.name == "Updated Name"
        assert request.skills["new_skill"] == 0.7
