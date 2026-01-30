"""Unit tests for LLMWorldGenerator."""

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.application.ports.world_generator_port import (
    WorldGenerationInput,
    WorldGenerationResult,
)
from src.contexts.world.domain.entities import (
    Era,
    EventSignificance,
    EventType,
    FactionAlignment,
    FactionType,
    Genre,
    LocationType,
    ToneType,
)
from src.contexts.world.infrastructure.generators.llm_world_generator import (
    LLMWorldGenerator,
)


@pytest.fixture
def sample_llm_response() -> Dict[str, Any]:
    """Sample LLM response for testing."""
    return {
        "world_setting": {
            "name": "Aethermoor",
            "description": "A realm where magic flows through ancient ley lines.",
            "themes": ["power", "corruption", "redemption"],
            "world_rules": ["Magic requires ley line proximity"],
            "cultural_influences": ["Celtic", "Norse"],
        },
        "locations": [
            {
                "temp_id": "temp_location_1",
                "name": "Silverhold",
                "description": "The gleaming capital city.",
                "location_type": "capital",
                "climate": "temperate",
                "status": "thriving",
                "population": 50000,
                "notable_features": ["Crystal Spire", "Grand Market"],
                "resources": ["silver", "magical artifacts"],
                "dangers": [],
                "accessibility": 80,
                "wealth_level": 75,
                "magic_concentration": 60,
                "parent_location_id": None,
                "child_location_ids": ["temp_location_2"],
                "connections": ["temp_location_3"],
            },
            {
                "temp_id": "temp_location_2",
                "name": "The Undercroft",
                "description": "Ancient tunnels beneath Silverhold.",
                "location_type": "dungeon",
                "climate": "artificial",
                "status": "hidden",
                "population": 0,
                "notable_features": ["Forgotten shrine"],
                "resources": [],
                "dangers": ["collapsed tunnels", "undead"],
                "accessibility": 20,
                "wealth_level": 30,
                "magic_concentration": 80,
                "parent_location_id": "temp_location_1",
                "child_location_ids": [],
                "connections": [],
            },
            {
                "temp_id": "temp_location_3",
                "name": "Thornwood Forest",
                "description": "A dangerous wilderness.",
                "location_type": "forest",
                "climate": "temperate",
                "status": "stable",
                "population": 100,
                "notable_features": ["Ancient oak grove"],
                "resources": ["timber", "herbs"],
                "dangers": ["wolves", "bandits"],
                "accessibility": 40,
                "wealth_level": 20,
                "magic_concentration": 40,
                "parent_location_id": None,
                "child_location_ids": [],
                "connections": ["temp_location_1"],
            },
        ],
        "factions": [
            {
                "temp_id": "temp_faction_1",
                "name": "The Silver Crown",
                "description": "The ruling monarchy of Aethermoor.",
                "faction_type": "kingdom",
                "alignment": "lawful_neutral",
                "status": "active",
                "leader_name": "Queen Isolde III",
                "founding_date": "Year 1 of the Current Era",
                "values": ["order", "tradition", "prosperity"],
                "goals": ["Maintain peace", "Expand trade"],
                "resources": ["treasury", "army", "mages"],
                "influence": 85,
                "military_strength": 70,
                "economic_power": 80,
                "member_count": 10000,
                "headquarters_id": "temp_location_1",
                "territories": ["temp_location_1", "temp_location_3"],
            },
            {
                "temp_id": "temp_faction_2",
                "name": "The Shadow Circle",
                "description": "A secretive cabal of rogue mages.",
                "faction_type": "secret_society",
                "alignment": "chaotic_neutral",
                "status": "hidden",
                "leader_name": None,
                "founding_date": "Unknown",
                "values": ["knowledge", "freedom", "power"],
                "goals": ["Uncover forbidden magic"],
                "resources": ["ancient texts", "hidden agents"],
                "influence": 30,
                "military_strength": 20,
                "economic_power": 40,
                "member_count": 50,
                "headquarters_id": "temp_location_2",
                "territories": [],
            },
        ],
        "events": [
            {
                "temp_id": "temp_event_1",
                "name": "The Founding of Silverhold",
                "description": "Queen Isolde I established the capital.",
                "event_type": "founding",
                "significance": "major",
                "outcome": "positive",
                "date_description": "Year 1 of the Current Era",
                "duration_description": "Several months",
                "location_ids": ["temp_location_1"],
                "faction_ids": ["temp_faction_1"],
                "key_figures": ["Queen Isolde I"],
                "causes": ["Need for centralized power"],
                "consequences": ["Unified kingdom", "Trade routes established"],
                "preceding_event_ids": [],
                "following_event_ids": ["temp_event_2"],
                "related_event_ids": [],
                "is_secret": False,
                "narrative_importance": 70,
            },
            {
                "temp_id": "temp_event_2",
                "name": "Discovery of the Undercroft",
                "description": "Workers uncovered ancient tunnels.",
                "event_type": "discovery",
                "significance": "moderate",
                "outcome": "mixed",
                "date_description": "Year 50 of the Current Era",
                "duration_description": None,
                "location_ids": ["temp_location_1", "temp_location_2"],
                "faction_ids": [],
                "key_figures": ["Master Builder Thom"],
                "causes": ["City expansion"],
                "consequences": ["The Shadow Circle formed", "Knowledge lost"],
                "preceding_event_ids": ["temp_event_1"],
                "following_event_ids": [],
                "related_event_ids": [],
                "is_secret": False,
                "narrative_importance": 50,
            },
        ],
    }


