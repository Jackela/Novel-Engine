"""Repository port for independent generation runs and snapshots."""

from __future__ import annotations

from typing import Protocol

from src.contexts.narrative.application.services.story_workflow_types import (
    GenerationRunResourceState,
)


class GenerationRunRepositoryPort(Protocol):
    """Persist append-only run resources independently from workspace state."""

    async def get_by_story_id(
        self,
        story_id: str,
    ) -> GenerationRunResourceState | None:
        """Return run resources for a story if they exist."""
        ...

    async def save(self, state: GenerationRunResourceState) -> None:
        """Persist run resources for a story."""
        ...

    async def delete(self, story_id: str) -> bool:
        """Delete run resources for a story."""
        ...

