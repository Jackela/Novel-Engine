"""In-memory repository for independent story generation state."""

from __future__ import annotations

import copy

from src.contexts.narrative.application.ports.story_generation_state_repository_port import (
    StoryGenerationStateRepositoryPort,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryGenerationState,
)


class InMemoryStoryGenerationStateRepository(StoryGenerationStateRepositoryPort):
    """Persist story generation state in-process for tests and local runs."""

    def __init__(self) -> None:
        self._states: dict[str, StoryGenerationState] = {}

    def reset(self) -> None:
        """Clear all stored generation state."""
        self._states.clear()

    async def get_by_story_id(self, story_id: str) -> StoryGenerationState | None:
        state = self._states.get(story_id)
        return copy.deepcopy(state) if state is not None else None

    async def save(self, state: StoryGenerationState) -> None:
        self._states[state.story_id] = copy.deepcopy(state)

    async def delete(self, story_id: str) -> bool:
        return self._states.pop(story_id, None) is not None


__all__ = ["InMemoryStoryGenerationStateRepository"]
