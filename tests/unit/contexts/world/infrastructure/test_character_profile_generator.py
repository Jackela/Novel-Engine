"""Unit tests for CharacterProfileGenerator.

Tests cover the character profile generation service including:
- Mock generator for deterministic testing
- LLM generator JSON parsing and response handling
- Factory class environment-based selection
- Error handling and fallback behavior
"""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.infrastructure.generators.character_profile_generator import (
    CharacterProfileGenerator,
    CharacterProfileInput,
    CharacterProfileResult,
    LLMCharacterProfileGenerator,
    MockCharacterProfileGenerator,
    generate_character_profile,
)


@pytest.fixture
def sample_llm_response() -> Dict[str, Any]:
    """Sample LLM response for testing."""
    return {
        "name": "Kira Darkwood",
        "aliases": ["Shadow Blade", "The Whisper", "Night's Edge"],
        "archetype": "Rogue",
        "traits": ["cunning", "agile", "secretive", "loyal"],
        "appearance": (
            "Lithe figure wrapped in dark leather. Eyes like polished obsidian "
            "that miss nothing. A faint scar traces her left cheekbone."
        ),
        "backstory": (
            "Raised in the Undercity's thieves' guild after her family was "
            "destroyed by corrupt nobles. Now walks the line between shadow and light."
        ),
        "motivations": ["protect the innocent", "expose corruption", "find her sister"],
        "quirks": ["collects small trinkets", "never sleeps with her back to a door"],
    }


@pytest.fixture
def llm_generator() -> LLMCharacterProfileGenerator:
    """Create an LLM generator instance for testing."""
    return LLMCharacterProfileGenerator()


@pytest.fixture
def mock_generator() -> MockCharacterProfileGenerator:
    """Create a mock generator instance for testing."""
    return MockCharacterProfileGenerator()


class TestCharacterProfileInput:
    """Tests for CharacterProfileInput dataclass."""

    @pytest.mark.unit
    def test_basic_creation(self) -> None:
        """Test creating input with required fields."""
        input_data = CharacterProfileInput(
            name="Test Character",
            archetype="Hero",
        )
        assert input_data.name == "Test Character"
        assert input_data.archetype == "Hero"
        assert input_data.context == ""

    @pytest.mark.unit
    def test_with_context(self) -> None:
        """Test creating input with context."""
        input_data = CharacterProfileInput(
            name="Test Character",
            archetype="Villain",
            context="A dark fantasy world",
        )
        assert input_data.context == "A dark fantasy world"


class TestCharacterProfileResult:
    """Tests for CharacterProfileResult dataclass."""

    @pytest.mark.unit
    def test_basic_creation(self) -> None:
        """Test creating result with all fields."""
        result = CharacterProfileResult(
            name="Test",
            aliases=["Alias1", "Alias2"],
            archetype="Hero",
            traits=["brave", "kind"],
            appearance="Tall and strong",
            backstory="A mysterious past",
            motivations=["justice"],
            quirks=["always early"],
        )
        assert result.name == "Test"
        assert len(result.aliases) == 2
        assert len(result.traits) == 2

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = CharacterProfileResult(
            name="Test",
            aliases=["A1"],
            archetype="Mentor",
            traits=["wise"],
            appearance="Old and weathered",
            backstory="Long history",
            motivations=["teach"],
            quirks=["speaks slowly"],
        )
        data = result.to_dict()

        assert data["name"] == "Test"
        assert data["archetype"] == "Mentor"
        assert "wise" in data["traits"]
        assert isinstance(data["aliases"], list)


