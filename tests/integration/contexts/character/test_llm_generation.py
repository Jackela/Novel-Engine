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

    def fake_call(self, messages):
        captured["messages"] = messages
        return json.dumps(
            {
                "name": "Echo Vale",
                "tagline": "A quiet signal in the noise.",
                "bio": "Echo traces forgotten broadcast trails.",
                "visual_prompt": "glowing circuit cloak, cyan highlights",
                "traits": ["focused", "mysterious"],
            }
        )

    with patch.object(LLMCharacterGenerator, "_call_llm", new=fake_call):
        result = generator.generate(
            CharacterGenerationInput(
                concept="Signal tracer",
                archetype="Hero",
                tone="moody",
            )
        )

    assert result.name == "Echo Vale"
    assert result.visual_prompt == "glowing circuit cloak, cyan highlights"
    assert "messages" in captured
    assert captured["messages"][0]["role"] == "system"
    assert "Archetype: Hero" in captured["messages"][1]["content"]
    assert "Concept: Signal tracer" in captured["messages"][1]["content"]
    assert "Tone: moody" in captured["messages"][1]["content"]


def test_llm_character_generator_falls_back_on_invalid_json() -> None:
    generator = LLMCharacterGenerator(model="test-model", temperature=0.1)

    def fake_call(self, messages):
        return "not-json"

    with patch.object(LLMCharacterGenerator, "_call_llm", new=fake_call):
        result = generator.generate(
            CharacterGenerationInput(
                concept="Lost cartographer",
                archetype="Mentor",
                tone=None,
            )
        )

    assert result.name == "Generation Error"
    assert "parsed" in result.bio
