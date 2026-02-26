"""Port definition for scene generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.contexts.character.domain.value_objects import CharacterContext
from src.contexts.story.domain.value_objects import SceneGenerationResult


@dataclass(frozen=True)
class SceneGenerationInput:
    """Input data for scene generation."""

    character_context: CharacterContext
    scene_type: str  # 'opening', 'action', 'dialogue', 'climax', 'resolution'
    tone: str | None = None


class SceneGeneratorPort(Protocol):
    """Protocol for scene generators."""

    def generate(self, request: SceneGenerationInput) -> SceneGenerationResult:
        """Generate a scene from structured input."""
        raise NotImplementedError(
            "SceneGeneratorPort implementations must define `generate`."
        )
