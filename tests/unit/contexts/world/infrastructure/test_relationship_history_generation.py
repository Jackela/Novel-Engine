"""Unit tests for relationship history generation in LLMWorldGenerator."""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.infrastructure.generators.llm_world_generator import (
    CharacterData,
    LLMWorldGenerator,
    RelationshipHistoryResult,
)


@pytest.fixture
def sample_history_response() -> Dict[str, Any]:
    """Sample LLM response for relationship history generation."""
    return {
        "backstory": (
            "Marcus and Elena first crossed paths during the Siege of Blackmoor, "
            "where Marcus served as a scout and Elena commanded the eastern garrison. "
            "Their initial meetings were tense, filled with arguments over strategy. "
            "However, when Elena's company was ambushed, Marcus risked his life to warn them, "
            "earning her grudging respect.\n\n"
            "Over the following months, their professional respect evolved into genuine friendship. "
            "Marcus's cautious nature balanced Elena's impulsiveness, and she learned to trust "
            "his judgment even when she disagreed. A near-death experience during the final battle "
            "cemented their bond - Elena would later say Marcus was the only person she'd trust "
            "to watch her back."
        ),
        "first_meeting": (
            "During the war council before the Siege of Blackmoor, where they argued "
            "fiercely about defensive positions."
        ),
        "defining_moment": (
            "Marcus risked capture to warn Elena's garrison of an ambush, "
            "saving dozens of lives including hers."
        ),
        "current_status": (
            "Close allies who trust each other implicitly, though Marcus still worries "
            "about her impulsive tendencies."
        ),
    }


@pytest.fixture
def generator() -> LLMWorldGenerator:
    """Create a generator instance for testing."""
    return LLMWorldGenerator()


@pytest.fixture
def character_a() -> CharacterData:
    """Create first sample character for testing."""
    return CharacterData(
        name="Marcus",
        psychology={
            "openness": 45,
            "conscientiousness": 75,
            "extraversion": 30,
            "agreeableness": 40,
            "neuroticism": 65,
        },
        traits=["skeptical", "observant", "cautious"],
    )


@pytest.fixture
def character_b() -> CharacterData:
    """Create second sample character for testing."""
    return CharacterData(
        name="Elena",
        psychology={
            "openness": 80,
            "conscientiousness": 50,
            "extraversion": 70,
            "agreeableness": 60,
            "neuroticism": 35,
        },
        traits=["brave", "impulsive", "charismatic"],
    )


class TestRelationshipHistoryResult:
    """Tests for RelationshipHistoryResult dataclass."""

    @pytest.mark.unit
    def test_create_minimal(self) -> None:
        """Test creating RelationshipHistoryResult with minimal fields."""
        result = RelationshipHistoryResult(backstory="They were childhood friends.")
        assert result.backstory == "They were childhood friends."
        assert result.first_meeting is None
        assert result.defining_moment is None
        assert result.current_status is None
        assert result.error is None
        assert not result.is_error()

    @pytest.mark.unit
    def test_create_full(self, sample_history_response: Dict[str, Any]) -> None:
        """Test creating RelationshipHistoryResult with all fields."""
        result = RelationshipHistoryResult(
            backstory=sample_history_response["backstory"],
            first_meeting=sample_history_response["first_meeting"],
            defining_moment=sample_history_response["defining_moment"],
            current_status=sample_history_response["current_status"],
        )
        assert "Marcus and Elena" in result.backstory
        assert "war council" in result.first_meeting
        assert "ambush" in result.defining_moment
        assert "trust each other implicitly" in result.current_status
        assert not result.is_error()

    @pytest.mark.unit
    def test_error_result(self) -> None:
        """Test creating an error RelationshipHistoryResult."""
        result = RelationshipHistoryResult(
            backstory="Unable to generate relationship history.",
            error="API connection failed",
        )
        assert result.is_error()
        assert result.error == "API connection failed"

    @pytest.mark.unit
    def test_to_dict_minimal(self) -> None:
        """Test to_dict with minimal fields."""
        result = RelationshipHistoryResult(backstory="Simple backstory.")
        d = result.to_dict()

        assert d["backstory"] == "Simple backstory."
        assert "first_meeting" not in d
        assert "defining_moment" not in d
        assert "current_status" not in d
        assert "error" not in d

    @pytest.mark.unit
    def test_to_dict_full(self, sample_history_response: Dict[str, Any]) -> None:
        """Test to_dict with all fields."""
        result = RelationshipHistoryResult(
            backstory=sample_history_response["backstory"],
            first_meeting=sample_history_response["first_meeting"],
            defining_moment=sample_history_response["defining_moment"],
            current_status=sample_history_response["current_status"],
        )
        d = result.to_dict()

        assert d["backstory"] == sample_history_response["backstory"]
        assert d["first_meeting"] == sample_history_response["first_meeting"]
        assert d["defining_moment"] == sample_history_response["defining_moment"]
        assert d["current_status"] == sample_history_response["current_status"]
        assert "error" not in d

    @pytest.mark.unit
    def test_to_dict_with_error(self) -> None:
        """Test to_dict includes error when present."""
        result = RelationshipHistoryResult(
            backstory="Unable to generate.",
            error="Generation failed",
        )
        d = result.to_dict()

        assert d["error"] == "Generation failed"


