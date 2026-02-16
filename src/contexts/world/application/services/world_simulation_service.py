#!/usr/bin/env python3
"""WorldSimulationService - Basic Simulation Tick Service.

This module provides the WorldSimulationService for advancing world simulation
and generating faction intents. This is a read-only preview implementation that
does not persist changes to the world state.

The service orchestrates:
1. Calendar advancement
2. Faction intent generation
3. Simulation tick result creation

Typical usage example:
    >>> from src.contexts.world.application.services import WorldSimulationService
    >>> from src.contexts.world.domain.repositories import IWorldStateRepository
    >>> service = WorldSimulationService(world_repo, faction_repo, intent_generator)
    >>> result = service.advance_simulation("world-123", days=7)
    >>> if result.is_ok:
    ...     tick = result.value
    ...     print(f"Advanced {tick.days_advanced} days")
"""

from typing import List, Protocol, runtime_checkable

from src.core.result import Err, Ok, Result
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction, FactionStatus
from src.contexts.world.domain.entities.faction_intent import FactionIntent
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.simulation_tick import SimulationTick

from .faction_intent_generator import FactionIntentGenerator


class SimulationError(Exception):
    """Base exception for simulation errors."""
    pass


class WorldNotFoundError(SimulationError):
    """Raised when the requested world is not found."""
    pass


class InvalidDaysError(SimulationError):
    """Raised when the days parameter is invalid."""
    pass


class RepositoryError(SimulationError):
    """Raised when a repository operation fails."""
    pass


@runtime_checkable
class IWorldStateRepository(Protocol):
    """Protocol for WorldState repository interface.

    Defines the minimal interface needed by WorldSimulationService.
    """

    async def get_by_id(self, world_state_id: str) -> WorldState | None:
        """Retrieve a WorldState by ID.

        Args:
            world_state_id: Unique identifier for the world state

        Returns:
            WorldState if found, None otherwise
        """
        ...


@runtime_checkable
class IFactionRepository(Protocol):
    """Protocol for Faction repository interface.

    Defines the minimal interface needed by WorldSimulationService.
    """

    async def get_by_world_id(self, world_id: str) -> List[Faction]:
        """Retrieve all factions for a world.

        Args:
            world_id: ID of the world to get factions for

        Returns:
            List of Faction entities in the world
        """
        ...


