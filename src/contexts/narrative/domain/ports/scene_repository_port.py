"""Scene repository port."""

from typing import Protocol
from uuid import UUID

from src.contexts.narrative.domain.entities.scene import Scene


class SceneRepositoryPort(Protocol):
    """Repository port for Scene entity."""

    async def get_by_id(self, scene_id: UUID) -> Scene | None:
        """Get scene by ID."""
        ...

    async def get_by_chapter(self, chapter_id: UUID) -> list[Scene]:
        """Get scenes by chapter ID."""
        ...

    async def save(self, scene: Scene) -> None:
        """Save scene."""
        ...

    async def delete(self, scene_id: UUID) -> bool:
        """Delete scene."""
        ...