class TestRelationshipHistoryPromptBuilding:
    """Tests for relationship history prompt building."""

    @pytest.mark.unit
    def test_build_prompt_includes_both_characters(
        self,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that prompt includes information about both characters."""
        prompt = generator._build_relationship_history_user_prompt(
            character_a=character_a,
            character_b=character_b,
            trust=75,
            romance=0,
        )

        # Both character names should be present
        assert "Marcus" in prompt
        assert "Elena" in prompt

    @pytest.mark.unit
    def test_build_prompt_includes_psychology(
        self,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that prompt includes psychology for both characters."""
        prompt = generator._build_relationship_history_user_prompt(
            character_a=character_a,
            character_b=character_b,
            trust=50,
            romance=50,
        )

        # Character A's psychology
        assert "Openness: 45" in prompt
        assert "Conscientiousness: 75" in prompt
        assert "Neuroticism: 65" in prompt

        # Character B's psychology
        assert "Openness: 80" in prompt
        assert "Extraversion: 70" in prompt
        assert "Neuroticism: 35" in prompt

    @pytest.mark.unit
    def test_build_prompt_includes_traits(
        self,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that prompt includes traits for both characters."""
        prompt = generator._build_relationship_history_user_prompt(
            character_a=character_a,
            character_b=character_b,
            trust=50,
            romance=0,
        )

        # Character A's traits
        assert "skeptical" in prompt
        assert "cautious" in prompt

        # Character B's traits
        assert "brave" in prompt
        assert "impulsive" in prompt

    @pytest.mark.unit
    def test_build_prompt_includes_relationship_metrics(
        self,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that prompt includes trust and romance levels."""
        prompt = generator._build_relationship_history_user_prompt(
            character_a=character_a,
            character_b=character_b,
            trust=85,
            romance=60,
        )

        assert "Trust Level: 85/100" in prompt
        assert "Romance Level: 60/100" in prompt

    @pytest.mark.unit
    def test_build_prompt_minimal_characters(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test building prompt with minimal character data."""
        char_a = CharacterData(name="Person A")
        char_b = CharacterData(name="Person B")

        prompt = generator._build_relationship_history_user_prompt(
            character_a=char_a,
            character_b=char_b,
            trust=50,
            romance=0,
        )

        assert "Person A" in prompt
        assert "Person B" in prompt
        assert "Not specified" in prompt  # Psychology placeholder
        assert "None specified" in prompt  # Traits placeholder

    @pytest.mark.unit
    def test_build_prompt_low_trust(
        self,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that low trust is clearly indicated in prompt."""
        prompt = generator._build_relationship_history_user_prompt(
            character_a=character_a,
            character_b=character_b,
            trust=15,
            romance=0,
        )

        assert "Trust Level: 15/100" in prompt

    @pytest.mark.unit
    def test_build_prompt_high_romance(
        self,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that high romance is clearly indicated in prompt."""
        prompt = generator._build_relationship_history_user_prompt(
            character_a=character_a,
            character_b=character_b,
            trust=75,
            romance=90,
        )

        assert "Romance Level: 90/100" in prompt


class TestRelationshipHistoryResponseParsing:
    """Tests for relationship history response parsing."""

    @pytest.mark.unit
    def test_parse_response_full(
        self,
        generator: LLMWorldGenerator,
        sample_history_response: Dict[str, Any],
    ) -> None:
        """Test parsing a complete relationship history response."""
        content = json.dumps(sample_history_response)
        result = generator._parse_relationship_history_response(content)

        assert "Marcus and Elena" in result.backstory
        assert "war council" in result.first_meeting
        assert "ambush" in result.defining_moment
        assert "trust each other implicitly" in result.current_status

    @pytest.mark.unit
    def test_parse_response_minimal(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test parsing a minimal response."""
        content = json.dumps({"backstory": "They were old rivals."})
        result = generator._parse_relationship_history_response(content)

        assert result.backstory == "They were old rivals."
        assert result.first_meeting is None
        assert result.defining_moment is None
        assert result.current_status is None

    @pytest.mark.unit
    def test_parse_response_missing_backstory_uses_default(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test parsing response with missing backstory uses default."""
        content = json.dumps({
            "first_meeting": "At a tavern",
            "defining_moment": "They fought together",
        })
        result = generator._parse_relationship_history_response(content)

        assert result.backstory == "Unable to generate backstory."


class TestRelationshipHistoryGeneration:
    """Integration-style tests for relationship history generation with mocked API."""

    @pytest.mark.unit
    @patch(
        "src.contexts.world.infrastructure.generators.llm_world_generator.requests.post"
    )
    def test_generate_history_success(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
        sample_history_response: Dict[str, Any],
    ) -> None:
        """Test successful relationship history generation with mocked API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(sample_history_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = generator.generate_relationship_history(
                character_a=character_a,
                character_b=character_b,
                trust=85,
                romance=0,
            )

        assert not result.is_error()
        assert "Marcus and Elena" in result.backstory
        assert result.first_meeting is not None
        assert result.defining_moment is not None
        assert result.current_status is not None

    @pytest.mark.unit
    @patch(
        "src.contexts.world.infrastructure.generators.llm_world_generator.requests.post"
    )
    def test_generate_history_api_error_returns_error_result(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that API errors return an error result."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = generator.generate_relationship_history(
                character_a=character_a,
                character_b=character_b,
                trust=50,
                romance=0,
            )

        assert result.is_error()
        assert "500" in result.error

    @pytest.mark.unit
    def test_generate_history_missing_api_key_returns_error(
        self,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test that missing API key returns error result."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            gen = LLMWorldGenerator()
            gen._api_key = ""  # Explicitly set to empty
            result = gen.generate_relationship_history(
                character_a=character_a,
                character_b=character_b,
                trust=50,
                romance=0,
            )

        assert result.is_error()
        assert "GEMINI_API_KEY" in result.error

    @pytest.mark.unit
    @patch(
        "src.contexts.world.infrastructure.generators.llm_world_generator.requests.post"
    )
    def test_generate_history_with_high_romance(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test generating history for a romantic relationship."""
        romantic_response = {
            "backstory": (
                "Their eyes met across the crowded ballroom, and both felt "
                "an immediate connection that defied explanation..."
            ),
            "first_meeting": "At the Duke's annual ball",
            "defining_moment": "The first kiss under the moonlit garden",
            "current_status": "Deeply in love, planning their future together",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(romantic_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = generator.generate_relationship_history(
                character_a=character_a,
                character_b=character_b,
                trust=80,
                romance=95,
            )

        assert not result.is_error()
        assert "ballroom" in result.backstory or "connection" in result.backstory

    @pytest.mark.unit
    @patch(
        "src.contexts.world.infrastructure.generators.llm_world_generator.requests.post"
    )
    def test_generate_history_with_low_trust(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        character_a: CharacterData,
        character_b: CharacterData,
    ) -> None:
        """Test generating history for a distrustful relationship."""
        hostile_response = {
            "backstory": (
                "Their feud began when Marcus accused Elena of stealing his "
                "family's heirloom. The accusation was never proven, but the "
                "damage was done..."
            ),
            "first_meeting": "At a merchant's guild meeting",
            "defining_moment": "The public accusation that ruined Elena's reputation",
            "current_status": "Bitter enemies who avoid each other when possible",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(hostile_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = generator.generate_relationship_history(
                character_a=character_a,
                character_b=character_b,
                trust=10,
                romance=0,
            )

        assert not result.is_error()
        assert "feud" in result.backstory or "accused" in result.backstory


class TestRelationshipHistoryPromptFile:
    """Tests for relationship history prompt file loading."""

    @pytest.mark.unit
    def test_load_prompt_exists(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that relationship history prompt file exists and loads."""
        prompt = generator._load_relationship_history_prompt()

        # Should contain key instructions
        assert "relationship" in prompt.lower()
        assert "backstory" in prompt.lower()
        assert "json" in prompt.lower()

    @pytest.mark.unit
    def test_load_prompt_contains_trust_guidance(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that prompt contains trust level guidance."""
        prompt = generator._load_relationship_history_prompt()

        assert "trust" in prompt.lower()
        # Should explain what different trust levels mean
        assert "distrust" in prompt.lower() or "betrayal" in prompt.lower()

    @pytest.mark.unit
    def test_load_prompt_contains_romance_guidance(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that prompt contains romance level guidance."""
        prompt = generator._load_relationship_history_prompt()

        assert "romance" in prompt.lower()
        # Should explain what different romance levels mean
        assert "love" in prompt.lower() or "romantic" in prompt.lower()
