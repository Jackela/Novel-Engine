"""Scene generation value objects for domain layer.

These are domain-level representations of scene generation data.
They exist to avoid importing API schemas from the domain layer,
maintaining hexagonal architecture boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SceneGenerationResult:
    """Domain value object containing generated scene data.

    This captures the result of scene generation without depending
    on API layer schemas.

    Attributes:
        title: The scene's title.
        content: The full markdown story text of the scene.
        summary: A short summary for node display.
        visual_prompt: Text description for generating scene visuals.
    """

    title: str
    content: str  # Markdown story text
    summary: str  # Short text for node display
    visual_prompt: str

    def __post_init__(self) -> None:
        """Validate the scene generation result after initialization."""
        if not self.title:
            raise ValueError("Scene title cannot be empty")
        if not self.content:
            raise ValueError("Scene content cannot be empty")
