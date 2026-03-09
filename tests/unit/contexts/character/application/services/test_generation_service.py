#!/usr/bin/env python3
"""
Unit Tests for Character Generation Service

Tests the character generation functionality including:
- Deterministic character generation
- Template-based generation
- Archetype-specific character creation
- Input validation
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
    CharacterGenerationResult,
    DeterministicCharacterGenerator,
    _get_mock_template,
    _select_default_generator,
    generate_character_card,
)

pytestmark = pytest.mark.unit


# ==================== Template Tests ====================


class TestMockTemplates:
    """Tests for mock template generation."""

    @pytest.mark.unit
    def test_get_hero_template(self):
        """Test getting hero archetype template."""
        template = _get_mock_template("hero")

        assert template["name"] == "Astra Vale"
        assert "reluctant beacon" in template["tagline"].lower()
        assert "resilient" in template["traits"]
        assert "heroic figure" in template["visual_prompt"]

    @pytest.mark.unit
    def test_get_antihero_template(self):
        """Test getting antihero archetype template."""
        template = _get_mock_template("antihero")

        assert template["name"] == "Kael Riven"
        assert "blade" in template["tagline"].lower()
        assert "cynical" in template["traits"]
        assert "shadowed" in template["visual_prompt"]

    @pytest.mark.unit
    def test_get_mentor_template(self):
        """Test getting mentor archetype template."""
        template = _get_mock_template("mentor")

        assert template["name"] == "Elder Suri"
        assert "wisdom" in template["tagline"].lower()
        assert "wise" in template["traits"]
        assert "serene elder" in template["visual_prompt"]

    @pytest.mark.unit
    def test_get_villain_template(self):
        """Test getting villain archetype template."""
        template = _get_mock_template("villain")

        assert template["name"] == "Vesper Kain"
        assert "fear" in template["tagline"].lower()
        assert "calculating" in template["traits"]
        assert "regal antagonist" in template["visual_prompt"]

    @pytest.mark.unit
    def test_get_default_template(self):
        """Test getting default template for unknown archetype."""
        template = _get_mock_template("unknown_archetype")

        assert template["name"] == "Nova Quinn"
        assert "adaptive" in template["traits"]
        assert "uncharted spark" in template["tagline"].lower()

    @pytest.mark.unit
    def test_get_template_empty_string(self):
        """Test getting template with empty string defaults to default template."""
        template = _get_mock_template("")

        assert template["name"] == "Nova Quinn"

    @pytest.mark.unit
    def test_get_template_none(self):
        """Test getting template with None defaults to default template."""
        template = _get_mock_template(None)

        assert template["name"] == "Nova Quinn"

    @pytest.mark.unit
    def test_get_template_case_insensitive(self):
        """Test that archetype matching is case insensitive."""
        template_lower = _get_mock_template("hero")
        template_upper = _get_mock_template("HERO")
        template_mixed = _get_mock_template("HeRo")

        assert template_lower == template_upper == template_mixed

    @pytest.mark.unit
    def test_get_template_whitespace_handling(self):
        """Test that archetype matching handles whitespace."""
        template = _get_mock_template("  hero  ")

        assert template["name"] == "Astra Vale"


# ==================== DeterministicCharacterGenerator Tests ====================


class TestDeterministicCharacterGenerator:
    """Tests for DeterministicCharacterGenerator."""

    @pytest.mark.unit
    def test_generate_basic_character(self):
        """Test basic character generation."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="A brave warrior",
            archetype="hero",
        )

        result = generator.generate(request)

        assert isinstance(result, CharacterGenerationResult)
        assert result.name == "Astra Vale"
        assert "brave warrior" in result.bio
        assert isinstance(result.traits, list)
        assert len(result.traits) > 0

    @pytest.mark.unit
    def test_generate_with_tone(self):
        """Test character generation with tone."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="A mysterious figure",
            archetype="antihero",
            tone="dark and brooding",
        )

        result = generator.generate(request)

        assert result.name == "Kael Riven"
        assert "Tone: dark and brooding" in result.bio

    @pytest.mark.unit
    def test_generate_without_tone(self):
        """Test character generation without tone."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="A simple farmer",
            archetype="mentor",
            tone=None,
        )

        result = generator.generate(request)

        assert result.name == "Elder Suri"
        assert "Tone:" not in result.bio

    @pytest.mark.unit
    def test_generate_empty_concept(self):
        """Test character generation with empty concept."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="",
            archetype="villain",
        )

        result = generator.generate(request)

        assert result.name == "Vesper Kain"
        assert "Unknown origin" in result.bio

    @pytest.mark.unit
    def test_generate_empty_tone(self):
        """Test character generation with empty/whitespace tone."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="Test",
            archetype="hero",
            tone="   ",
        )

        result = generator.generate(request)

        assert "Tone:" not in result.bio

    @pytest.mark.unit
    def test_generate_all_archetypes(self):
        """Test generation for all defined archetypes."""
        generator = DeterministicCharacterGenerator()
        archetypes = ["hero", "antihero", "mentor", "villain", ""]

        for archetype in archetypes:
            request = CharacterGenerationInput(
                concept=f"Test concept for {archetype}",
                archetype=archetype,
            )
            result = generator.generate(request)

            assert isinstance(result, CharacterGenerationResult)
            assert result.name
            assert result.tagline
            assert result.bio
            assert result.visual_prompt
            assert len(result.traits) > 0

    @pytest.mark.unit
    def test_generate_result_structure(self):
        """Test that generated result has correct structure."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="Test",
            archetype="hero",
        )

        result = generator.generate(request)

        # Verify all fields are strings or lists
        assert isinstance(result.name, str)
        assert isinstance(result.tagline, str)
        assert isinstance(result.bio, str)
        assert isinstance(result.visual_prompt, str)
        assert isinstance(result.traits, list)
        assert all(isinstance(t, str) for t in result.traits)

    @pytest.mark.unit
    def test_generate_traits_are_copied(self):
        """Test that traits are copied, not referenced."""
        generator = DeterministicCharacterGenerator()
        request = CharacterGenerationInput(
            concept="Test",
            archetype="hero",
        )

        result1 = generator.generate(request)
        result2 = generator.generate(request)

        # Modifying one should not affect the other
        result1.traits.append("extra_trait")
        assert "extra_trait" not in result2.traits


# ==================== Generator Selection Tests ====================


class TestGeneratorSelection:
    """Tests for generator selection logic."""

    @pytest.mark.unit
    def test_select_default_generator_in_pytest(self):
        """Test that pytest environment returns deterministic generator."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_example"}):
            generator = _select_default_generator()

        assert isinstance(generator, DeterministicCharacterGenerator)

    @pytest.mark.unit
    def test_select_default_generator_with_llm_enabled(self):
        """Test generator selection when LLM is enabled."""
        # Note: In the test environment, LLM generator may or may not be available
        with patch.dict(os.environ, {"ENABLE_LLM_GENERATION": "true"}, clear=True):
            # Remove PYTEST_CURRENT_TEST to test LLM path
            env_without_test = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
            with patch.dict(os.environ, env_without_test, clear=True):
                with patch.dict(os.environ, {"ENABLE_LLM_GENERATION": "true"}):
                    generator = _select_default_generator()

        # Should return either LLM or Deterministic generator depending on availability
        from src.contexts.character.infrastructure.generators.llm_character_generator import (
            LLMCharacterGenerator,
        )
        assert isinstance(generator, (DeterministicCharacterGenerator, LLMCharacterGenerator))

    @pytest.mark.unit
    def test_select_default_generator_default(self):
        """Test default generator selection."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            generator = _select_default_generator()

        assert isinstance(generator, DeterministicCharacterGenerator)


# ==================== generate_character_card Tests ====================


class TestGenerateCharacterCard:
    """Tests for generate_character_card function."""

    @pytest.mark.unit
    def test_generate_with_default_generator(self):
        """Test generation using default generator."""
        request = CharacterGenerationInput(
            concept="A noble knight",
            archetype="hero",
        )

        result = generate_character_card(request)

        assert isinstance(result, CharacterGenerationResult)
        assert result.name == "Astra Vale"

    @pytest.mark.unit
    def test_generate_with_custom_generator(self):
        """Test generation with custom generator."""
        custom_generator = Mock()
        custom_result = CharacterGenerationResult(
            name="Custom Name",
            tagline="Custom tagline",
            bio="Custom bio",
            visual_prompt="Custom visual",
            traits=["custom"],
        )
        custom_generator.generate.return_value = custom_result

        request = CharacterGenerationInput(
            concept="Test",
            archetype="hero",
        )

        result = generate_character_card(request, generator=custom_generator)

        custom_generator.generate.assert_called_once_with(request)
        assert result == custom_result

    @pytest.mark.unit
    def test_generate_with_none_generator(self):
        """Test generation with None generator uses default."""
        request = CharacterGenerationInput(
            concept="Test",
            archetype="villain",
        )

        result = generate_character_card(request, generator=None)

        assert isinstance(result, CharacterGenerationResult)
        assert result.name == "Vesper Kain"


# ==================== Input/Output Model Tests ====================


class TestDataModels:
    """Tests for CharacterGenerationInput and CharacterGenerationResult."""

    @pytest.mark.unit
    def test_input_model_creation(self):
        """Test CharacterGenerationInput creation."""
        input_data = CharacterGenerationInput(
            concept="Test concept",
            archetype="hero",
            tone="epic",
        )

        assert input_data.concept == "Test concept"
        assert input_data.archetype == "hero"
        assert input_data.tone == "epic"

    @pytest.mark.unit
    def test_input_model_defaults(self):
        """Test CharacterGenerationInput default values."""
        input_data = CharacterGenerationInput(
            concept="Test",
            archetype="hero",
        )

        assert input_data.tone is None

    @pytest.mark.unit
    def test_input_model_frozen(self):
        """Test that CharacterGenerationInput is immutable."""
        input_data = CharacterGenerationInput(
            concept="Test",
            archetype="hero",
        )

        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            input_data.concept = "Modified"

    @pytest.mark.unit
    def test_result_model_creation(self):
        """Test CharacterGenerationResult creation."""
        result = CharacterGenerationResult(
            name="Test Name",
            tagline="Test Tagline",
            bio="Test Bio",
            visual_prompt="Test Visual",
            traits=["trait1", "trait2"],
        )

        assert result.name == "Test Name"
        assert result.traits == ["trait1", "trait2"]

    @pytest.mark.unit
    def test_result_model_frozen(self):
        """Test that CharacterGenerationResult is immutable."""
        result = CharacterGenerationResult(
            name="Test",
            tagline="Tagline",
            bio="Bio",
            visual_prompt="Visual",
            traits=["trait"],
        )

        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            result.name = "Modified"


# ==================== Integration Tests ====================


class TestGenerationIntegration:
    """Integration-style tests for the generation flow."""

    @pytest.mark.unit
    def test_full_generation_flow_hero(self):
        """Test complete generation flow for hero."""
        request = CharacterGenerationInput(
            concept="A champion of justice protecting the innocent",
            archetype="hero",
            tone="hopeful and inspiring",
        )

        result = generate_character_card(request)

        assert result.name == "Astra Vale"
        assert "champion of justice" in result.bio
        assert "hopeful and inspiring" in result.bio
        assert "resilient" in result.traits
        assert result.visual_prompt

    @pytest.mark.unit
    def test_full_generation_flow_villain(self):
        """Test complete generation flow for villain."""
        request = CharacterGenerationInput(
            concept="A tyrant ruling with an iron fist",
            archetype="villain",
            tone="menacing",
        )

        result = generate_character_card(request)

        assert result.name == "Vesper Kain"
        assert "tyrant" in result.bio
        assert "menacing" in result.bio
        assert "calculating" in result.traits

    @pytest.mark.unit
    def test_generation_preserves_concept(self):
        """Test that concept is preserved in output bio."""
        concept = "Very specific unique concept XYZ123"
        request = CharacterGenerationInput(
            concept=concept,
            archetype="mentor",
        )

        result = generate_character_card(request)

        assert concept in result.bio
