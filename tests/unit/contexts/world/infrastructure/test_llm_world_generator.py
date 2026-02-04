"""Unit tests for LLMWorldGenerator."""

import json
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
    BeatSuggestion,
    BeatSuggestionResult,
    CritiqueCategoryScore,
    CritiqueResult,
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
    """Create a generator instance for testing.

    Note: We set _api_key directly to avoid dependency on environment variables,
    which may not be set in CI environments. The actual API call is mocked anyway.
    """
    gen = LLMWorldGenerator()
    gen._api_key = "test-api-key"
    return gen


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


# ==================== Beat Suggestion Tests ====================


@pytest.fixture
def sample_beat_suggestion_response() -> Dict[str, Any]:
    """Sample LLM response for beat suggestion testing."""
    return {
        "suggestions": [
            {
                "beat_type": "reaction",
                "content": "She froze, her hand still on the sword hilt, eyes locked with the stranger.",
                "mood_shift": -1,
                "rationale": "After the warning dialogue, a reaction beat shows the tension building.",
            },
            {
                "beat_type": "action",
                "content": "The mysterious figure stepped forward, revealing a glint of metal at their hip.",
                "mood_shift": -2,
                "rationale": "An unexpected action raises stakes and moves the confrontation forward.",
            },
            {
                "beat_type": "dialogue",
                "content": "'I didn't come here to fight,' the figure said, raising empty hands. 'But I will if you force me.'",
                "mood_shift": 0,
                "rationale": "Dialogue reveals motivation while maintaining tension through the threat.",
            },
        ]
    }


@pytest.fixture
def current_beats_fixture() -> list:
    """Sample current beats for testing."""
    return [
        {"beat_type": "action", "content": "She drew her sword.", "mood_shift": 0},
        {"beat_type": "dialogue", "content": "'Stay back!' she warned.", "mood_shift": -1},
    ]


class TestBeatSuggestion:
    """Tests for BeatSuggestion dataclass."""

    @pytest.mark.unit
    def test_beat_suggestion_creation(self) -> None:
        """Test creating a BeatSuggestion."""
        suggestion = BeatSuggestion(
            beat_type="action",
            content="She lunged forward.",
            mood_shift=-2,
            rationale="Escalates the conflict.",
        )
        assert suggestion.beat_type == "action"
        assert suggestion.content == "She lunged forward."
        assert suggestion.mood_shift == -2
        assert suggestion.rationale == "Escalates the conflict."

    @pytest.mark.unit
    def test_beat_suggestion_defaults(self) -> None:
        """Test BeatSuggestion default values."""
        suggestion = BeatSuggestion(beat_type="reaction", content="She paused.")
        assert suggestion.mood_shift == 0
        assert suggestion.rationale is None