@pytest.fixture
def generator() -> LLMWorldGenerator:
    """Create a generator instance for testing."""
    return LLMWorldGenerator()


class TestWorldGenerationInput:
    """Tests for WorldGenerationInput dataclass."""

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Test default input values."""
        request = WorldGenerationInput()
        assert request.genre == Genre.FANTASY
        assert request.era == Era.MEDIEVAL
        assert request.tone == ToneType.HEROIC
        assert request.magic_level == 5
        assert request.technology_level == 3
        assert request.num_factions == 3
        assert request.num_locations == 5
        assert request.num_events == 3

    @pytest.mark.unit
    def test_custom_values(self) -> None:
        """Test custom input values."""
        request = WorldGenerationInput(
            genre=Genre.SCIENCE_FICTION,
            era=Era.FAR_FUTURE,
            tone=ToneType.DARK,
            themes=["survival", "technology"],
            magic_level=0,
            technology_level=9,
            num_factions=5,
            num_locations=8,
            num_events=4,
            custom_constraints="Include a space station",
        )
        assert request.genre == Genre.SCIENCE_FICTION
        assert request.technology_level == 9
        assert request.custom_constraints == "Include a space station"

    @pytest.mark.unit
    def test_invalid_magic_level_raises(self) -> None:
        """Test that invalid magic level raises ValueError."""
        with pytest.raises(ValueError, match="magic_level must be between 0 and 10"):
            WorldGenerationInput(magic_level=11)

    @pytest.mark.unit
    def test_invalid_technology_level_raises(self) -> None:
        """Test that invalid technology level raises ValueError."""
        with pytest.raises(ValueError, match="technology_level must be between 0 and 10"):
            WorldGenerationInput(technology_level=-1)

    @pytest.mark.unit
    def test_invalid_num_factions_raises(self) -> None:
        """Test that invalid faction count raises ValueError."""
        with pytest.raises(ValueError, match="num_factions must be between 1 and 10"):
            WorldGenerationInput(num_factions=0)

    @pytest.mark.unit
    def test_invalid_num_locations_raises(self) -> None:
        """Test that invalid location count raises ValueError."""
        with pytest.raises(ValueError, match="num_locations must be between 1 and 10"):
            WorldGenerationInput(num_locations=15)

    @pytest.mark.unit
    def test_invalid_num_events_raises(self) -> None:
        """Test that invalid event count raises ValueError."""
        with pytest.raises(ValueError, match="num_events must be between 1 and 10"):
            WorldGenerationInput(num_events=0)


class TestLLMWorldGeneratorParsing:
    """Tests for LLMWorldGenerator JSON parsing."""

    @pytest.mark.unit
    def test_extract_json_direct(self, generator: LLMWorldGenerator) -> None:
        """Test direct JSON extraction."""
        content = '{"world_setting": {"name": "Test"}}'
        result = generator._extract_json(content)
        assert result["world_setting"]["name"] == "Test"

    @pytest.mark.unit
    def test_extract_json_from_markdown(self, generator: LLMWorldGenerator) -> None:
        """Test JSON extraction from markdown code block."""
        content = """Here is the world:
