import json
from unittest.mock import patch

from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
)
from src.contexts.character.infrastructure.generators.llm_character_generator import (
    LLMCharacterGenerator,
)


def test_llm_character_generator_parses_response() -> None:
    generator = LLMCharacterGenerator(model="test-model", temperature=0.1)
    captured = {}

    def fake_call(self, system_prompt: str, user_prompt: str) -> str:
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return json.dumps(
            {
                "name": "Echo Vale",
                "tagline": "A quiet signal in the noise.",
                "bio": "Echo traces forgotten broadcast trails.",
                "visual_prompt": "glowing circuit cloak, cyan highlights",
                "traits": ["focused", "mysterious"],
            }
        )

    with patch.object(LLMCharacterGenerator, "_call_gemini", new=fake_call):
        result = generator.generate(
            CharacterGenerationInput(
                concept="Signal tracer",
                archetype="Hero",
                tone="moody",
            )
        )

    assert result.name == "Echo Vale"
    assert result.visual_prompt == "glowing circuit cloak, cyan highlights"
    assert "system_prompt" in captured
    assert "user_prompt" in captured
    assert "Archetype: Hero" in captured["user_prompt"]
    assert "Concept: Signal tracer" in captured["user_prompt"]
    assert "Tone: moody" in captured["user_prompt"]


def test_llm_character_generator_falls_back_on_invalid_json() -> None:
    generator = LLMCharacterGenerator(model="test-model", temperature=0.1)

    def fake_call(self, system_prompt: str, user_prompt: str) -> str:
        return "not-json"

    with patch.object(LLMCharacterGenerator, "_call_gemini", new=fake_call):
        result = generator.generate(
            CharacterGenerationInput(
                concept="Lost cartographer",
                archetype="Mentor",
                tone=None,
            )
        )

    assert result.name == "Generation Error"
    assert "parsed" in result.bio