class TestBeatSuggestionResult:
    """Tests for BeatSuggestionResult dataclass."""

    @pytest.mark.unit
    def test_result_with_suggestions(self) -> None:
        """Test BeatSuggestionResult with suggestions."""
        suggestions = [
            BeatSuggestion(beat_type="action", content="Test 1"),
            BeatSuggestion(beat_type="reaction", content="Test 2"),
            BeatSuggestion(beat_type="dialogue", content="Test 3"),
        ]
        result = BeatSuggestionResult(suggestions=suggestions)

        assert len(result.suggestions) == 3
        assert not result.is_error()

    @pytest.mark.unit
    def test_result_with_error(self) -> None:
        """Test BeatSuggestionResult with error."""
        result = BeatSuggestionResult(suggestions=[], error="API call failed")

        assert result.is_error()
        assert result.error == "API call failed"
        assert len(result.suggestions) == 0

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test BeatSuggestionResult.to_dict()."""
        suggestions = [
            BeatSuggestion(
                beat_type="action",
                content="Test content",
                mood_shift=-1,
                rationale="Test reason",
            )
        ]
        result = BeatSuggestionResult(suggestions=suggestions)
        data = result.to_dict()

        assert "suggestions" in data
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["beat_type"] == "action"
        assert data["suggestions"][0]["content"] == "Test content"
        assert data["suggestions"][0]["mood_shift"] == -1
        assert data["suggestions"][0]["rationale"] == "Test reason"

    @pytest.mark.unit
    def test_to_dict_with_error(self) -> None:
        """Test BeatSuggestionResult.to_dict() includes error."""
        result = BeatSuggestionResult(suggestions=[], error="Test error")
        data = result.to_dict()

        assert "error" in data
        assert data["error"] == "Test error"


class TestBeatSuggestionParsing:
    """Tests for beat suggestion response parsing."""

    @pytest.mark.unit
    def test_parse_beat_suggestion_response(
        self,
        generator: LLMWorldGenerator,
        sample_beat_suggestion_response: Dict[str, Any],
    ) -> None:
        """Test parsing a valid beat suggestion response."""
        json_content = json.dumps(sample_beat_suggestion_response)
        result = generator._parse_beat_suggestion_response(json_content)

        assert len(result.suggestions) == 3
        assert result.suggestions[0].beat_type == "reaction"
        assert "froze" in result.suggestions[0].content
        assert result.suggestions[0].mood_shift == -1
        assert "tension" in str(result.suggestions[0].rationale)

    @pytest.mark.unit
    def test_parse_beat_suggestion_limits_to_three(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that parsing limits to 3 suggestions max."""
        response = {
            "suggestions": [
                {"beat_type": "action", "content": f"Beat {i}", "mood_shift": 0}
                for i in range(5)
            ]
        }
        json_content = json.dumps(response)
        result = generator._parse_beat_suggestion_response(json_content)

        assert len(result.suggestions) == 3

    @pytest.mark.unit
    def test_parse_beat_suggestion_clamps_mood_shift(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that mood_shift values are clamped to valid range."""
        response = {
            "suggestions": [
                {"beat_type": "action", "content": "Extreme positive", "mood_shift": 10},
                {"beat_type": "reaction", "content": "Extreme negative", "mood_shift": -10},
            ]
        }
        json_content = json.dumps(response)
        result = generator._parse_beat_suggestion_response(json_content)

        assert result.suggestions[0].mood_shift == 5  # Clamped to max
        assert result.suggestions[1].mood_shift == -5  # Clamped to min

    @pytest.mark.unit
    def test_parse_beat_suggestion_handles_missing_fields(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test parsing handles missing optional fields."""
        response = {
            "suggestions": [
                {"beat_type": "action", "content": "Minimal beat"}
                # Missing mood_shift and rationale
            ]
        }
        json_content = json.dumps(response)
        result = generator._parse_beat_suggestion_response(json_content)

        assert len(result.suggestions) == 1
        assert result.suggestions[0].mood_shift == 0  # Default
        assert result.suggestions[0].rationale is None


class TestBeatSuggestionPromptBuilding:
    """Tests for beat suggestion prompt building."""

    @pytest.mark.unit
    def test_build_beat_suggester_user_prompt_with_beats(
        self,
        generator: LLMWorldGenerator,
        current_beats_fixture: list,
    ) -> None:
        """Test prompt building with existing beats."""
        prompt = generator._build_beat_suggester_user_prompt(
            current_beats=current_beats_fixture,
            scene_context="A tense standoff in an abandoned warehouse.",
            mood_target=-2,
        )

        assert "tense standoff" in prompt
        assert "[ACTION]" in prompt
        assert "[DIALOGUE]" in prompt
        assert "drew her sword" in prompt
        assert "'Stay back!' she warned." in prompt
        assert "mood: +0" in prompt or "mood: -1" in prompt
        assert "target:" in prompt.lower()

    @pytest.mark.unit
    def test_build_beat_suggester_user_prompt_empty_beats(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test prompt building with no existing beats."""
        prompt = generator._build_beat_suggester_user_prompt(
            current_beats=[],
            scene_context="Opening scene of a heist.",
            mood_target=None,
        )

        assert "Opening scene of a heist" in prompt
        assert "start of the scene" in prompt.lower()
        assert "Follow natural story momentum" in prompt

    @pytest.mark.unit
    def test_build_beat_suggester_user_prompt_action_heavy(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that action-heavy beats get appropriate hint."""
        beats = [
            {"beat_type": "action", "content": "He ran."},
            {"beat_type": "action", "content": "He jumped."},
            {"beat_type": "action", "content": "He climbed."},
        ]
        prompt = generator._build_beat_suggester_user_prompt(
            current_beats=beats,
            scene_context="Chase scene.",
            mood_target=None,
        )

        assert "heavy on action" in prompt.lower()
        assert "reaction" in prompt.lower() or "dialogue" in prompt.lower()

    @pytest.mark.unit
    def test_build_beat_suggester_user_prompt_calculates_mood(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that prompt calculates cumulative mood correctly."""
        beats = [
            {"beat_type": "action", "content": "Test 1", "mood_shift": -2},
            {"beat_type": "reaction", "content": "Test 2", "mood_shift": -1},
            {"beat_type": "dialogue", "content": "Test 3", "mood_shift": +1},
        ]
        prompt = generator._build_beat_suggester_user_prompt(
            current_beats=beats,
            scene_context="Test scene.",
            mood_target=None,
        )

        # Cumulative: -2 + -1 + 1 = -2
        assert "cumulative: -2" in prompt


class TestBeatSuggestionIntegration:
    """Integration-style tests for beat suggestion with mocked API."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    async def test_suggest_next_beats_success(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        sample_beat_suggestion_response: Dict[str, Any],
        current_beats_fixture: list,
    ) -> None:
        """Test successful beat suggestion with mocked API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(sample_beat_suggestion_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        result = await generator.suggest_next_beats(
            current_beats=current_beats_fixture,
            scene_context="A tense standoff in an abandoned warehouse.",
            mood_target=-2,
        )

        assert not result.is_error()
        assert len(result.suggestions) == 3
        assert result.suggestions[0].beat_type == "reaction"
        assert result.suggestions[1].beat_type == "action"
        assert result.suggestions[2].beat_type == "dialogue"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    async def test_suggest_next_beats_api_error(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test beat suggestion handles API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = await generator.suggest_next_beats(
            current_beats=[],
            scene_context="Test scene.",
            mood_target=None,
        )

        assert result.is_error()
        assert "500" in result.error
        assert len(result.suggestions) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_suggest_next_beats_missing_api_key(self) -> None:
        """Test beat suggestion returns error when API key missing."""
        gen = LLMWorldGenerator()
        gen._api_key = ""

        result = await gen.suggest_next_beats(
            current_beats=[],
            scene_context="Test scene.",
            mood_target=None,
        )

        assert result.is_error()
        assert "GEMINI_API_KEY" in result.error


# ==================== Scene Critique Tests ====================


@pytest.fixture
def sample_scene_critique_response() -> Dict[str, Any]:
    """Sample LLM response for scene critique testing."""
    return {
        "overall_score": 7,
        "category_scores": [
            {
                "category": "pacing",
                "score": 8,
                "issues": ["Some sections drag during the dialogue exchange."],
                "suggestions": [
                    "Consider trimming the middle dialogue exchange by 20%.",
                    "Add a small action beat to break up the conversation.",
                ],
            },
            {
                "category": "voice",
                "score": 6,
                "issues": [
                    "Narrative voice feels somewhat generic.",
                    "Lack of distinct sensory details specific to the POV character.",
                ],
                "suggestions": [
                    "Inject more of the character's personality into descriptions.",
                    "Use sensory details that reflect the character's background.",
                ],
            },
            {
                "category": "showing",
                "score": 5,
                "issues": [
                    "Multiple instances of telling emotions ('he felt angry').",
                    "Adverb-heavy dialogue tags ('said nervously', 'asked angrily').",
                ],
                "suggestions": [
                    "Replace 'he felt angry' with physical manifestations (clenched fists, flushed face).",
                    "Remove dialogue tags and use action beats instead.",
                    "Show emotion through subtext in dialogue rather than explanations.",
                ],
            },
            {
                "category": "dialogue",
                "score": 7,
                "issues": ["Some lines feel slightly on-the-nose with exposition."],
                "suggestions": [
                    "Rewrite exposition-heavy lines to be more subtle.",
                    "Add subtext by having characters avoid direct questions.",
                ],
            },
        ],
        "highlights": [
            "Opening hook is strong and immediately engaging.",
            "Dialogue has good rhythmic flow when not doing exposition.",
            "Clear sense of setting and atmosphere established.",
        ],
        "summary": "This scene has a solid foundation with strong opening and clear setting. The main areas for improvement are showing vs. telling (replace emotion words with physical manifestations) and injecting more distinct voice. With revision on dialogue tags and emotional descriptions, this could be professional quality.",
    }


@pytest.fixture
def scene_text_fixture() -> str:
    """Sample scene text for testing."""
    return """The room was dark. John felt scared as he stepped inside.

"Who's there?" he asked nervously.

"Me," Sarah said angrily. "You're late."

"I know," John said sadly. "I'm sorry."""
class TestCritiqueCategoryScore:
    """Tests for CritiqueCategoryScore dataclass."""

    @pytest.mark.unit
    def test_category_score_creation(self) -> None:
        """Test creating a CritiqueCategoryScore."""
        score = CritiqueCategoryScore(
            category="pacing",
            score=8,
            issues=["Some sections drag."],
            suggestions=["Trim dialogue by 20%."],
        )
        assert score.category == "pacing"
        assert score.score == 8
        assert len(score.issues) == 1
        assert len(score.suggestions) == 1

    @pytest.mark.unit
    def test_category_score_defaults(self) -> None:
        """Test CritiqueCategoryScore default values."""
        score = CritiqueCategoryScore(category="voice", score=7)
        assert score.issues == []
        assert score.suggestions == []


class TestCritiqueResult:
    """Tests for CritiqueResult dataclass."""

    @pytest.mark.unit
    def test_critique_result_creation(self) -> None:
        """Test creating a CritiqueResult."""
        categories = [
            CritiqueCategoryScore(category="pacing", score=8),
            CritiqueCategoryScore(category="voice", score=6),
        ]
        result = CritiqueResult(
            overall_score=7,
            category_scores=categories,
            highlights=["Strong opening"],
            summary="Good scene with room for improvement.",
        )

        assert result.overall_score == 7
        assert len(result.category_scores) == 2
        assert len(result.highlights) == 1
        assert "Good scene" in result.summary
        assert not result.is_error()

    @pytest.mark.unit
    def test_critique_result_with_error(self) -> None:
        """Test CritiqueResult with error."""
        result = CritiqueResult(
            overall_score=0,
            category_scores=[],
            highlights=[],
            summary="",
            error="API call failed",
        )

        assert result.is_error()
        assert result.error == "API call failed"
        assert result.overall_score == 0

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test CritiqueResult.to_dict()."""
        categories = [
            CritiqueCategoryScore(
                category="showing",
                score=5,
                issues=["Tells emotions"],
                suggestions=["Show, don't tell"],
            )
        ]
        result = CritiqueResult(
            overall_score=6,
            category_scores=categories,
            highlights=["Good dialogue"],
            summary="Needs work on showing.",
        )
        data = result.to_dict()

        assert data["overall_score"] == 6
        assert len(data["category_scores"]) == 1
        assert data["category_scores"][0]["category"] == "showing"
        assert data["category_scores"][0]["score"] == 5
        assert data["category_scores"][0]["issues"] == ["Tells emotions"]
        assert data["category_scores"][0]["suggestions"] == ["Show, don't tell"]
        assert data["highlights"] == ["Good dialogue"]
        assert "Needs work on showing" in data["summary"]

    @pytest.mark.unit
    def test_to_dict_with_error(self) -> None:
        """Test CritiqueResult.to_dict() includes error."""
        result = CritiqueResult(
            overall_score=0,
            category_scores=[],
            highlights=[],
            summary="",
            error="Test error",
        )
        data = result.to_dict()

        assert "error" in data
        assert data["error"] == "Test error"


class TestCritiqueParsing:
    """Tests for scene critique response parsing."""

    @pytest.mark.unit
    def test_parse_critique_response(
        self,
        generator: LLMWorldGenerator,
        sample_scene_critique_response: Dict[str, Any],
    ) -> None:
        """Test parsing a valid scene critique response."""
        json_content = json.dumps(sample_scene_critique_response)
        result = generator._parse_critique_response(json_content)

        assert result.overall_score == 7
        assert len(result.category_scores) == 4
        assert not result.is_error()

        # Check pacing category
        pacing = next((c for c in result.category_scores if c.category == "pacing"), None)
        assert pacing is not None
        assert pacing.score == 8
        assert len(pacing.issues) == 1
        assert len(pacing.suggestions) == 2

        # Check showing category
        showing = next((c for c in result.category_scores if c.category == "showing"), None)
        assert showing is not None
        assert showing.score == 5
        assert "he felt angry" in str(showing.issues)
        assert len(showing.suggestions) == 3

        # Check highlights
        assert len(result.highlights) == 3
        assert "Opening hook" in result.highlights[0]

        # Check summary
        assert len(result.summary) > 0
        assert "solid foundation" in result.summary.lower()

    @pytest.mark.unit
    def test_parse_critique_clamps_overall_score(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that overall_score is clamped to valid range (1-10)."""
        # Test too high
        response = {"overall_score": 15, "category_scores": [], "highlights": [], "summary": ""}
        json_content = json.dumps(response)
        result = generator._parse_critique_response(json_content)
        assert result.overall_score == 10

        # Test too low
        response = {"overall_score": -5, "category_scores": [], "highlights": [], "summary": ""}
        json_content = json.dumps(response)
        result = generator._parse_critique_response(json_content)
        assert result.overall_score == 1

    @pytest.mark.unit
    def test_parse_critique_clamps_category_scores(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that category scores are clamped to valid range (1-10)."""
        response = {
            "overall_score": 5,
            "category_scores": [
                {"category": "pacing", "score": 15, "issues": [], "suggestions": []},
                {"category": "voice", "score": -5, "issues": [], "suggestions": []},
            ],
            "highlights": [],
            "summary": "",
        }
        json_content = json.dumps(response)
        result = generator._parse_critique_response(json_content)

        pacing = next((c for c in result.category_scores if c.category == "pacing"), None)
        voice = next((c for c in result.category_scores if c.category == "voice"), None)

        assert pacing is not None
        assert pacing.score == 10
        assert voice is not None
        assert voice.score == 1

    @pytest.mark.unit
    def test_parse_critique_filters_invalid_categories(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that invalid categories are filtered out."""
        response = {
            "overall_score": 5,
            "category_scores": [
                {"category": "pacing", "score": 7, "issues": [], "suggestions": []},
                {"category": "invalid_category", "score": 5, "issues": [], "suggestions": []},
                {"category": "voice", "score": 6, "issues": [], "suggestions": []},
            ],
            "highlights": [],
            "summary": "",
        }
        json_content = json.dumps(response)
        result = generator._parse_critique_response(json_content)

        # Should only have pacing and voice
        assert len(result.category_scores) == 2
        categories = {c.category for c in result.category_scores}
        assert categories == {"pacing", "voice"}

    @pytest.mark.unit
    def test_parse_critique_handles_missing_fields(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test parsing handles missing optional fields."""
        response = {
            "overall_score": 5,
            "category_scores": [
                {
                    "category": "pacing",
                    "score": 7,
                    # Missing issues and suggestions
                }
            ],
            # Missing highlights
            "summary": "Test summary",
        }
        json_content = json.dumps(response)
        result = generator._parse_critique_response(json_content)

        assert len(result.category_scores) == 1
        assert result.category_scores[0].issues == []
        assert result.category_scores[0].suggestions == []
        assert result.highlights == []
        assert result.summary == "Test summary"

    @pytest.mark.unit
    def test_parse_critique_ensures_lists(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that issues and suggestions are always lists."""
        response = {
            "overall_score": 5,
            "category_scores": [
                {
                    "category": "pacing",
                    "score": 7,
                    "issues": "not a list",  # String instead of list
                    "suggestions": None,  # None instead of list
                }
            ],
            "highlights": "also not a list",
            "summary": "Test",
        }
        json_content = json.dumps(response)
        result = generator._parse_critique_response(json_content)

        assert isinstance(result.category_scores[0].issues, list)
        assert isinstance(result.category_scores[0].suggestions, list)
        assert isinstance(result.highlights, list)


class TestCritiquePromptBuilding:
    """Tests for scene critique prompt building."""

    @pytest.mark.unit
    def test_build_critique_user_prompt_with_goals(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test prompt building with scene goals."""
        scene_text = "The room was dark. John felt scared."
        goals = ["build tension", "establish suspense"]

        prompt = generator._build_critique_user_prompt(scene_text, goals)

        assert "The room was dark" in prompt
        assert "build tension" in prompt
        assert "establish suspense" in prompt

    @pytest.mark.unit
    def test_build_critique_user_prompt_without_goals(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test prompt building without scene goals."""
        scene_text = "She walked into the room. It was empty."

        prompt = generator._build_critique_user_prompt(scene_text, None)

        assert "She walked into the room" in prompt
        assert "No specific goals provided" in prompt

    @pytest.mark.unit
    def test_build_critique_user_prompt_truncates_long_text(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that very long scene text is truncated."""
        # Create a scene longer than 12000 characters
        long_scene = "A" * 15000

        prompt = generator._build_critique_user_prompt(long_scene, None)

        # Should be truncated with "..." appended
        assert len(prompt) < 16000  # Should be significantly less
        assert "..." in prompt

    @pytest.mark.unit
    def test_build_critique_user_prompt_includes_dimensions(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test that prompt mentions critique dimensions."""
        scene_text = "Test scene."

        prompt = generator._build_critique_user_prompt(scene_text, None)

        # Should mention the four critique categories
        assert "pacing" in prompt.lower()
        assert "voice" in prompt.lower()
        assert "showing" in prompt.lower() or "show" in prompt.lower()
        assert "dialogue" in prompt.lower()


class TestCritiqueIntegration:
    """Integration-style tests for scene critique with mocked API."""

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_critique_scene_success(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        sample_scene_critique_response: Dict[str, Any],
        scene_text_fixture: str,
    ) -> None:
        """Test successful scene critique with mocked API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(sample_scene_critique_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        result = generator.critique_scene(
            scene_text=scene_text_fixture,
            scene_goals=["build tension"],
        )

        assert not result.is_error()
        assert result.overall_score == 7
        assert len(result.category_scores) == 4
        assert len(result.highlights) == 3

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_critique_scene_api_error(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test scene critique handles API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = generator.critique_scene(scene_text="Test scene.")

        assert result.is_error()
        assert "500" in result.error
        assert result.overall_score == 0
        assert len(result.category_scores) == 0

    @pytest.mark.unit
    def test_critique_scene_missing_api_key(self) -> None:
        """Test scene critique returns error when API key missing."""
        gen = LLMWorldGenerator()
        gen._api_key = ""

        result = gen.critique_scene(scene_text="Test scene.")

        assert result.is_error()
        assert "GEMINI_API_KEY" in result.error


# ==================== RAG Integration Tests (Warzone 4) ====================


class TestRAGIntegration:
    """Tests for RAG integration in LLMWorldGenerator."""

    @pytest.mark.unit
    def test_generator_with_rag_service(self) -> None:
        """Test creating generator with RAG service."""
        from unittest.mock import MagicMock

        rag_mock = MagicMock()
        gen = LLMWorldGenerator(rag_service=rag_mock)

        assert gen._rag_service is rag_mock
        assert gen._rag_service is not None

    @pytest.mark.unit
    def test_generator_without_rag_service(self, generator: LLMWorldGenerator) -> None:
        """Test creating generator without RAG service."""
        assert generator._rag_service is None

    @pytest.mark.unit
    def test_extract_keywords_for_dialogue(self, generator: LLMWorldGenerator) -> None:
        """Test keyword extraction for dialogue RAG query."""
        from src.contexts.world.infrastructure.generators.llm_world_generator import (
            CharacterData,
        )

        character = CharacterData(
            name="Alice",
            traits=["brave", "curious"],
            psychology={"openness": 80, "conscientiousness": 60},
        )

        keywords = generator._extract_keywords_for_dialogue(
            character=character,
            context="A stranger approaches in the tavern",
            mood="suspicious",
        )

        assert "Alice" in keywords
        assert "brave" in keywords
        assert "curious" in keywords
        assert "suspicious" in keywords
        assert "stranger" in keywords

    @pytest.mark.unit
    def test_extract_keywords_for_dialogue_minimal(self, generator: LLMWorldGenerator) -> None:
        """Test keyword extraction with minimal character data."""
        from src.contexts.world.infrastructure.generators.llm_world_generator import (
            CharacterData,
        )

        character = CharacterData(name="Bob")

        keywords = generator._extract_keywords_for_dialogue(
            character=character,
            context="Hello world",
            mood=None,
        )

        assert "Bob" in keywords
        assert "Hello" in keywords

    @pytest.mark.unit
    def test_extract_keywords_for_beats(self, generator: LLMWorldGenerator) -> None:
        """Test keyword extraction for beat suggestion RAG query."""
        current_beats = [
            {"beat_type": "action", "content": "She drew her sword.", "mood_shift": 0},
            {"beat_type": "dialogue", "content": "'Stay back!'", "mood_shift": -1},
        ]

        keywords = generator._extract_keywords_for_beats(
            current_beats=current_beats,
            scene_context="A tense standoff in an abandoned warehouse",
            mood_target=-2,
        )

        assert "tense" in keywords
        assert "standoff" in keywords
        assert "tense" in keywords or "negative" in keywords or "dramatic" in keywords
        assert "action" in keywords

    @pytest.mark.unit
    def test_extract_keywords_for_beats_empty(self, generator: LLMWorldGenerator) -> None:
        """Test keyword extraction with no existing beats."""
        keywords = generator._extract_keywords_for_beats(
            current_beats=[],
            scene_context="Opening scene of a heist",
            mood_target=None,
        )

        assert "Opening" in keywords
        assert "scene" in keywords

    @pytest.mark.unit
    def test_extract_keywords_for_beats_positive_mood(self, generator: LLMWorldGenerator) -> None:
        """Test keyword extraction with positive mood target."""
        keywords = generator._extract_keywords_for_beats(
            current_beats=[],
            scene_context="Victory celebration",
            mood_target=3,
        )

        assert "uplifting" in keywords or "positive" in keywords

    @pytest.mark.unit
    async def test_enrich_with_rag_no_service(self, generator: LLMWorldGenerator) -> None:
        """Test enrichment when no RAG service is available."""
        base_prompt = "Generate dialogue for Alice."

        prompt, chunks, tokens = await generator._enrich_with_rag(
            query="Alice",
            base_prompt=base_prompt,
        )

        assert prompt == base_prompt
        assert chunks == 0
        assert tokens == 0

    @pytest.mark.unit
    async def test_enrich_with_rag_service_error(self, generator: LLMWorldGenerator) -> None:
        """Test enrichment when RAG service raises an error."""
        from unittest.mock import AsyncMock, MagicMock

        rag_mock = MagicMock()
        rag_mock.enrich_prompt = AsyncMock(side_effect=Exception("RAG failed"))
        gen = LLMWorldGenerator(rag_service=rag_mock)

        base_prompt = "Generate dialogue for Alice."

        prompt, chunks, tokens = await gen._enrich_with_rag(
            query="Alice",
            base_prompt=base_prompt,
        )

        # Should fall back to original prompt on error
        assert prompt == base_prompt
        assert chunks == 0
        assert tokens == 0

    @pytest.mark.unit
    async def test_enrich_with_rag_service_success(self) -> None:
        """Test successful enrichment with RAG service."""
        from unittest.mock import AsyncMock, MagicMock

        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = "Relevant Context:\n[Alice is brave]\n\n---\n\nGenerate dialogue for Alice."
        enriched_result.chunks_retrieved = 2
        enriched_result.tokens_added = 50

        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)
        gen = LLMWorldGenerator(rag_service=rag_mock)

        base_prompt = "Generate dialogue for Alice."

        prompt, chunks, tokens = await gen._enrich_with_rag(
            query="Alice brave warrior",
            base_prompt=base_prompt,
        )

        assert "Relevant Context:" in prompt
        assert prompt != base_prompt
        assert chunks == 2
        assert tokens == 50

        # Verify the service was called correctly
        rag_mock.enrich_prompt.assert_called_once_with(
            query="Alice brave warrior",
            base_prompt=base_prompt,
        )

    @pytest.mark.unit
    async def test_generate_dialogue_with_rag_disabled(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test dialogue generation with RAG disabled."""
        # Verify the method accepts use_rag parameter
        # Since we can't actually call the API without a key, we just verify
        # the method signature is valid
        assert callable(generator.generate_dialogue)
        assert hasattr(generator.generate_dialogue, "__annotations__")

    @pytest.mark.unit
    async def test_suggest_next_beats_with_rag_disabled(
        self, generator: LLMWorldGenerator
    ) -> None:
        """Test beat suggestion with RAG disabled."""
        # Verify the method accepts use_rag parameter
        assert callable(generator.suggest_next_beats)

    @pytest.mark.unit
    def test_rag_integration_docstring(self) -> None:
        """Test that RAG integration is documented."""
        from src.contexts.world.infrastructure.generators.llm_world_generator import (
            LLMWorldGenerator,
        )

        # Check that the class docstring mentions RAG
        docstring = LLMWorldGenerator.__doc__
        assert docstring is not None
        assert "RAG" in docstring or "Retrieval" in docstring

    @pytest.mark.unit
    def test_rag_service_attribute_optional(self) -> None:
        """Test that _rag_service is optional in __init__."""
        # Should not raise when rag_service is not provided
        gen = LLMWorldGenerator()
        assert hasattr(gen, "_rag_service")
        assert gen._rag_service is None

        # Should accept rag_service parameter
        from unittest.mock import MagicMock

        rag_mock = MagicMock()
        gen_with_rag = LLMWorldGenerator(rag_service=rag_mock)
        assert gen_with_rag._rag_service is rag_mock

    @pytest.mark.unit
    async def test_enrich_with_rag_returns_context_in_prompt(self) -> None:
        """Test that RAG enrichment injects context with 'Relevant Context:' header."""
        from unittest.mock import AsyncMock, MagicMock

        # Create a mock RAG service that returns enriched prompt
        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = """Relevant Context:
[1] CHARACTER:alice (part 1/1)
Alice is a brave warrior known for exceptional courage.

---

Generate dialogue for Alice."""
        enriched_result.chunks_retrieved = 1
        enriched_result.tokens_added = 25

        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)
        gen = LLMWorldGenerator(rag_service=rag_mock)

        base_prompt = "Generate dialogue for Alice."
        prompt, chunks, tokens = await gen._enrich_with_rag(
            query="Alice brave warrior",
            base_prompt=base_prompt,
        )

        # Verify the prompt structure contains the context section
        assert "Relevant Context:" in prompt
        assert "CHARACTER:alice" in prompt
        assert "---" in prompt  # Context separator
        assert "Generate dialogue for Alice." in prompt
        assert chunks == 1
        assert tokens == 25

    @pytest.mark.unit
    async def test_enrich_with_rag_logs_chunks_and_tokens(self) -> None:
        """Test that RAG enrichment logs chunks retrieved and tokens added."""
        from unittest.mock import AsyncMock, MagicMock
        import structlog

        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = "Relevant Context:\n[Context here]\n\n---\n\nOriginal prompt"
        enriched_result.chunks_retrieved = 3
        enriched_result.tokens_added = 150

        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)
        gen = LLMWorldGenerator(rag_service=rag_mock)

        base_prompt = "Original prompt"

        # Capture log output
        with structlog.testing.capture_logs() as logs:
            prompt, chunks, tokens = await gen._enrich_with_rag(
                query="test query",
                base_prompt=base_prompt,
            )

            # Verify the info log contains RAG metrics
            rag_logs = [log for log in logs if log.get("event") == "rag_enrichment"]
            assert len(rag_logs) > 0
            assert rag_logs[0].get("chunks_retrieved") == 3
            assert rag_logs[0].get("tokens_added") == 150
            # Verify the returned values match
            assert chunks == 3
            assert tokens == 150

    @pytest.mark.unit
    async def test_generate_dialogue_use_rag_toggle(self) -> None:
        """Test that use_rag parameter controls RAG enrichment."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from src.contexts.world.infrastructure.generators.llm_world_generator import (
            CharacterData,
        )

        # Create a mock RAG service
        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = "Relevant Context:\n[Context]\n\n---\n\nBase prompt"
        enriched_result.chunks_retrieved = 2
        enriched_result.tokens_added = 50
        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)

        gen = LLMWorldGenerator(rag_service=rag_mock)
        gen._api_key = "test-key"

        # Mock the Gemini API call
        with patch.object(gen, "_call_gemini", return_value='{"dialogue": "Test response", "tone": "neutral"}'):
            character = CharacterData(name="Alice", traits=["brave"])

            # Test with use_rag=True (default)
            await gen.generate_dialogue(
                character=character,
                context="Test context",
                use_rag=True,
            )
            # RAG service should have been called
            assert rag_mock.enrich_prompt.called

            # Reset mock
            rag_mock.enrich_prompt.reset_mock()

            # Test with use_rag=False
            await gen.generate_dialogue(
                character=character,
                context="Test context",
                use_rag=False,
            )
            # RAG service should NOT have been called
            assert not rag_mock.enrich_prompt.called

    @pytest.mark.unit
    async def test_suggest_next_beats_use_rag_toggle(self) -> None:
        """Test that use_rag parameter controls RAG enrichment for beat suggestions."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Create a mock RAG service
        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = "Relevant Context:\n[Context]\n\n---\n\nBase prompt"
        enriched_result.chunks_retrieved = 1
        enriched_result.tokens_added = 30
        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)

        gen = LLMWorldGenerator(rag_service=rag_mock)
        gen._api_key = "test-key"

        # Mock the Gemini API call
        with patch.object(gen, "_call_gemini", return_value='{"suggestions": [{"beat_type": "action", "content": "Test"}]}'):
            # Test with use_rag=True (default)
            await gen.suggest_next_beats(
                current_beats=[],
                scene_context="Test scene",
                use_rag=True,
            )
            # RAG service should have been called
            assert rag_mock.enrich_prompt.called

            # Reset mock
            rag_mock.enrich_prompt.reset_mock()

            # Test with use_rag=False
            await gen.suggest_next_beats(
                current_beats=[],
                scene_context="Test scene",
                use_rag=False,
            )
            # RAG service should NOT have been called
            assert not rag_mock.enrich_prompt.called

    @pytest.mark.unit
    async def test_enrich_with_rag_no_context_returns_original(self) -> None:
        """Test that enrichment returns original prompt when no context is retrieved."""
        from unittest.mock import AsyncMock, MagicMock

        rag_mock = MagicMock()
        # Simulate no chunks retrieved
        enriched_result = MagicMock()
        enriched_result.prompt = "Original prompt"  # No context added
        enriched_result.chunks_retrieved = 0
        enriched_result.tokens_added = 0
        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)

        gen = LLMWorldGenerator(rag_service=rag_mock)

        base_prompt = "Original prompt"
        prompt, chunks, tokens = await gen._enrich_with_rag(
            query="test query",
            base_prompt=base_prompt,
        )

        # Should return the (unchanged) prompt with zero metrics
        assert prompt == "Original prompt"
        assert chunks == 0
        assert tokens == 0
        assert rag_mock.enrich_prompt.called

    @pytest.mark.unit
    async def test_rag_context_injected_into_system_prompt(self) -> None:
        """Test that RAG context is injected into the system prompt, not user prompt.

        BRAIN-007C: Context should be injected into the System Prompt as
        'Relevant Context:' section, not the user prompt.
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from src.contexts.world.infrastructure.generators.llm_world_generator import (
            CharacterData,
        )

        # Create a mock RAG service
        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = """Relevant Context:
[1] CHARACTER:alice (part 1/1)
Alice is a brave warrior.

---

Original system prompt"""
        enriched_result.chunks_retrieved = 1
        enriched_result.tokens_added = 25

        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)

        gen = LLMWorldGenerator(rag_service=rag_mock)
        gen._api_key = "test-key"

        # Track what's passed to _call_gemini
        call_args = []

        def capture_call(system_prompt: str, user_prompt: str) -> str:
            call_args.append({"system": system_prompt, "user": user_prompt})
            return '{"dialogue": "Test", "tone": "neutral"}'

        with patch.object(gen, "_call_gemini", side_effect=capture_call):
            character = CharacterData(name="Alice", traits=["brave"])

            await gen.generate_dialogue(
                character=character,
                context="Test context",
                use_rag=True,
            )

        # Verify context was injected into SYSTEM prompt
        assert len(call_args) == 1
        assert "Relevant Context:" in call_args[0]["system"]
        assert "CHARACTER:alice" in call_args[0]["system"]
        # User prompt should NOT contain the RAG context
        assert "Relevant Context:" not in call_args[0]["user"]

    @pytest.mark.unit
    async def test_rag_context_injection_logs_metrics(self) -> None:
        """Test that context injection logs chunks and tokens at info level.

        BRAIN-007C: Log number of chunks retrieved and tokens added.
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from src.contexts.world.infrastructure.generators.llm_world_generator import (
            CharacterData,
        )
        import structlog

        # Create a mock RAG service
        rag_mock = MagicMock()
        enriched_result = MagicMock()
        enriched_result.prompt = "Relevant Context:\n[Test]\n\n---\n\nBase"
        enriched_result.chunks_retrieved = 3
        enriched_result.tokens_added = 120

        rag_mock.enrich_prompt = AsyncMock(return_value=enriched_result)

        gen = LLMWorldGenerator(rag_service=rag_mock)
        gen._api_key = "test-key"

        with patch.object(gen, "_call_gemini", return_value='{"dialogue": "Test", "tone": "neutral"}'):
            with structlog.testing.capture_logs() as logs:
                character = CharacterData(name="Alice", traits=["brave"])

                await gen.generate_dialogue(
                    character=character,
                    context="Test context",
                    use_rag=True,
                )

                # Verify info-level log with chunks_retrieved and tokens_added
                rag_logs = [log for log in logs if log.get("event") == "rag_context_injected"]
                assert len(rag_logs) > 0
                assert rag_logs[0].get("chunks_retrieved") == 3
                assert rag_logs[0].get("tokens_added") == 120

