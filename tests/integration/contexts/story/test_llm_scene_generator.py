"""Integration tests for LLMSceneGenerator.

Tests the LLM adapter with mocked API calls to verify:
- YAML prompt loading
- Prompt rendering
- JSON response parsing
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.api.schemas import CharacterGenerationResponse
from src.contexts.story.application.ports.scene_generator_port import (
    SceneGenerationInput,
)
from src.contexts.story.infrastructure.generators.llm_scene_generator import (
    LLMSceneGenerator,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def character_context() -> CharacterGenerationResponse:
    """Create a character context for testing."""
    return CharacterGenerationResponse(
        name="Kael Riven",
        tagline="The blade that cuts both ways.",
        bio="Kael walks the line between survival and redemption.",
        visual_prompt="shadowed wanderer, scarred cloak, neon rim light",
        traits=["cynical", "resourceful", "driven"],
    )


@pytest.fixture
def scene_input(character_context: CharacterGenerationResponse) -> SceneGenerationInput:
    """Create a scene generation input."""
    return SceneGenerationInput(
        character_context=character_context,
        scene_type="action",
        tone="noir",
    )


@pytest.fixture
def valid_llm_response() -> str:
    """Return a valid JSON response string."""
    return json.dumps(
        {
            "title": "Shadows in the Alley",
            "content": "Kael pressed his back against the cold brick wall, the distant neon signs casting fractured light across his scarred face. The footsteps grew closer, echoing through the narrow passage.",
            "summary": "Kael faces off against pursuers in a rain-soaked alley.",
            "visual_prompt": "dark alley, neon reflections on wet pavement, silhouette confrontation",
        }
    )


@pytest.mark.integration
class TestLLMSceneGeneratorPromptLoading:
    """Tests for prompt loading functionality."""

    def test_loads_system_prompt_from_yaml(self) -> None:
        """Generator should load system prompt from scene_gen.yaml."""
        generator = LLMSceneGenerator(model="test-model")
        prompt = generator._load_system_prompt()

        assert "bestselling fiction author" in prompt
        assert "CHARACTER CONTEXT" in prompt
        assert "SCENE TYPE" in prompt
        assert "OUTPUT FORMAT" in prompt

    def test_raises_error_if_prompt_missing(self, tmp_path) -> None:
        """Generator should raise if system_prompt key is missing."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("other_key: value")

        generator = LLMSceneGenerator(prompt_path=empty_yaml)

        with pytest.raises(ValueError, match="Missing system_prompt"):
            generator._load_system_prompt()


@pytest.mark.integration
class TestLLMSceneGeneratorPromptBuilding:
    """Tests for user prompt building."""

    def test_builds_user_prompt_with_all_fields(
        self, scene_input: SceneGenerationInput
    ) -> None:
        """User prompt should include character context, scene type, and tone."""
        generator = LLMSceneGenerator(model="test-model")
        prompt = generator._build_user_prompt(scene_input)

        assert "Kael Riven" in prompt
        assert "action" in prompt
        assert "noir" in prompt
        assert "JSON" in prompt

    def test_builds_user_prompt_without_tone(
        self, character_context: CharacterGenerationResponse
    ) -> None:
        """User prompt should handle missing tone gracefully."""
        input_no_tone = SceneGenerationInput(
            character_context=character_context,
            scene_type="dialogue",
            tone=None,
        )
        generator = LLMSceneGenerator(model="test-model")
        prompt = generator._build_user_prompt(input_no_tone)

        assert "unspecified" in prompt.lower() or "tone" in prompt.lower()


@pytest.mark.integration
class TestLLMSceneGeneratorParsing:
    """Tests for response parsing."""

    def test_parses_valid_json_response(
        self,
        scene_input: SceneGenerationInput,
        valid_llm_response: str,
    ) -> None:
        """Generator should parse valid JSON into SceneGenerationResult."""
        generator = LLMSceneGenerator(model="test-model")

        def fake_call(self, system_prompt: str, user_prompt: str) -> str:
            return valid_llm_response

        with patch.object(LLMSceneGenerator, "_call_gemini", new=fake_call):
            result = generator.generate(scene_input)

        assert result.title == "Shadows in the Alley"
        assert "Kael pressed his back" in result.content
        assert "rain-soaked alley" in result.summary
        assert "neon reflections" in result.visual_prompt

    def test_parses_json_from_markdown_block(
        self, scene_input: SceneGenerationInput
    ) -> None:
        """Generator should extract JSON from markdown code blocks."""
        generator = LLMSceneGenerator(model="test-model")

        markdown_response = """Here's the scene:
```json
{
    "title": "Dawn's Edge",
    "content": "The first light crept over the horizon.",
    "summary": "A new day begins.",
    "visual_prompt": "sunrise over ruins"
}
```
"""

        def fake_call(self, system_prompt: str, user_prompt: str) -> str:
            return markdown_response

        with patch.object(LLMSceneGenerator, "_call_gemini", new=fake_call):
            result = generator.generate(scene_input)

        assert result.title == "Dawn's Edge"

    def test_falls_back_on_invalid_json(
        self, scene_input: SceneGenerationInput
    ) -> None:
        """Generator should return error result on invalid JSON."""
        generator = LLMSceneGenerator(model="test-model")

        def fake_call(self, system_prompt: str, user_prompt: str) -> str:
            return "not-valid-json-at-all"

        with patch.object(LLMSceneGenerator, "_call_gemini", new=fake_call):
            result = generator.generate(scene_input)

        assert result.title == "Generation Error"
        assert "parsed" in result.summary.lower() or "error" in result.summary.lower()


@pytest.mark.integration
class TestLLMSceneGeneratorEndToEnd:
    """End-to-end tests with mocked API."""

    def test_full_generation_flow(
        self,
        scene_input: SceneGenerationInput,
        valid_llm_response: str,
    ) -> None:
        """Test complete flow from input to result."""
        generator = LLMSceneGenerator(model="test-model", temperature=0.5)
        captured = {}

        def fake_call(self, system_prompt: str, user_prompt: str) -> str:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt
            return valid_llm_response

        with patch.object(LLMSceneGenerator, "_call_gemini", new=fake_call):
            result = generator.generate(scene_input)

        # Verify prompts were constructed correctly
        assert "bestselling" in captured["system_prompt"]
        assert "Kael Riven" in captured["user_prompt"]
        assert "action" in captured["user_prompt"]

        # Verify result
        assert result.title == "Shadows in the Alley"
        assert result.content is not None
        assert len(result.content) > 0
