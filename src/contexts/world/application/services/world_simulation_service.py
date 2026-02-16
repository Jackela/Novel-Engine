#!/usr/bin/env python3
"""WorldSimulationService - Basic Simulation Tick Service.

This module provides the WorldSimulationService for advancing world simulation
and generating faction intents. This is a read-only preview implementation that
does not persist changes to the world state.

The service orchestrates:
1. Calendar advancement
2. Faction intent generation
3. Intent resolution (SIM-016)
4. Simulation tick result creation

Typical usage example:
    >>> from src.contexts.world.application.services import WorldSimulationService
    >>> from src.contexts.world.domain.repositories import IWorldStateRepository
    >>> service = WorldSimulationService(world_repo, faction_repo, intent_generator)
    >>> result = service.advance_simulation("world-123", days=7)
    >>> if result.is_ok:
    ...     tick = result.value
    ...     print(f"Advanced {tick.days_advanced} days")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, runtime_checkable

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction, FactionStatus
from src.contexts.world.domain.entities.faction_intent import FactionIntent, IntentType
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.simulation_tick import (
    DiplomacyChange,
    ResourceChanges,
    SimulationTick,
)
from src.core.result import Err, Ok, Result

from .faction_intent_generator import FactionIntentGenerator


@dataclass
class ResolutionResult:
    """Result of resolving faction intents.

    Contains all changes that should be applied to the world state
    after intent resolution. This is a mutable dataclass that accumulates
    changes during the resolution process.

    Attributes:
        resource_changes: Dict mapping faction_id to ResourceChanges.
        diplomacy_changes: List of DiplomacyChange records.
        territory_changes: Dict mapping location_id to new owner faction_id.
        events_generated: List of event IDs for significant changes.
        successful_intents: List of intent IDs that were successfully resolved.
        failed_intents: List of intent IDs that failed to resolve.
    """

    resource_changes: Dict[str, ResourceChanges] = field(default_factory=dict)
    diplomacy_changes: List[DiplomacyChange] = field(default_factory=list)
    territory_changes: Dict[str, str] = field(default_factory=dict)
    events_generated: List[str] = field(default_factory=list)
    successful_intents: List[str] = field(default_factory=list)
    failed_intents: List[str] = field(default_factory=list)

    def add_resource_change(
        self,
        faction_id: str,
        wealth_delta: int = 0,
        military_delta: int = 0,
        influence_delta: int = 0,
    ) -> None:
        """Add or accumulate resource changes for a faction.

        Args:
            faction_id: ID of the faction to modify.
            wealth_delta: Change in wealth (-100 to 100).
            military_delta: Change in military (-100 to 100).
            influence_delta: Change in influence (-100 to 100).
        """
        if faction_id not in self.resource_changes:
            self.resource_changes[faction_id] = ResourceChanges()

        # Create new ResourceChanges with accumulated values
        existing = self.resource_changes[faction_id]
        new_wealth = max(-100, min(100, existing.wealth_delta + wealth_delta))
        new_military = max(-100, min(100, existing.military_delta + military_delta))
        new_influence = max(-100, min(100, existing.influence_delta + influence_delta))

        self.resource_changes[faction_id] = ResourceChanges(
            wealth_delta=new_wealth,
            military_delta=new_military,
            influence_delta=new_influence,
        )

    def add_diplomacy_change(
        self,
        faction_a: str,
        faction_b: str,
        status_before: DiplomaticStatus,
        status_after: DiplomaticStatus,
    ) -> None:
        """Add a diplomacy change record.

        Args:
            faction_a: First faction ID.
            faction_b: Second faction ID.
            status_before: Status before the change.
            status_after: Status after the change.
        """
        self.diplomacy_changes.append(
            DiplomacyChange(
                faction_a=faction_a,
                faction_b=faction_b,
                status_before=status_before,
                status_after=status_after,
            )
        )

    def add_territory_change(self, location_id: str, new_owner_id: str) -> None:
        """Record a territory ownership change.

        Args:
            location_id: ID of the location changing hands.
            new_owner_id: ID of the new owning faction.
        """
        self.territory_changes[location_id] = new_owner_id

    def mark_intent_success(self, intent_id: str) -> None:
        """Mark an intent as successfully resolved.

        Args:
            intent_id: ID of the successful intent.
        """
        self.successful_intents.append(intent_id)

    def mark_intent_failed(self, intent_id: str) -> None:
        """Mark an intent as failed to resolve.

        Args:
            intent_id: ID of the failed intent.
        """
        self.failed_intents.append(intent_id)

    def has_changes(self) -> bool:
        """Check if any changes were recorded.

        Returns:
            True if any resource, diplomacy, or territory changes exist.
        """
        return bool(
            self.resource_changes
            or self.diplomacy_changes
            or self.territory_changes
            or self.events_generated
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all resolution results.
        """
        return {
            "resource_changes": {
                k: v.to_dict() for k, v in self.resource_changes.items()
            },
            "diplomacy_changes": [dc.to_dict() for dc in self.diplomacy_changes],
            "territory_changes": self.territory_changes,
            "events_generated": self.events_generated,
            "successful_intents": self.successful_intents,
            "failed_intents": self.failed_intents,
            "has_changes": self.has_changes(),
        }


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
        from src.contexts.world.domain.aggregates.diplomacy_matrix import (
            DiplomacyMatrix,
        )

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

    def _resolve_intents(
        self,
        intents: List[FactionIntent],
        world: WorldState,
        factions: List[Faction],
        diplomacy: DiplomacyMatrix,
    ) -> ResolutionResult:
        """Resolve faction intents and compute resulting changes.

        Processes all intents according to resolution rules and calculates
        the resource, diplomacy, and territory changes that would result.

        Resolution rules (evaluated per intent type):
        - ATTACK: Reduces attacker and defender military (-5 each), may
            change territory ownership if attacker is stronger.
        - EXPAND: Requires wealth >= 20, reduces wealth by 10, adds territory.
        - ALLY: Creates bilateral ALLIED status if target accepts.
        - RECOVER: Increases wealth by +5 if below 50.
        - DEFEND: Increases military by +3 if below 80.
        - CONSOLIDATE: Small wealth +2, military +1.
        - TRADE: No immediate effect (future: creates trade route).

        Conflict handling:
        - Two factions attacking same target: strongest attacker wins.
        - Target of ALLY has conflicting relations: alliance fails.

        Args:
            intents: List of FactionIntent entities to resolve.
            world: Current WorldState aggregate.
            factions: List of all Faction entities in the world.
            diplomacy: Current DiplomacyMatrix.

        Returns:
            ResolutionResult containing all computed changes.

        Example:
            >>> result = service._resolve_intents(intents, world, factions, diplomacy)
            >>> if result.has_changes():
            ...     print(f"Resource changes: {len(result.resource_changes)}")
        """
        result = ResolutionResult()

        # Build faction lookup for quick access
        faction_map: Dict[str, Faction] = {f.id: f for f in factions}

        # Track conflicts: target_id -> list of attacking intents
        attack_targets: Dict[str, List[FactionIntent]] = {}

        # Sort intents by priority (descending) for conflict resolution
        sorted_intents = sorted(intents, key=lambda i: i.priority, reverse=True)

        # First pass: collect attacks for conflict detection
        for intent in sorted_intents:
            if intent.intent_type == IntentType.ATTACK and intent.target_id:
                if intent.target_id not in attack_targets:
                    attack_targets[intent.target_id] = []
                attack_targets[intent.target_id].append(intent)

        # Second pass: resolve each intent
        for intent in sorted_intents:
            faction = faction_map.get(intent.faction_id)
            if faction is None:
                result.mark_intent_failed(intent.intent_id)
                continue

            if intent.intent_type == IntentType.ATTACK:
                self._resolve_attack(
                    intent, faction, faction_map, attack_targets, diplomacy, result
                )
            elif intent.intent_type == IntentType.EXPAND:
                self._resolve_expand(intent, faction, result)
            elif intent.intent_type == IntentType.ALLY:
                self._resolve_ally(intent, faction, faction_map, diplomacy, result)
            elif intent.intent_type == IntentType.RECOVER:
                self._resolve_recover(intent, faction, result)
            elif intent.intent_type == IntentType.DEFEND:
                self._resolve_defend(intent, faction, result)
            elif intent.intent_type == IntentType.CONSOLIDATE:
                self._resolve_consolidate(intent, faction, result)
            elif intent.intent_type == IntentType.TRADE:
                # TRADE has no immediate effect in current implementation
                result.mark_intent_success(intent.intent_id)

        return result

    def _resolve_attack(
        self,
        intent: FactionIntent,
        attacker: Faction,
        faction_map: Dict[str, Faction],
        attack_targets: Dict[str, List[FactionIntent]],
        diplomacy: DiplomacyMatrix,
        result: ResolutionResult,
    ) -> None:
        """Resolve an ATTACK intent.

        Rules:
        - Both attacker and defender lose 5 military strength.
        - If multiple attackers target same faction, only the strongest succeeds.
        - Territory change occurs if attacker military > defender military.

        Args:
            intent: The ATTACK intent to resolve.
            attacker: The attacking faction.
            faction_map: Lookup dict for all factions.
            attack_targets: Dict tracking all attacks by target.
            diplomacy: Current diplomacy matrix.
            result: ResolutionResult to accumulate changes.
        """
        target_id = intent.target_id
        if not target_id:
            result.mark_intent_failed(intent.intent_id)
            return

        defender = faction_map.get(target_id)
        if defender is None:
            result.mark_intent_failed(intent.intent_id)
            return

        # Apply military losses to both sides (happens even for conflict losers)
        result.add_resource_change(attacker.id, military_delta=-5)
        result.add_resource_change(defender.id, military_delta=-5)

        # Check for conflict: multiple attackers
        attacks_on_target = attack_targets.get(target_id, [])
        if len(attacks_on_target) > 1:
            # Find the strongest attacker by military strength
            # Use 0 as default for unknown factions
            def get_military_strength(intent: FactionIntent) -> int:
                faction = faction_map.get(intent.faction_id)
                return faction.military_strength if faction is not None else 0

            strongest = max(attacks_on_target, key=get_military_strength)
            if intent.intent_id != strongest.intent_id:
                # This attacker loses the conflict (military loss already applied)
                result.mark_intent_failed(intent.intent_id)
                return

        # Check for territory change
        if attacker.military_strength > defender.military_strength:
            # Attacker wins - transfer one territory if available
            if defender.territories and len(defender.territories) > 0:
                # Take the first territory
                captured_territory = defender.territories[0]
                result.add_territory_change(captured_territory, attacker.id)

        result.mark_intent_success(intent.intent_id)

    def _resolve_expand(
        self,
        intent: FactionIntent,
        faction: Faction,
        result: ResolutionResult,
    ) -> None:
        """Resolve an EXPAND intent.

        Rules:
        - Requires economic_power >= 20.
        - Reduces economic_power by 10.
        - Territory expansion is recorded (actual location assignment
          requires location repository, not implemented in this service).

        Args:
            intent: The EXPAND intent to resolve.
            faction: The expanding faction.
            result: ResolutionResult to accumulate changes.
        """
        # Check wealth requirement
        if faction.economic_power < 20:
            result.mark_intent_failed(intent.intent_id)
            return

        # Reduce wealth for expansion cost
        result.add_resource_change(faction.id, wealth_delta=-10)

        # Note: Actual territory assignment requires location repository
        # For now, we just record the intent as successful
        result.mark_intent_success(intent.intent_id)

    def _resolve_ally(
        self,
        intent: FactionIntent,
        faction: Faction,
        faction_map: Dict[str, Faction],
        diplomacy: DiplomacyMatrix,
        result: ResolutionResult,
    ) -> None:
        """Resolve an ALLY intent.

        Rules:
        - Creates bilateral ALLIED status.
        - Fails if target has conflicting relations (AT_WAR or HOSTILE with requester).
        - Fails if target doesn't exist.

        Args:
            intent: The ALLY intent to resolve.
            faction: The faction seeking alliance.
            faction_map: Lookup dict for all factions.
            diplomacy: Current diplomacy matrix.
            result: ResolutionResult to accumulate changes.
        """
        target_id = intent.target_id
        if not target_id:
            result.mark_intent_failed(intent.intent_id)
            return

        target = faction_map.get(target_id)
        if target is None:
            result.mark_intent_failed(intent.intent_id)
            return

        # Check for conflicting relations
        current_status = diplomacy.get_status(faction.id, target_id)
        if current_status in (DiplomaticStatus.AT_WAR, DiplomaticStatus.HOSTILE):
            result.mark_intent_failed(intent.intent_id)
            return

        # Create alliance
        status_before = current_status or DiplomaticStatus.NEUTRAL
        result.add_diplomacy_change(
            faction.id,
            target_id,
            status_before,
            DiplomaticStatus.ALLIED,
        )

        result.mark_intent_success(intent.intent_id)

    def _resolve_recover(
        self,
        intent: FactionIntent,
        faction: Faction,
        result: ResolutionResult,
    ) -> None:
        """Resolve a RECOVER intent.

        Rules:
        - Increases economic_power by +5 if below 50.
        - No effect if economic_power is already >= 50.

        Args:
            intent: The RECOVER intent to resolve.
            faction: The recovering faction.
            result: ResolutionResult to accumulate changes.
        """
        if faction.economic_power < 50:
            result.add_resource_change(faction.id, wealth_delta=5)

        result.mark_intent_success(intent.intent_id)

    def _resolve_defend(
        self,
        intent: FactionIntent,
        faction: Faction,
        result: ResolutionResult,
    ) -> None:
        """Resolve a DEFEND intent.

        Rules:
        - Increases military_strength by +3 if below 80.
        - No effect if military_strength is already >= 80.

        Args:
            intent: The DEFEND intent to resolve.
            faction: The defending faction.
            result: ResolutionResult to accumulate changes.
        """
        if faction.military_strength < 80:
            result.add_resource_change(faction.id, military_delta=3)

        result.mark_intent_success(intent.intent_id)

    def _resolve_consolidate(
        self,
        intent: FactionIntent,
        faction: Faction,
        result: ResolutionResult,
    ) -> None:
        """Resolve a CONSOLIDATE intent.

        Rules:
        - Small wealth gain: +2.
        - Small military gain: +1.
        - Always succeeds (default fallback intent).

        Args:
            intent: The CONSOLIDATE intent to resolve.
            faction: The consolidating faction.
            result: ResolutionResult to accumulate changes.
        """
        result.add_resource_change(faction.id, wealth_delta=2, military_delta=1)
        result.mark_intent_success(intent.intent_id)
