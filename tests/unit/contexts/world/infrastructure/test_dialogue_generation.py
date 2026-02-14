"""Unit tests for dialogue generation in LLMWorldGenerator."""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.infrastructure.generators.llm_world_generator import (
    CharacterData,
    DialogueResult,
    LLMWorldGenerator,
)


@pytest.fixture
def sample_dialogue_response() -> Dict[str, Any]:
    """Sample LLM response for dialogue generation."""
    return {
        "dialogue": "I've seen deals like this before. What's the catch?",
        "internal_thought": "This is too good to be true. Stay alert.",
        "tone": "suspicious",
        "body_language": "narrows eyes, crosses arms",
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


@pytest.fixture
def sample_character() -> CharacterData:
    """Create a sample character for testing."""
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
        speaking_style="Terse, measured speech with occasional dry humor",
    )


class TestCharacterData:
    """Tests for CharacterData dataclass."""

    @pytest.mark.unit
    def test_create_minimal(self) -> None:
        """Test creating CharacterData with minimal fields."""
        char = CharacterData(name="Test Character")
        assert char.name == "Test Character"
        assert char.psychology is None
        assert char.traits is None
        assert char.speaking_style is None

    @pytest.mark.unit
    def test_create_full(self, sample_character: CharacterData) -> None:
        """Test creating CharacterData with all fields."""
        assert sample_character.name == "Marcus"
        assert sample_character.psychology is not None
        assert sample_character.psychology["openness"] == 45
        assert sample_character.psychology["neuroticism"] == 65
        assert "skeptical" in sample_character.traits
        assert "measured speech" in sample_character.speaking_style

    @pytest.mark.unit
    def test_from_character_aggregate_with_psychology(self) -> None:
        """Test creating CharacterData from a mock Character aggregate."""
        # Create a mock character aggregate
        mock_character = MagicMock()
        mock_character.profile.name = "Elena"
        mock_character.profile.traits = ["brave", "impulsive"]
        mock_character.psychology.to_dict.return_value = {
            "openness": 80,
            "conscientiousness": 50,
            "extraversion": 70,
            "agreeableness": 60,
            "neuroticism": 35,
        }

        char_data = CharacterData.from_character_aggregate(mock_character)

        assert char_data.name == "Elena"
        assert char_data.psychology is not None
        assert char_data.psychology["openness"] == 80
        assert char_data.traits == ["brave", "impulsive"]

    @pytest.mark.unit
    def test_from_character_aggregate_without_psychology(self) -> None:
        """Test creating CharacterData when psychology is None."""
        mock_character = MagicMock()
        mock_character.profile.name = "NoTraits"
        mock_character.profile.traits = None
        mock_character.psychology = None

        # Set up personality_traits fallback
        mock_character.profile.personality_traits.quirks = ["nervous laugh"]

        char_data = CharacterData.from_character_aggregate(mock_character)

        assert char_data.name == "NoTraits"
        assert char_data.psychology is None
        assert char_data.traits == ["nervous laugh"]


class TestDialogueResult:
    """Tests for DialogueResult dataclass."""

    @pytest.mark.unit
    def test_create_minimal(self) -> None:
        """Test creating DialogueResult with minimal fields."""
        result = DialogueResult(dialogue="Hello there.", tone="friendly")
        assert result.dialogue == "Hello there."
        assert result.tone == "friendly"
        assert result.internal_thought is None
        assert result.body_language is None
        assert result.error is None
        assert not result.is_error()

    @pytest.mark.unit
    def test_create_full(self) -> None:
        """Test creating DialogueResult with all fields."""
        result = DialogueResult(
            dialogue="I don't trust you.",
            tone="hostile",
            internal_thought="Keep your guard up.",
            body_language="steps back, hand on sword",
        )
        assert result.dialogue == "I don't trust you."
        assert result.tone == "hostile"
        assert result.internal_thought == "Keep your guard up."
        assert result.body_language == "steps back, hand on sword"
        assert not result.is_error()

    @pytest.mark.unit
    def test_error_result(self) -> None:
        """Test creating an error DialogueResult."""
        result = DialogueResult(
            dialogue="...",
            tone="uncertain",
            error="API connection failed",
        )
        assert result.is_error()
        assert result.error == "API connection failed"

    @pytest.mark.unit
    def test_to_dict_minimal(self) -> None:
        """Test to_dict with minimal fields."""
        result = DialogueResult(dialogue="Yes.", tone="curt")
        d = result.to_dict()

        assert d["dialogue"] == "Yes."
        assert d["tone"] == "curt"
        assert "internal_thought" not in d
        assert "body_language" not in d
        assert "error" not in d

    @pytest.mark.unit
    def test_to_dict_full(self) -> None:
        """Test to_dict with all fields."""
        result = DialogueResult(
            dialogue="Fascinating!",
            tone="excited",
            internal_thought="This changes everything.",
            body_language="leans forward eagerly",
            error=None,
        )
        d = result.to_dict()

        assert d["dialogue"] == "Fascinating!"
        assert d["tone"] == "excited"
        assert d["internal_thought"] == "This changes everything."
        assert d["body_language"] == "leans forward eagerly"
        assert "error" not in d

    @pytest.mark.unit
    def test_to_dict_with_error(self) -> None:
        """Test to_dict includes error when present."""
        result = DialogueResult(
            dialogue="...",
            tone="uncertain",
            error="Generation failed",
        )
        d = result.to_dict()

        assert d["error"] == "Generation failed"