class WorldSimulationService:
    """Service for advancing world simulation.

    This service provides basic simulation functionality including:
    - Calendar advancement (read-only preview)
    - Faction intent generation based on world state
    - Simulation tick result creation

    This is a preview implementation that does NOT apply changes to the world.
    Use commit_simulation (SIM-017) for full simulation with state persistence.

    Attributes:
        MIN_DAYS: Minimum days allowed for simulation (1).
        MAX_DAYS: Maximum days allowed for simulation (365).

    Example:
        >>> service = WorldSimulationService(world_repo, faction_repo, intent_generator)
        >>> result = service.advance_simulation("world-123", days=7)
        >>> if result.is_ok:
        ...     tick = result.value
        ...     print(f"Generated {len(tick.events_generated)} events")
    """

    MIN_DAYS = 1
    MAX_DAYS = 365

    def __init__(
        self,
        world_repo: IWorldStateRepository,
        faction_repo: IFactionRepository,
        intent_generator: FactionIntentGenerator,
    ):
        """Initialize the simulation service.

        Args:
            world_repo: Repository for WorldState aggregates
            faction_repo: Repository for Faction entities
            intent_generator: Service for generating faction intents
        """
        self._world_repo = world_repo
        self._faction_repo = faction_repo
        self._intent_generator = intent_generator

    async def advance_simulation(
        self,
        world_id: str,
        days: int = 1,
    ) -> Result[SimulationTick, Exception]:
        """Advance simulation and generate faction intents (preview only).

        This is a read-only preview that:
        1. Validates the days parameter
        2. Loads the WorldState
        3. Stores calendar state before advancement
        4. Advances the calendar
        5. Loads all factions for the world
        6. Builds DiplomacyMatrix from faction relations
        7. Generates intents for each active faction
        8. Creates a SimulationTick with results (no changes applied)

        No changes are persisted - this is a preview operation.

        Args:
            world_id: ID of the world to simulate
            days: Number of days to advance (1-365)

        Returns:
            Result containing SimulationTick on success, or Exception on failure:
            - WorldNotFoundError: World with given ID not found
            - InvalidDaysError: Days parameter out of valid range
            - RepositoryError: Failed to load data from repository

        Example:
            >>> result = await service.advance_simulation("world-123", days=7)
            >>> if result.is_ok:
            ...     tick = result.value
            ...     print(f"Calendar: {tick.calendar_after.format()}")
            ... else:
            ...     print(f"Error: {result.error}")
        """
        # Step 1: Validate days
        if not self.MIN_DAYS <= days <= self.MAX_DAYS:
            return Err(InvalidDaysError(
                f"Days must be between {self.MIN_DAYS} and {self.MAX_DAYS}, got {days}"
            ))

        # Step 2: Load WorldState
        world = await self._world_repo.get_by_id(world_id)
        if world is None:
            return Err(WorldNotFoundError(f"World not found: {world_id}"))

        # Step 3: Store calendar before
        calendar_before = world.calendar

        # Step 4: Advance calendar (preview - create new calendar without modifying world)
        calendar_result = calendar_before.advance(days)
        if calendar_result.is_error:
            error = calendar_result.error
            if error is not None:
                return Err(error)
            return Err(ValueError("Unknown calendar advancement error"))
        calendar_after = calendar_result.value

        # Step 5: Load all factions for this world
        try:
            factions = await self._faction_repo.get_by_world_id(world_id)
        except Exception as e:
            return Err(RepositoryError(f"Failed to load factions: {e}"))

        # Step 6: Build DiplomacyMatrix from faction relations
        diplomacy = self._build_diplomacy_matrix(world_id, factions)

        # Step 7: Generate intents for each active faction
        all_intents: List[FactionIntent] = []
        for faction in factions:
            # Skip disbanded/inactive factions
            if faction.status == FactionStatus.DISBANDED:
                continue

            intents = self._intent_generator.generate_intents(
                faction=faction,
                world=world,
                diplomacy=diplomacy,
            )
            all_intents.extend(intents)

        # Step 8: Create SimulationTick with results
        tick = SimulationTick(
            world_id=world_id,
            calendar_before=calendar_before,
            calendar_after=calendar_after,
            days_advanced=days,
            events_generated=[],  # No events in preview mode
            resource_changes={},  # No resource changes in preview mode
            diplomacy_changes=[],  # No diplomacy changes in preview mode
            character_reactions=[],  # No character reactions in preview mode
            rumors_created=0,
        )

        return Ok(tick)

    def _build_diplomacy_matrix(
        self,
        world_id: str,
        factions: List[Faction],
    ) -> DiplomacyMatrix:
        """Build a DiplomacyMatrix from faction relations.

        Creates a DiplomacyMatrix aggregate by extracting relations from
        each Faction and converting them to DiplomaticStatus values.

        Args:
            world_id: ID of the world
            factions: List of all factions in the world

        Returns:
            DiplomacyMatrix with all faction relations populated

        Note:
            Relations are converted from FactionRelation.strength to
            DiplomaticStatus using the strength-based mapping rules.
        """
        from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix

        matrix = DiplomacyMatrix(
            world_id=world_id,
            relations={},
            faction_ids=set(),
        )

        # Register all factions first
        for faction in factions:
            matrix.register_faction(faction.id)

        # Extract relations from each faction
        for faction in factions:
            for relation in faction.relations:
                # Convert strength to DiplomaticStatus
                status = DiplomaticStatus.from_relation_strength(relation.strength)

                # Set the relation (skip if already set to avoid duplicates)
                if not matrix.has_relation(faction.id, relation.target_faction_id):
                    matrix.set_status(faction.id, relation.target_faction_id, status)

        return matrix
