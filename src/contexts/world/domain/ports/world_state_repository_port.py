"""World state repository port."""

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from src.contexts.world.domain.aggregates.world_state import WorldState


class WorldStateRepositoryPort(Protocol):
    """Repository port for WorldState aggregate."""

    async def get_by_id(self, world_id: UUID) -> "WorldState | None":
        """Get world state by ID."""
        ...

    async def get_by_story(self, story_id: UUID) -> "WorldState | None":
        """Get world state by story ID."""
        ...

    async def save(self, world_state: "WorldState") -> None:
        """Save world state."""
        ...

    async def delete(self, world_id: UUID) -> bool:
        """Delete world state."""
        ...

    async def get_version_history(
        self, world_id: UUID, limit: int = 50
    ) -> "list[WorldState]":
        """Get version history."""
        ...

    async def create_snapshot(self, world_id: UUID) -> UUID:
        """Create snapshot of world state."""
        ...