class TestMockCharacterProfileGenerator:
    """Tests for MockCharacterProfileGenerator."""

    @pytest.mark.unit
    def test_generate_hero_profile(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test generating a hero archetype profile."""
        result = mock_generator.generate_character_profile(
            name="Marcus Lightbringer",
            archetype="Hero",
            context="A realm of light and shadow",
        )

        assert result.name == "Marcus Lightbringer"
        assert result.archetype == "Hero"
        assert "courageous" in result.traits
        assert "selfless" in result.traits
        assert len(result.aliases) >= 2
        assert len(result.appearance) > 0

    @pytest.mark.unit
    def test_generate_villain_profile(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test generating a villain archetype profile."""
        result = mock_generator.generate_character_profile(
            name="Lord Malachar",
            archetype="Villain",
        )

        assert result.name == "Lord Malachar"
        assert result.archetype == "Villain"
        assert "ruthless" in result.traits
        assert "calculating" in result.traits

    @pytest.mark.unit
    def test_generate_mentor_profile(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test generating a mentor archetype profile."""
        result = mock_generator.generate_character_profile(
            name="Elder Sage",
            archetype="Mentor",
        )

        assert result.archetype == "Mentor"
        assert "wise" in result.traits
        assert "patient" in result.traits

    @pytest.mark.unit
    def test_generate_rogue_profile(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test generating a rogue archetype profile."""
        result = mock_generator.generate_character_profile(
            name="Shadow Dancer",
            archetype="Rogue",
        )

        assert result.archetype == "Rogue"
        assert "cunning" in result.traits

    @pytest.mark.unit
    def test_generate_warrior_profile(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test generating a warrior archetype profile."""
        result = mock_generator.generate_character_profile(
            name="Ironside",
            archetype="Warrior",
        )

        assert result.archetype == "Warrior"
        assert "brave" in result.traits
        assert "loyal" in result.traits

    @pytest.mark.unit
    def test_unknown_archetype_fallback(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test that unknown archetypes get default template."""
        result = mock_generator.generate_character_profile(
            name="Mystery Person",
            archetype="UnknownType",
        )

        assert result.name == "Mystery Person"
        assert result.archetype == "UnknownType"
        assert "enigmatic" in result.traits

    @pytest.mark.unit
    def test_case_insensitive_archetype(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test that archetype matching is case-insensitive."""
        result1 = mock_generator.generate_character_profile("Test", "HERO")
        result2 = mock_generator.generate_character_profile("Test", "hero")
        result3 = mock_generator.generate_character_profile("Test", "Hero")

        assert result1.traits == result2.traits == result3.traits


class TestLLMCharacterProfileGeneratorParsing:
    """Tests for LLMCharacterProfileGenerator JSON parsing."""

    @pytest.mark.unit
    def test_extract_json_direct(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test direct JSON extraction."""
        content = '{"name": "Test", "aliases": [], "archetype": "Hero"}'
        result = llm_generator._extract_json(content)
        assert result["name"] == "Test"

    @pytest.mark.unit
    def test_extract_json_from_markdown(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test JSON extraction from markdown code block."""
        content = """Here is the profile:
```json
{"name": "Markdown Test", "archetype": "Rogue"}
```
That's it!"""
        result = llm_generator._extract_json(content)
        assert result["name"] == "Markdown Test"

    @pytest.mark.unit
    def test_extract_json_with_surrounding_text(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test JSON extraction with surrounding text."""
        content = 'Here is the result: {"name": "Embedded", "archetype": "Mentor"} end'
        result = llm_generator._extract_json(content)
        assert result["name"] == "Embedded"

    @pytest.mark.unit
    def test_extract_json_invalid_raises(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test that invalid JSON raises error."""
        content = "This is not JSON at all"
        with pytest.raises(json.JSONDecodeError):
            llm_generator._extract_json(content)

    @pytest.mark.unit
    def test_ensure_list_with_list(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test _ensure_list with a list input."""
        result = llm_generator._ensure_list(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    @pytest.mark.unit
    def test_ensure_list_with_string(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test _ensure_list with a string input."""
        result = llm_generator._ensure_list("single value")
        assert result == ["single value"]

    @pytest.mark.unit
    def test_ensure_list_with_none(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test _ensure_list with None input."""
        result = llm_generator._ensure_list(None)
        assert result == []


class TestLLMCharacterProfileGeneratorPrompt:
    """Tests for prompt building."""

    @pytest.mark.unit
    def test_build_user_prompt_includes_all_params(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test that user prompt includes all parameters."""
        prompt = llm_generator._build_user_prompt(
            name="Test Hero",
            archetype="Champion",
            context="A war-torn kingdom",
        )

        assert "Test Hero" in prompt
        assert "Champion" in prompt
        assert "war-torn kingdom" in prompt

    @pytest.mark.unit
    def test_build_user_prompt_default_context(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test that empty context gets default value."""
        prompt = llm_generator._build_user_prompt(
            name="Test",
            archetype="Hero",
            context="",
        )

        assert "fantasy world" in prompt.lower()

    @pytest.mark.unit
    def test_default_system_prompt_structure(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test that default system prompt has required elements."""
        prompt = llm_generator._default_system_prompt()

        assert "JSON" in prompt
        assert "name" in prompt
        assert "aliases" in prompt
        assert "archetype" in prompt
        assert "traits" in prompt
        assert "appearance" in prompt


class TestLLMCharacterProfileGeneratorIntegration:
    """Integration-style tests with mocked API."""

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.character_profile_generator.requests.post")
    def test_generate_success(
        self,
        mock_post: MagicMock,
        llm_generator: LLMCharacterProfileGenerator,
        sample_llm_response: Dict[str, Any],
    ) -> None:
        """Test successful generation with mocked API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(sample_llm_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            llm_generator._api_key = "test-key"
            result = llm_generator.generate_character_profile(
                name="Kira Darkwood",
                archetype="Rogue",
                context="A thieves' guild",
            )

        assert result.name == "Kira Darkwood"
        assert "Shadow Blade" in result.aliases
        assert result.archetype == "Rogue"
        assert "cunning" in result.traits

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.character_profile_generator.requests.post")
    def test_generate_api_error_returns_error_result(
        self,
        mock_post: MagicMock,
        llm_generator: LLMCharacterProfileGenerator,
    ) -> None:
        """Test that API errors return error result."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            llm_generator._api_key = "test-key"
            result = llm_generator.generate_character_profile(
                name="Test",
                archetype="Hero",
            )

        assert "[Generation Error]" in result.aliases
        assert "failed" in result.appearance.lower()

    @pytest.mark.unit
    def test_generate_missing_api_key_returns_error_result(self) -> None:
        """Test that missing API key returns error result."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            generator = LLMCharacterProfileGenerator()
            generator._api_key = ""
            result = generator.generate_character_profile(
                name="Test",
                archetype="Hero",
            )

        assert "[Generation Error]" in result.aliases
        assert "GEMINI_API_KEY" in result.appearance

    @pytest.mark.unit
    @patch("src.contexts.world.infrastructure.generators.character_profile_generator.requests.post")
    def test_generate_rate_limit_error(
        self,
        mock_post: MagicMock,
        llm_generator: LLMCharacterProfileGenerator,
    ) -> None:
        """Test handling of rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            llm_generator._api_key = "test-key"
            result = llm_generator.generate_character_profile(
                name="Test",
                archetype="Hero",
            )

        assert "rate limit" in result.appearance.lower()


class TestCharacterProfileGeneratorFactory:
    """Tests for the CharacterProfileGenerator factory class."""

    @pytest.mark.unit
    def test_force_mock_creates_mock_generator(self) -> None:
        """Test that force_mock=True creates mock generator."""
        generator = CharacterProfileGenerator(force_mock=True)
        result = generator.generate_character_profile(
            name="Test Hero",
            archetype="Hero",
        )

        # Mock generator should return deterministic results
        assert result.name == "Test Hero"
        assert "courageous" in result.traits

    @pytest.mark.unit
    def test_env_mock_llm_true_creates_mock(self) -> None:
        """Test that MOCK_LLM=true creates mock generator."""
        with patch.dict("os.environ", {"MOCK_LLM": "true"}):
            generator = CharacterProfileGenerator()
            result = generator.generate_character_profile(
                name="Test",
                archetype="Villain",
            )

        assert "ruthless" in result.traits

    @pytest.mark.unit
    def test_env_mock_llm_yes_creates_mock(self) -> None:
        """Test that MOCK_LLM=yes creates mock generator."""
        with patch.dict("os.environ", {"MOCK_LLM": "yes"}):
            generator = CharacterProfileGenerator()
            result = generator.generate_character_profile(
                name="Test",
                archetype="Mentor",
            )

        assert "wise" in result.traits

    @pytest.mark.unit
    def test_env_mock_llm_1_creates_mock(self) -> None:
        """Test that MOCK_LLM=1 creates mock generator."""
        with patch.dict("os.environ", {"MOCK_LLM": "1"}):
            generator = CharacterProfileGenerator()
            result = generator.generate_character_profile(
                name="Test",
                archetype="Rogue",
            )

        assert "cunning" in result.traits


class TestConvenienceFunction:
    """Tests for the generate_character_profile convenience function."""

    @pytest.mark.unit
    def test_with_mock_generator(self) -> None:
        """Test convenience function with mock generator."""
        mock_gen = MockCharacterProfileGenerator()
        result = generate_character_profile(
            name="Test",
            archetype="Hero",
            generator=mock_gen,
        )

        assert result.name == "Test"
        assert "courageous" in result.traits

    @pytest.mark.unit
    def test_default_generator_with_mock_env(self) -> None:
        """Test convenience function with default generator in mock mode."""
        with patch.dict("os.environ", {"MOCK_LLM": "true"}):
            result = generate_character_profile(
                name="Default Test",
                archetype="Warrior",
            )

        assert result.name == "Default Test"
        assert result.archetype == "Warrior"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_empty_name_handling(self, mock_generator: MockCharacterProfileGenerator) -> None:
        """Test handling of empty name."""
        result = mock_generator.generate_character_profile(
            name="",
            archetype="Hero",
        )
        assert result.name == ""

    @pytest.mark.unit
    def test_whitespace_archetype_handling(
        self, mock_generator: MockCharacterProfileGenerator
    ) -> None:
        """Test handling of archetype with whitespace."""
        result = mock_generator.generate_character_profile(
            name="Test",
            archetype="  hero  ",
        )
        # Should still match hero template after strip and lower
        assert "courageous" in result.traits

    @pytest.mark.unit
    def test_special_characters_in_name(
        self, mock_generator: MockCharacterProfileGenerator
    ) -> None:
        """Test handling of special characters in name."""
        result = mock_generator.generate_character_profile(
            name="Sir O'Brien-McAllister III",
            archetype="Hero",
        )
        assert result.name == "Sir O'Brien-McAllister III"

    @pytest.mark.unit
    def test_long_context_handling(
        self, llm_generator: LLMCharacterProfileGenerator
    ) -> None:
        """Test that long context is included in prompt."""
        long_context = "A" * 1000
        prompt = llm_generator._build_user_prompt(
            name="Test",
            archetype="Hero",
            context=long_context,
        )
        assert long_context in prompt

    @pytest.mark.unit
    def test_result_immutability(self) -> None:
        """Test that CharacterProfileResult is immutable."""
        result = CharacterProfileResult(
            name="Test",
            aliases=["A"],
            archetype="Hero",
            traits=["brave"],
            appearance="Tall",
            backstory="Unknown",
            motivations=["justice"],
            quirks=["early"],
        )

        # Should raise an error when trying to modify
        with pytest.raises(AttributeError):
            result.name = "Modified"  # type: ignore
