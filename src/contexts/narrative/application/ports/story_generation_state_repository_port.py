"""Repository port for independent story generation state."""

from __future__ import annotations

from typing import Protocol

from src.contexts.narrative.application.services.story_workflow_types import (
    StoryGenerationState,
)


class StoryGenerationStateRepositoryPort(Protocol):
    """Persist append-only generation state independently from Story metadata."""

    async def get_by_story_id(self, story_id: str) -> StoryGenerationState | None:
        """Return generation state for a story if it exists."""
        ...

    async def save(self, state: StoryGenerationState) -> None:
        """Persist generation state for a story."""
        ...

    async def delete(self, story_id: str) -> bool:
        """Delete generation state for a story."""
        ...

