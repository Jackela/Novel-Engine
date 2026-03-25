"""World Simulation Protocols.

Protocol interfaces for simulation service dependencies.
"""

from typing import List, Optional, Protocol, runtime_checkable

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction
from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot
from src.shared.application.result import Failure, Result


@runtime_checkable
class IWorldStateRepository(Protocol):
    # Protocol for WorldState repository interface.
    # Defines the minimal interface needed by WorldSimulationService.

    async def get_by_id(self, world_state_id: str) -> WorldState | None:
        # Retrieve a WorldState by ID.
        #
        # Args:
        #     world_state_id: Unique identifier for the world state
        #
        # Returns:
        #     WorldState if found, None otherwise
        ...


@runtime_checkable
class IFactionRepository(Protocol):
    # Protocol for Faction repository interface.
    # Defines the minimal interface needed by WorldSimulationService.

    async def get_by_world_id(self, world_id: str) -> List[Faction]:
        # Retrieve all factions for a world.
        #
        # Args:
        #     world_id: ID of the world to get factions for
        #
        # Returns:
        #     List of Faction entities in the world
        ...

    async def save(self, faction: Faction) -> Faction:
        # Save a faction entity.
        #
        # Args:
        #     faction: Faction entity to save
        #
        # Returns:
        #     Saved Faction entity
        ...

    async def save_all(self, factions: List[Faction]) -> List[Faction]:
        # Save multiple faction entities.
        #
        # Args:
        #     factions: List of Faction entities to save
        #
        # Returns:
        #     List of saved Faction entities
        ...


@runtime_checkable
class ISnapshotService(Protocol):
    # Protocol for SnapshotService interface.
    # Defines the minimal interface needed by WorldSimulationService.

    def create_snapshot(
        self, world_id: str, tick_number: int, description: str = ""
    ) -> Result[WorldSnapshot, Failure]:
        # Create a snapshot of the current world state.
        #
        # Args:
        #     world_id: ID of the world to snapshot
        #     tick_number: Sequential tick number
        #     description: Optional description
        #
        # Returns:
        #     Result containing created WorldSnapshot or error
        ...

    def restore_snapshot(self, snapshot_id: str) -> Result[WorldSnapshot, Failure]:
        # Restore world state from a snapshot.
        #
        # Args:
        #     snapshot_id: ID of the snapshot to restore
        #
        # Returns:
        #     Result containing restored WorldSnapshot or error
        ...

    def get_latest_snapshot(
        self, world_id: str
    ) -> Result[Optional[WorldSnapshot], Failure]:
        # Get the latest snapshot for a world.
        #
        # Args:
        #     world_id: ID of the world
        #
        # Returns:
        #     Result containing latest WorldSnapshot or None if no snapshots exist
        ...
