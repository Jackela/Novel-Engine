"""Scene generation service."""

from __future__ import annotations

import os
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
    """Fallback scene generator with deterministic output."""

    def generate(self, request: SceneGenerationInput) -> SceneGenerationResult:
        """Generate a scene using template-based logic."""
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
    """Service for generating narrative scenes."""

    def __init__(self, generator: SceneGeneratorPort | None = None) -> None:
        """Initialize with a scene generator."""
        self._generator = generator or _select_default_generator()

    def generate(
        self,
        character_context: CharacterGenerationResponse,
        scene_type: str,
        tone: str | None = None,
    ) -> SceneGenerationResult:
        """Generate a scene based on character context and parameters."""
        request = SceneGenerationInput(
            character_context=character_context,
            scene_type=scene_type,
            tone=tone,
        )
        return self._generator.generate(request)


def _select_default_generator() -> SceneGeneratorPort:
    """Select the appropriate generator based on configuration."""
    if os.getenv("ENABLE_LLM_GENERATION", "").lower() == "true":
        try:
            from src.contexts.story.infrastructure.generators.llm_scene_generator import (
                LLMSceneGenerator,
            )

            return LLMSceneGenerator()
        except Exception:
            return DeterministicSceneGenerator()
    return DeterministicSceneGenerator()


def generate_scene(
    character_context: CharacterGenerationResponse,
    scene_type: str,
    tone: str | None = None,
    generator: SceneGeneratorPort | None = None,
) -> SceneGenerationResult:
    """Convenience function to generate a scene."""
    service = SceneGenerationService(generator=generator)
    return service.generate(
        character_context=character_context,
        scene_type=scene_type,
        tone=tone,
    )
