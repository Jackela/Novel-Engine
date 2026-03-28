"""In-memory repository for independent generation runs."""

from __future__ import annotations

import copy

from src.contexts.narrative.application.ports.generation_run_repository_port import (
    GenerationRunRepositoryPort,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    GenerationRunResourceState,
)


class InMemoryGenerationRunRepository(GenerationRunRepositoryPort):
    """Persist generation run resources in-process for tests and local runs."""

    def __init__(self) -> None:
        self._states: dict[str, GenerationRunResourceState] = {}

    def reset(self) -> None:
        """Clear all stored run resources."""
        self._states.clear()

    async def get_by_story_id(
        self,
        story_id: str,
    ) -> GenerationRunResourceState | None:
        state = self._states.get(story_id)
        return copy.deepcopy(state) if state is not None else None

    async def save(self, state: GenerationRunResourceState) -> None:
        self._states[state.story_id] = copy.deepcopy(state)

    async def delete(self, story_id: str) -> bool:
        return self._states.pop(story_id, None) is not None


__all__ = ["InMemoryGenerationRunRepository"]

