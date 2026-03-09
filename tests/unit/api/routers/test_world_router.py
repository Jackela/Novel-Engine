"""
Unit tests for World Router API

Tests cover:
- POST /world/generation - Generate a complete world
- Helper functions for safe enum conversion
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.error_handlers import ServiceUnavailableException, setup_error_handlers
from src.api.routers.world import (
    _safe_era,
    _safe_genre,
    _safe_tone,
    router,
)
from src.contexts.world.domain.entities import Era, Genre, ToneType

pytestmark = pytest.mark.unit


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    setup_error_handlers(app)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestWorldGeneration:
    """Tests for POST /api/world/generation endpoint."""

    @patch("src.api.routers.world.LLMWorldGenerator")
    def test_generate_world_success(
        self, mock_generator_class, client: TestClient
    ) -> None:
        """Test successful world generation."""
        # Setup mock
        mock_generator = MagicMock()
        mock_result = MagicMock()

        # Setup world setting - use a simple class instead of MagicMock
        # to avoid MagicMock's reserved 'name' attribute issue
        class MockWorldSetting:
            id = "world_001"
            name = "Test World"
            description = "A test world"
            genre = Genre.FANTASY
            era = Era.MEDIEVAL
            tone = ToneType.HEROIC
            themes = ["adventure", "magic"]
            magic_level = 5
            technology_level = 3

        mock_result.world_setting = MockWorldSetting()

        # Setup factions
        faction = MagicMock()
        faction.id = "faction_001"
        faction.name = "Test Faction"
        faction.description = "A test faction"
        faction.faction_type = MagicMock(value="kingdom")
        faction.alignment = MagicMock(value="neutral")
        faction.values = ["honor", "strength"]
        faction.goals = ["expand", "protect"]
        faction.influence = 50
        faction.get_allies.return_value = []
        faction.get_enemies.return_value = []
        mock_result.factions = [faction]

        # Setup locations
        location = MagicMock()
        location.id = "loc_001"
        location.name = "Test Location"
        location.description = "A test location"
        location.location_type = MagicMock(value="city")
        location.population = 1000
        location.controlling_faction_id = "faction_001"
        location.notable_features = ["castle", "market"]
        location.get_danger_level.return_value = "low"
        mock_result.locations = [location]

        # Setup events
        event = MagicMock()
        event.id = "event_001"
        event.name = "Test Event"
        event.description = "A test event"
        event.event_type = MagicMock(value="political")
        event.significance = 5
        event.participant_ids = set(["faction_001"])
        mock_result.events = [event]

        mock_result.generation_summary = "Successfully generated world"
        mock_generator.generate.return_value = mock_result
        mock_generator_class.return_value = mock_generator

        payload = {
            "genre": "fantasy",
            "era": "medieval",
            "tone": "heroic",
            "themes": ["adventure", "magic"],
            "magic_level": 5,
            "technology_level": 3,
            "num_factions": 3,
            "num_locations": 5,
            "num_events": 3,
        }

        response = client.post("/api/world/generation", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["world_setting"]["name"] == "Test World"
        assert len(data["factions"]) == 1
        assert len(data["locations"]) == 1
        assert len(data["events"]) == 1
        assert data["generation_summary"] == "Successfully generated world"

    @patch("src.api.routers.world.LLMWorldGenerator")
    def test_generate_world_default_values(
        self, mock_generator_class, client: TestClient
    ) -> None:
        """Test world generation with default values."""
        mock_generator = MagicMock()
        mock_result = MagicMock()

        # Use a simple class to avoid MagicMock's reserved 'name' attribute
        class MockWorldSetting:
            id = "world_002"
            name = "Default World"
            description = "Default description"
            genre = Genre.FANTASY
            era = Era.MEDIEVAL
            tone = ToneType.HEROIC
            themes = ["adventure", "heroism"]
            magic_level = 5
            technology_level = 3

        mock_result.world_setting = MockWorldSetting()
        mock_result.factions = []
        mock_result.locations = []
        mock_result.events = []
        mock_result.generation_summary = "Generated with defaults"

        mock_generator.generate.return_value = mock_result
        mock_generator_class.return_value = mock_generator

        # Send empty payload - should use defaults
        response = client.post("/api/world/generation", json={})
        assert response.status_code == 200

        data = response.json()
        assert data["world_setting"]["genre"] == "fantasy"
        assert data["world_setting"]["era"] == "medieval"

    @patch("src.api.routers.world.LLMWorldGenerator")
    def test_generate_world_failure(
        self, mock_generator_class, client: TestClient
    ) -> None:
        """Test world generation failure."""
        mock_generator = MagicMock()
        mock_result = MagicMock()

        # Use a simple class to avoid MagicMock's reserved 'name' attribute
        class MockWorldSetting:
            name = "Generation Failed"

        mock_result.world_setting = MockWorldSetting()
        mock_result.generation_summary = "Error: Generation failed"
        mock_result.factions = []
        mock_result.locations = []
        mock_result.events = []

        mock_generator.generate.return_value = mock_result
        mock_generator_class.return_value = mock_generator

        payload = {"genre": "fantasy"}

        response = client.post("/api/world/generation", json=payload)
        assert response.status_code == 503

    def test_generate_world_invalid_magic_level(self, client: TestClient) -> None:
        """Test world generation with invalid magic level."""
        payload = {"magic_level": 15}  # Above max of 10

        response = client.post("/api/world/generation", json=payload)
        assert response.status_code == 422

    def test_generate_world_invalid_num_factions(self, client: TestClient) -> None:
        """Test world generation with invalid faction count."""
        payload = {"num_factions": 15}  # Above max of 10

        response = client.post("/api/world/generation", json=payload)
        assert response.status_code == 422

    def test_generate_world_negative_values(self, client: TestClient) -> None:
        """Test world generation with negative values."""
        payload = {"magic_level": -1}

        response = client.post("/api/world/generation", json=payload)
        assert response.status_code == 422


class TestSafeEnumConversion:
    """Tests for safe enum conversion helpers."""

    def test_safe_genre_valid(self) -> None:
        """Test valid genre conversion."""
        assert _safe_genre("fantasy") == Genre.FANTASY
        assert _safe_genre("science_fiction") == Genre.SCIENCE_FICTION
        assert _safe_genre("science-fiction") == Genre.SCIENCE_FICTION
        assert _safe_genre("horror") == Genre.HORROR
        assert _safe_genre("mystery") == Genre.MYSTERY

    def test_safe_genre_invalid_fallback(self) -> None:
        """Test genre conversion falls back to fantasy for unsupported inputs."""
        # "sci-fi" normalizes to "sci_fi" which is not a valid enum value
        assert _safe_genre("sci-fi") == Genre.FANTASY
        assert _safe_genre("sci_fi") == Genre.FANTASY
        assert _safe_genre("sci fi") == Genre.FANTASY

    def test_safe_genre_invalid(self) -> None:
        """Test invalid genre falls back to fantasy."""
        assert _safe_genre("unknown_genre") == Genre.FANTASY
        assert _safe_genre("") == Genre.FANTASY

    def test_safe_era_valid(self) -> None:
        """Test valid era conversion."""
        assert _safe_era("medieval") == Era.MEDIEVAL
        assert _safe_era("modern") == Era.MODERN
        assert _safe_era("ancient") == Era.ANCIENT

    def test_safe_era_with_hyphens(self) -> None:
        """Test era conversion with hyphens."""
        # "industrial" is the valid enum value
        assert _safe_era("industrial") == Era.INDUSTRIAL
        # "industrial-age" normalizes to "industrial_age" which is not valid
        assert _safe_era("industrial-age") == Era.MEDIEVAL

    def test_safe_era_invalid(self) -> None:
        """Test invalid era falls back to medieval."""
        assert _safe_era("unknown_era") == Era.MEDIEVAL

    def test_safe_tone_valid(self) -> None:
        """Test valid tone conversion."""
        assert _safe_tone("heroic") == ToneType.HEROIC
        assert _safe_tone("dark") == ToneType.DARK
        assert _safe_tone("gritty") == ToneType.GRITTY
        assert _safe_tone("epic") == ToneType.EPIC
        assert _safe_tone("light") == ToneType.LIGHT
        assert _safe_tone("hopeful") == ToneType.HOPEFUL

    def test_safe_tone_invalid(self) -> None:
        """Test invalid tone falls back to heroic."""
        assert _safe_tone("unknown_tone") == ToneType.HEROIC


class TestRequestResponseModels:
    """Tests for request/response Pydantic models."""

    def test_world_generation_request_defaults(self) -> None:
        """Test default values in request model."""
        from src.api.routers.world import WorldGenerationRequest

        request = WorldGenerationRequest()

        assert request.genre == "fantasy"
        assert request.era == "medieval"
        assert request.tone == "heroic"
        assert request.themes == ["adventure", "heroism"]
        assert request.magic_level == 5
        assert request.technology_level == 3
        assert request.num_factions == 3
        assert request.num_locations == 5
        assert request.num_events == 3

    def test_world_generation_request_custom(self) -> None:
        """Test custom values in request model."""
        from src.api.routers.world import WorldGenerationRequest

        request = WorldGenerationRequest(
            genre="sci-fi",
            magic_level=8,
            num_factions=5,
        )

        assert request.genre == "sci-fi"
        assert request.magic_level == 8
        assert request.num_factions == 5

    def test_world_setting_response(self) -> None:
        """Test world setting response model."""
        from src.api.routers.world import WorldSettingResponse

        response = WorldSettingResponse(
            id="world_001",
            name="Test World",
            description="A test world",
            genre="fantasy",
            era="medieval",
            tone="heroic",
            themes=["adventure"],
            magic_level=5,
            technology_level=3,
        )

        assert response.id == "world_001"
        assert response.name == "Test World"

    def test_faction_response(self) -> None:
        """Test faction response model."""
        from src.api.routers.world import FactionResponse

        response = FactionResponse(
            id="faction_001",
            name="Test Faction",
            description="A test faction",
            faction_type="kingdom",
            alignment="neutral",
            values=["honor"],
            goals=["expand"],
            influence=50,
        )

        assert response.id == "faction_001"
        assert response.ally_count == 0  # Default
        assert response.enemy_count == 0  # Default

    def test_location_response(self) -> None:
        """Test location response model."""
        from src.api.routers.world import LocationResponse

        response = LocationResponse(
            id="loc_001",
            name="Test Location",
            description="A test location",
            location_type="city",
            population=1000,
            notable_features=["castle"],
            danger_level="low",
        )

        assert response.id == "loc_001"
        assert response.controlling_faction_id is None  # Optional

    def test_generated_event_response(self) -> None:
        """Test generated event response model."""
        from src.api.routers.world import GeneratedEventResponse

        response = GeneratedEventResponse(
            id="event_001",
            name="Test Event",
            description="A test event",
            event_type="political",
            significance=5,
            participants=["faction_001"],
        )

        assert response.id == "event_001"
        assert response.participants == ["faction_001"]

    def test_world_generation_response(self) -> None:
        """Test world generation response model."""
        from src.api.routers.world import (
            WorldGenerationResponse,
            WorldSettingResponse,
        )

        world_setting = WorldSettingResponse(
            id="world_001",
            name="Test World",
            description="A test world",
            genre="fantasy",
            era="medieval",
            tone="heroic",
            themes=["adventure"],
            magic_level=5,
            technology_level=3,
        )

        response = WorldGenerationResponse(
            world_setting=world_setting,
            factions=[],
            locations=[],
            events=[],
            generation_summary="Test generation",
        )

        assert response.world_setting.name == "Test World"
        assert response.generation_summary == "Test generation"
