"""In-memory repository for independent story artifacts."""

from __future__ import annotations

import copy

from src.contexts.narrative.application.ports.story_artifact_repository_port import (
    StoryArtifactRepositoryPort,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryArtifactResourceState,
)


class InMemoryStoryArtifactRepository(StoryArtifactRepositoryPort):
    """Persist story artifact resources in-process for tests and local runs."""

    def __init__(self) -> None:
        self._states: dict[str, StoryArtifactResourceState] = {}

    def reset(self) -> None:
        """Clear all stored artifact resources."""
        self._states.clear()

    async def get_by_story_id(
        self,
        story_id: str,
    ) -> StoryArtifactResourceState | None:
        state = self._states.get(story_id)
        return copy.deepcopy(state) if state is not None else None

    async def save(self, state: StoryArtifactResourceState) -> None:
        self._states[state.story_id] = copy.deepcopy(state)

    async def delete(self, story_id: str) -> bool:
        return self._states.pop(story_id, None) is not None


__all__ = ["InMemoryStoryArtifactRepository"]

