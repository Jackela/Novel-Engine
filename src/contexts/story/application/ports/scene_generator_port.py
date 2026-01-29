"""Port definition for scene generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.api.schemas import CharacterGenerationResponse


@dataclass(frozen=True)
class SceneGenerationInput:
    """Input data for scene generation."""

    character_context: CharacterGenerationResponse
    scene_type: str  # 'opening', 'action', 'dialogue', 'climax', 'resolution'
    tone: str | None = None


@dataclass(frozen=True)
class SceneGenerationResult:
    """Result of scene generation."""

    title: str
    content: str  # Markdown story text
    summary: str  # Short text for node display
    visual_prompt: str


class SceneGeneratorPort(Protocol):
    """Protocol for scene generators."""

    def generate(self, request: SceneGenerationInput) -> SceneGenerationResult:
        """Generate a scene from structured input."""
        ...