```json
{"world_setting": {"name": "MarkdownWorld"}}
```
That's it!"""
        result = generator._extract_json(content)
        assert result["world_setting"]["name"] == "MarkdownWorld"

    @pytest.mark.unit
    def test_extract_json_with_surrounding_text(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test JSON extraction with surrounding text."""
        content = 'Here is the result: {"world_setting": {"name": "Embedded"}} end'
        result = generator._extract_json(content)
        assert result["world_setting"]["name"] == "Embedded"

    @pytest.mark.unit
    def test_extract_json_invalid_raises(self, generator: LLMWorldGenerator) -> None:
        """Test that invalid JSON raises error."""
        content = "This is not JSON at all"
        with pytest.raises(json.JSONDecodeError):
            generator._extract_json(content)


class TestLLMWorldGeneratorBuilding:
    """Tests for LLMWorldGenerator entity building."""

    @pytest.mark.unit
    def test_build_world_setting(
        self,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test WorldSetting building from parsed data."""
        request = WorldGenerationInput()
        world = generator._build_world_setting(
            sample_llm_response["world_setting"], request
        )

        assert world.name == "Aethermoor"
        assert "magic flows" in world.description
        assert "power" in world.themes
        assert world.genre == Genre.FANTASY
        assert world.era == Era.MEDIEVAL

    @pytest.mark.unit
    def test_build_locations(
        self,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test Location building from parsed data."""
        locations, id_map = generator._build_locations(sample_llm_response["locations"])

        assert len(locations) == 3
        assert len(id_map) == 3

        # Check first location
        silverhold = locations[0]
        assert silverhold.name == "Silverhold"
        assert silverhold.location_type == LocationType.CAPITAL
        assert silverhold.population == 50000
        assert "Crystal Spire" in silverhold.notable_features

        # Check parent/child relationship resolved
        undercroft = locations[1]
        assert undercroft.parent_location_id == silverhold.id
        assert undercroft.id in silverhold.child_location_ids

    @pytest.mark.unit
    def test_build_factions(
        self,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test Faction building from parsed data."""
        locations, location_id_map = generator._build_locations(
            sample_llm_response["locations"]
        )
        factions, faction_id_map = generator._build_factions(
            sample_llm_response["factions"], location_id_map
        )

        assert len(factions) == 2
        assert len(faction_id_map) == 2

        # Check first faction
        crown = factions[0]
        assert crown.name == "The Silver Crown"
        assert crown.faction_type == FactionType.KINGDOM
        assert crown.alignment == FactionAlignment.LAWFUL_NEUTRAL
        assert crown.leader_name == "Queen Isolde III"
        assert crown.headquarters_id == locations[0].id  # Silverhold

        # Check territories resolved
        assert locations[0].id in crown.territories  # Silverhold
        assert locations[2].id in crown.territories  # Thornwood

    @pytest.mark.unit
    def test_build_events(
        self,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test HistoryEvent building from parsed data."""
        locations, location_id_map = generator._build_locations(
            sample_llm_response["locations"]
        )
        factions, faction_id_map = generator._build_factions(
            sample_llm_response["factions"], location_id_map
        )
        events = generator._build_events(
            sample_llm_response["events"], location_id_map, faction_id_map
        )

        assert len(events) == 2

        # Check first event
        founding = events[0]
        assert founding.name == "The Founding of Silverhold"
        assert founding.event_type == EventType.FOUNDING
        assert founding.significance == EventSignificance.MAJOR
        assert "Queen Isolde I" in founding.key_figures
        assert locations[0].id in founding.location_ids

        # Check event relationships resolved
        discovery = events[1]
        assert founding.id in discovery.preceding_event_ids
        assert discovery.id in founding.following_event_ids

    @pytest.mark.unit
    def test_build_result_complete(
        self,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test complete result building."""
        request = WorldGenerationInput()
        result = generator._build_result(sample_llm_response, request)

        assert isinstance(result, WorldGenerationResult)
        assert result.world_setting.name == "Aethermoor"
        assert len(result.locations) == 3
        assert len(result.factions) == 2
        assert len(result.events) == 2
        assert result.total_entities == 8  # 1 world + 3 loc + 2 fac + 2 events

    @pytest.mark.unit
    def test_parse_enum_valid(self, generator: LLMWorldGenerator) -> None:
        """Test enum parsing with valid value."""
        result = generator._parse_enum(Genre, "fantasy", Genre.HORROR)
        assert result == Genre.FANTASY

    @pytest.mark.unit
    def test_parse_enum_invalid_returns_default(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test enum parsing with invalid value returns default."""
        result = generator._parse_enum(Genre, "invalid_genre", Genre.HORROR)
        assert result == Genre.HORROR

    @pytest.mark.unit
    def test_parse_enum_none_returns_default(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test enum parsing with None returns default."""
        result = generator._parse_enum(Genre, None, Genre.HORROR)
        assert result == Genre.HORROR


class TestLLMWorldGeneratorPrompt:
    """Tests for prompt building."""

    @pytest.mark.unit
    def test_build_user_prompt_includes_all_params(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that user prompt includes all request parameters."""
        request = WorldGenerationInput(
            genre=Genre.CYBERPUNK,
            era=Era.NEAR_FUTURE,
            tone=ToneType.GRITTY,
            themes=["technology", "dystopia"],
            magic_level=1,
            technology_level=9,
            num_factions=4,
            num_locations=6,
            num_events=5,
            custom_constraints="Include megacorporations",
        )
        prompt = generator._build_user_prompt(request)

        assert "cyberpunk" in prompt.lower()
        assert "near_future" in prompt.lower()
        assert "gritty" in prompt.lower()
        assert "technology, dystopia" in prompt.lower()
        assert "Magic Level: 1/10" in prompt
        assert "Technology Level: 9/10" in prompt
        assert "Number of Factions: 4" in prompt
        assert "Number of Locations: 6" in prompt
        assert "Number of Historical Events: 5" in prompt
        assert "Include megacorporations" in prompt


class TestLLMWorldGeneratorIntegration:
    """Integration-style tests with mocked API."""

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_generate_success(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test successful generation with mocked API."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(sample_llm_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        # Set API key for test
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            request = WorldGenerationInput()
            result = generator.generate(request)

        assert result.world_setting.name == "Aethermoor"
        assert len(result.factions) == 2
        assert len(result.locations) == 3
        assert len(result.events) == 2

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_generate_api_error_returns_error_result(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that API errors return error result."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            request = WorldGenerationInput()
            result = generator.generate(request)

        assert result.world_setting.name == "Generation Failed"
        assert "500" in result.generation_summary
        assert len(result.factions) == 0
        assert len(result.locations) == 0

    @pytest.mark.unit
    def test_generate_missing_api_key_returns_error_result(self) -> None:
        """Test that missing API key returns error result."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            # Create generator inside patch to ensure it reads empty API key
            gen = LLMWorldGenerator()
            gen._api_key = ""  # Explicitly set to empty
            request = WorldGenerationInput()
            result = gen.generate(request)

        assert result.world_setting.name == "Generation Failed"
        assert "GEMINI_API_KEY" in result.generation_summary


class TestWorldGenerationResult:
    """Tests for WorldGenerationResult dataclass."""

    @pytest.mark.unit
    def test_total_entities_count(
        self,
        generator: LLMWorldGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test total entities count property."""
        request = WorldGenerationInput()
        result = generator._build_result(sample_llm_response, request)

        # 1 world + 3 locations + 2 factions + 2 events = 8
        assert result.total_entities == 8

    @pytest.mark.unit
    def test_empty_result(self) -> None:
        """Test result with only world setting."""
        from src.contexts.world.domain.entities import WorldSetting

        world = WorldSetting(name="Empty World")
        result = WorldGenerationResult(
            world_setting=world,
            generation_summary="Test",
        )

        assert result.total_entities == 1
        assert len(result.factions) == 0
        assert len(result.locations) == 0
        assert len(result.events) == 0
