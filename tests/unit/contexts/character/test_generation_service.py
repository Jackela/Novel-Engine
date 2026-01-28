from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
    DeterministicCharacterGenerator,
    generate_character_card,
)


def test_generate_character_card_hero_archetype() -> None:
    result = generate_character_card(
        CharacterGenerationInput(concept="lost heir", archetype="hero", tone="hopeful")
    )

    assert result.name == "Astra Vale"
    assert "lost heir" in result.bio
    assert "Tone: hopeful." in result.bio
    assert "resilient" in result.traits


def test_generate_character_card_unknown_archetype_defaults() -> None:
    result = generate_character_card(
        CharacterGenerationInput(concept="mystery", archetype="unknown", tone=None)
    )

    assert result.name == "Nova Quinn"
    assert "Concept: mystery." in result.bio


def test_deterministic_generator_mentor() -> None:
    generator = DeterministicCharacterGenerator()
    result = generator.generate(
        CharacterGenerationInput(concept="retired tactician", archetype="mentor")
    )

    assert result.name == "Elder Suri"
    assert result.tagline == "The wisdom that steadies the storm."
