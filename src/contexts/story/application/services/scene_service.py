"""Scene generation service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.api.schemas import CharacterGenerationResponse
from src.contexts.story.application.ports.scene_generator_port import (
    SceneGenerationInput,
    SceneGenerationResult,
    SceneGeneratorPort,
)

if TYPE_CHECKING:
    pass


class DeterministicSceneGenerator:
    """Fallback scene generator with deterministic output.

    This generator uses predefined templates to create scenes without
    requiring an LLM. It's useful for testing, development, and as a
    fallback when LLM services are unavailable.
    """

    def generate(self, request: SceneGenerationInput) -> SceneGenerationResult:
        """Generate a scene using template-based logic.

        Produces deterministic output by selecting templates based on
        scene type and interpolating character data.

        Args:
            request: Scene generation input containing character context,
                scene type ('opening', 'action', 'dialogue', 'climax',
                'resolution'), and optional tone.

        Returns:
            SceneGenerationResult with title, content, summary, and
            visual_prompt fields populated from templates.
        """
        char = request.character_context
        scene_type = request.scene_type
        tone = request.tone or "neutral"

        templates = {
            "opening": {
                "title": f"The Introduction of {char.name}",
                "content": (
                    f"{char.name} emerged from the shadows, their presence commanding "
                    f"attention. {char.tagline}\n\n{char.bio}"
                ),
                "summary": f"{char.name} makes their first appearance.",
                "visual_prompt": f"{char.visual_prompt}, establishing shot, cinematic",
            },
            "action": {
                "title": f"{char.name} in Motion",
                "content": (
                    f"The moment demanded action, and {char.name} responded with instinct "
                    f"honed through countless trials. Their {', '.join(char.traits[:2])} "
                    f"nature drove them forward.\n\nTone: {tone}."
                ),
                "summary": f"{char.name} takes decisive action.",
                "visual_prompt": f"{char.visual_prompt}, dynamic pose, motion blur",
            },
            "dialogue": {
                "title": f"Words from {char.name}",
                "content": (
                    f'"There are things you need to understand," {char.name} began, '
                    f'their voice carrying the weight of experience. {char.bio}'
                ),
                "summary": f"{char.name} reveals something important.",
                "visual_prompt": f"{char.visual_prompt}, close-up, emotional",
            },
            "climax": {
                "title": f"The Turning Point",
                "content": (
                    f"Everything had led to this moment. {char.name} stood at the precipice, "
                    f"their {char.traits[0] if char.traits else 'determined'} spirit tested "
                    f"like never before.\n\n{char.tagline}"
                ),
                "summary": f"A pivotal moment for {char.name}.",
                "visual_prompt": f"{char.visual_prompt}, dramatic lighting, peak tension",
            },
            "resolution": {
                "title": f"After the Storm",
                "content": (
                    f"As the dust settled, {char.name} surveyed the aftermath. "
                    f"The path forward was clearer now, though not without its scars. "
                    f"{char.bio}"
                ),
                "summary": f"{char.name} finds a moment of peace.",
                "visual_prompt": f"{char.visual_prompt}, soft lighting, contemplative",
            },
        }

        template = templates.get(scene_type, templates["opening"])
        return SceneGenerationResult(
            title=template["title"],
            content=template["content"],
            summary=template["summary"],
            visual_prompt=template["visual_prompt"],
        )


class SceneGenerationService:
    """Service for generating narrative scenes.

    Orchestrates scene generation by delegating to a generator implementation.
    Follows the hexagonal architecture pattern where the service contains
    application logic and the generator (port) handles infrastructure concerns.
    """

    def __init__(self, generator: SceneGeneratorPort | None = None) -> None:
        """Initialize the service with a scene generator.

        Args:
            generator: Optional scene generator implementation. If not provided,
                defaults to DeterministicSceneGenerator. For LLM-based generation,
                inject LLMSceneGenerator from the infrastructure layer.
        """
        self._generator = generator or _select_default_generator()

    def generate(
        self,
        character_context: CharacterGenerationResponse,
        scene_type: str,
        tone: str | None = None,
    ) -> SceneGenerationResult:
        """Generate a scene based on character context and parameters.

        Args:
            character_context: Character data including name, bio, traits, and
                visual prompt from a previous character generation call.
            scene_type: Type of scene to generate. Valid values are 'opening',
                'action', 'dialogue', 'climax', or 'resolution'.
            tone: Optional tone modifier for the scene (e.g., 'dark', 'hopeful').

        Returns:
            SceneGenerationResult containing the generated scene's title,
            content, summary, and visual_prompt.
        """
        request = SceneGenerationInput(
            character_context=character_context,
            scene_type=scene_type,
            tone=tone,
        )
        return self._generator.generate(request)


def _select_default_generator() -> SceneGeneratorPort:
    """Select the appropriate generator based on configuration.

    Note: This function returns DeterministicSceneGenerator by default.
    For LLM-based generation, the caller (API layer) should inject
    the LLMSceneGenerator instance directly to maintain hexagonal
    architecture boundaries.
    """
    return DeterministicSceneGenerator()


def generate_scene(
    character_context: CharacterGenerationResponse,
    scene_type: str,
    tone: str | None = None,
    generator: SceneGeneratorPort | None = None,
) -> SceneGenerationResult:
    """Convenience function to generate a scene.

    Creates a SceneGenerationService instance and generates a scene in one call.
    Useful for simple use cases that don't need to manage service lifecycle.

    Args:
        character_context: Character data from character generation.
        scene_type: Scene type ('opening', 'action', 'dialogue', 'climax', 'resolution').
        tone: Optional tone modifier.
        generator: Optional custom generator. Defaults to DeterministicSceneGenerator.

    Returns:
        SceneGenerationResult with generated scene content.
    """
    service = SceneGenerationService(generator=generator)
    return service.generate(
        character_context=character_context,
        scene_type=scene_type,
        tone=tone,
    )
