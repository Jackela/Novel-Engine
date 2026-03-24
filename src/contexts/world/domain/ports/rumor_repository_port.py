"""Rumor repository port."""

from typing import TYPE_CHECKING, List, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from src.contexts.world.domain.entities.rumor import Rumor


class RumorRepositoryPort(Protocol):
    """Repository port for Rumor entity."""

    async def get_by_id(self, rumor_id: UUID) -> "Rumor | None":
        """Get rumor by ID."""
        ...

    async def get_active_by_world(self, world_id: UUID) -> "List[Rumor]":
        """Get active rumors by world ID."""
        ...

    async def save(self, rumor: "Rumor") -> "Rumor":
        """Save rumor."""
        ...

    async def save_all(self, rumors: "List[Rumor]") -> "List[Rumor]":
        """Save multiple rumors."""
        ...

    async def delete(self, rumor_id: UUID) -> bool:
        """Delete rumor by ID."""
        ...

    async def get_by_world_id(self, world_id: str) -> "List[Rumor]":
        """Get all rumors for a world."""
        ...

    async def get_active_rumors(self, world_id: str) -> "List[Rumor]":
        """Get active rumors (truth_value > 0) for a world."""
        ...

    async def update_propagation(self, rumor_id: UUID, reach: int) -> None:
        """Update rumor propagation reach."""
        ...
