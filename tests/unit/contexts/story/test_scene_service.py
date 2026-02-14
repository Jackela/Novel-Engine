"""Unit tests for SceneGenerationService.

Tests the service layer with mocked SceneGeneratorPort to verify
correct request passthrough and response handling.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.api.schemas import CharacterGenerationResponse
from src.contexts.story.application.ports.scene_generator_port import (
    SceneGenerationInput,
    SceneGenerationResult,
    SceneGeneratorPort,
)
from src.contexts.story.application.services.scene_service import (
    SceneGenerationService,
    generate_scene,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_character_context() -> CharacterGenerationResponse:
    """Create a mock character context for testing."""
    return CharacterGenerationResponse(
        name="Astra Vale",
        tagline="A reluctant beacon in a broken world.",
        bio="Astra is driven by a quiet resolve to protect the vulnerable.",
        visual_prompt="heroic figure in weathered armor, soft cyan glow",
        traits=["resilient", "empathetic", "principled"],
    )


@pytest.fixture
def mock_scene_result() -> SceneGenerationResult:
    """Create a mock scene generation result."""
    return SceneGenerationResult(
        title="The First Light",
        content="Astra stood at the edge of the broken city, her armor catching the dawn light...",
        summary="Astra surveys the devastation and makes a pivotal choice.",
        visual_prompt="lone figure on rubble, sunrise backlighting, dust particles in air",
    )


@pytest.fixture
def mock_generator(mock_scene_result: SceneGenerationResult) -> Mock:
    """Create a mock SceneGeneratorPort."""
    generator = Mock(spec=SceneGeneratorPort)
    generator.generate.return_value = mock_scene_result
    return generator


@pytest.mark.unit
class TestSceneGenerationService:
    """Tests for SceneGenerationService."""

    def test_generate_passes_input_to_generator(
        self,
        mock_generator: Mock,
        mock_character_context: CharacterGenerationResponse,
        mock_scene_result: SceneGenerationResult,
    ) -> None:
        """Service should pass the input to the generator and return its result."""
        service = SceneGenerationService(generator=mock_generator)

        result = service.generate(
            character_context=mock_character_context,
            scene_type="opening",
            tone="hopeful",
        )

        # Verify generator was called with correct input
        mock_generator.generate.assert_called_once()
        call_args = mock_generator.generate.call_args[0][0]
        assert isinstance(call_args, SceneGenerationInput)
        assert call_args.character_context == mock_character_context
        assert call_args.scene_type == "opening"
        assert call_args.tone == "hopeful"

        # Verify result is returned correctly
        assert result == mock_scene_result

    def test_generate_with_no_tone(
        self,
        mock_generator: Mock,
        mock_character_context: CharacterGenerationResponse,
    ) -> None:
        """Service should handle None tone gracefully."""
        service = SceneGenerationService(generator=mock_generator)

        service.generate(
            character_context=mock_character_context,
            scene_type="dialogue",
            tone=None,
        )

        call_args = mock_generator.generate.call_args[0][0]
        assert call_args.tone is None

    def test_generate_with_different_scene_types(
        self,
        mock_generator: Mock,
        mock_character_context: CharacterGenerationResponse,
    ) -> None:
        """Service should handle various scene types."""
        service = SceneGenerationService(generator=mock_generator)

        for scene_type in ["opening", "action", "dialogue", "climax", "resolution"]:
            service.generate(
                character_context=mock_character_context,
                scene_type=scene_type,
                tone=None,
            )
            call_args = mock_generator.generate.call_args[0][0]
            assert call_args.scene_type == scene_type


@pytest.mark.unit
class TestGenerateSceneFunction:
    """Tests for the generate_scene convenience function."""

    def test_generate_scene_uses_provided_generator(
        self,
        mock_generator: Mock,
        mock_character_context: CharacterGenerationResponse,
        mock_scene_result: SceneGenerationResult,
    ) -> None:
        """generate_scene should use the provided generator."""
        result = generate_scene(
            character_context=mock_character_context,
            scene_type="action",
            tone="tense",
            generator=mock_generator,
        )

        assert result == mock_scene_result
        mock_generator.generate.assert_called_once()

    def test_generate_scene_creates_input_correctly(
        self,
        mock_generator: Mock,
        mock_character_context: CharacterGenerationResponse,
    ) -> None:
        """generate_scene should create SceneGenerationInput with all fields."""
        generate_scene(
            character_context=mock_character_context,
            scene_type="climax",
            tone="dramatic",
            generator=mock_generator,
        )

        call_args = mock_generator.generate.call_args[0][0]
        assert call_args.character_context.name == "Astra Vale"
        assert call_args.scene_type == "climax"
        assert call_args.tone == "dramatic"