class TestDialoguePromptBuilding:
    """Tests for dialogue prompt building."""

    @pytest.mark.unit
    def test_build_dialogue_user_prompt_full(
        self,
        generator: LLMWorldGenerator,
        sample_character: CharacterData,
    ) -> None:
        """Test building user prompt with full character data."""
        prompt = generator._build_dialogue_user_prompt(
            character=sample_character,
            context="A merchant offers a suspiciously good deal",
            mood="wary",
        )

        # Check character name included
        assert "Marcus" in prompt

        # Check psychology values included
        assert "Openness: 45/100" in prompt
        assert "Conscientiousness: 75/100" in prompt
        assert "Extraversion: 30/100" in prompt
        assert "Neuroticism: 65/100" in prompt

        # Check traits included
        assert "skeptical" in prompt.lower()
        assert "observant" in prompt.lower()

        # Check speaking style included
        assert "measured speech" in prompt.lower()

        # Check mood included
        assert "wary" in prompt.lower()

        # Check context included
        assert "merchant" in prompt.lower()
        assert "suspiciously good deal" in prompt.lower()

    @pytest.mark.unit
    def test_build_dialogue_user_prompt_minimal(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test building user prompt with minimal character data."""
        minimal_char = CharacterData(name="Unknown Stranger")
        prompt = generator._build_dialogue_user_prompt(
            character=minimal_char,
            context="Greeting",
            mood=None,
        )

        assert "Unknown Stranger" in prompt
        assert "Not specified" in prompt  # Psychology placeholder
        assert "None specified" in prompt  # Traits placeholder
        assert "Neutral" in prompt  # Default mood


class TestDialogueResponseParsing:
    """Tests for dialogue response parsing."""

    @pytest.mark.unit
    def test_parse_dialogue_response_full(
        self,
        generator: LLMWorldGenerator,
        sample_dialogue_response: Dict[str, Any],
    ) -> None:
        """Test parsing a complete dialogue response."""
        content = json.dumps(sample_dialogue_response)
        result = generator._parse_dialogue_response(content)

        assert result.dialogue == "I've seen deals like this before. What's the catch?"
        assert result.internal_thought == "This is too good to be true. Stay alert."
        assert result.tone == "suspicious"
        assert result.body_language == "narrows eyes, crosses arms"

    @pytest.mark.unit
    def test_parse_dialogue_response_minimal(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test parsing a minimal dialogue response."""
        content = json.dumps({"dialogue": "Fine.", "tone": "dismissive"})
        result = generator._parse_dialogue_response(content)

        assert result.dialogue == "Fine."
        assert result.tone == "dismissive"
        assert result.internal_thought is None
        assert result.body_language is None

    @pytest.mark.unit
    def test_parse_dialogue_response_missing_fields(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test parsing response with missing fields uses defaults."""
        content = json.dumps({})
        result = generator._parse_dialogue_response(content)

        assert result.dialogue == "..."  # Default
        assert result.tone == "neutral"  # Default


class TestDialogueGeneration:
    """Integration-style tests for dialogue generation with mocked API."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "src.contexts.world.infrastructure.generators.llm_world_generator.requests.post"
    )
    async def test_generate_dialogue_success(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        sample_character: CharacterData,
        sample_dialogue_response: Dict[str, Any],
    ) -> None:
        """Test successful dialogue generation with mocked API."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(sample_dialogue_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        # Set API key for test
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = await generator.generate_dialogue(
                character=sample_character,
                context="A shady merchant offers a deal",
                mood="suspicious",
            )

        assert not result.is_error()
        assert "catch" in result.dialogue.lower()
        assert result.tone == "suspicious"
        assert result.internal_thought is not None
        assert result.body_language is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "src.contexts.world.infrastructure.generators.llm_world_generator.requests.post"
    )
    async def test_generate_dialogue_api_error_returns_error_result(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        sample_character: CharacterData,
    ) -> None:
        """Test that API errors return an error result."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = await generator.generate_dialogue(
                character=sample_character,
                context="Test context",
            )

        assert result.is_error()
        assert result.dialogue == "..."
        assert "500" in result.error

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_dialogue_missing_api_key_returns_error(
        self,
        sample_character: CharacterData,
    ) -> None:
        """Test that missing API key returns error result."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            gen = LLMWorldGenerator()
            gen._api_key = ""  # Explicitly set to empty
            result = await gen.generate_dialogue(
                character=sample_character,
                context="Test context",
            )

        assert result.is_error()
        assert "GEMINI_API_KEY" in result.error


class TestDialoguePromptFile:
    """Tests for dialogue prompt file loading."""

    @pytest.mark.unit
    def test_load_dialogue_prompt_exists(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that dialogue prompt file exists and loads."""
        prompt = generator._load_dialogue_prompt()

        # Should contain key instructions
        assert "dialogue" in prompt.lower()
        assert "psychology" in prompt.lower()
        assert "big five" in prompt.lower()
        assert "json" in prompt.lower()

    @pytest.mark.unit
    def test_load_dialogue_prompt_contains_guidelines(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that dialogue prompt contains necessary guidelines."""
        prompt = generator._load_dialogue_prompt()

        # Should mention trait behaviors
        assert "openness" in prompt.lower()
        assert "conscientiousness" in prompt.lower()
        assert "extraversion" in prompt.lower()
        assert "agreeableness" in prompt.lower()
        assert "neuroticism" in prompt.lower()


class TestPsychologyInfluenceOnPrompt:
    """Tests verifying psychology traits influence prompt construction."""

    @pytest.mark.unit
    def test_high_extraversion_character(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that high extraversion is clearly indicated in prompt."""
        extrovert = CharacterData(
            name="Chatty Charlie",
            psychology={
                "openness": 50,
                "conscientiousness": 50,
                "extraversion": 95,
                "agreeableness": 50,
                "neuroticism": 50,
            },
        )
        prompt = generator._build_dialogue_user_prompt(
            character=extrovert,
            context="Meeting someone new",
            mood=None,
        )

        assert "Extraversion: 95/100" in prompt

    @pytest.mark.unit
    def test_high_neuroticism_character(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that high neuroticism is clearly indicated in prompt."""
        anxious = CharacterData(
            name="Worried Wendy",
            psychology={
                "openness": 50,
                "conscientiousness": 50,
                "extraversion": 50,
                "agreeableness": 50,
                "neuroticism": 90,
            },
        )
        prompt = generator._build_dialogue_user_prompt(
            character=anxious,
            context="Facing uncertainty",
            mood="anxious",
        )

        assert "Neuroticism: 90/100" in prompt
        assert "anxious" in prompt.lower()

    @pytest.mark.unit
    def test_low_agreeableness_character(
        self,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that low agreeableness is clearly indicated in prompt."""
        disagreeable = CharacterData(
            name="Grumpy Greg",
            psychology={
                "openness": 50,
                "conscientiousness": 50,
                "extraversion": 50,
                "agreeableness": 15,
                "neuroticism": 50,
            },
            traits=["blunt", "argumentative"],
        )
        prompt = generator._build_dialogue_user_prompt(
            character=disagreeable,
            context="Being asked for help",
            mood=None,
        )

        assert "Agreeableness: 15/100" in prompt
        assert "blunt" in prompt.lower()
        assert "argumentative" in prompt.lower()
