"""Repository port for independent append-only story artifacts."""

from __future__ import annotations

from typing import Protocol

from src.contexts.narrative.application.services.story_workflow_types import (
    StoryArtifactResourceState,
)


class StoryArtifactRepositoryPort(Protocol):
    """Persist append-only artifact resources independently from workspace state."""

    async def get_by_story_id(
        self,
        story_id: str,
    ) -> StoryArtifactResourceState | None:
        """Return artifact resources for a story if they exist."""
        ...

    async def save(self, state: StoryArtifactResourceState) -> None:
        """Persist artifact resources for a story."""
        ...

    async def delete(self, story_id: str) -> bool:
        """Delete artifact resources for a story."""
        ...

