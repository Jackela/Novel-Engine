# mypy: ignore-errors

"""World Simulation Service.

Main service implementation for world simulation.
"""

from collections import OrderedDict
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import uuid4

import structlog

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction, FactionStatus
from src.contexts.world.domain.entities.faction_intent import ActionType, FactionIntent
from src.contexts.world.domain.entities.history_event import (
    EventType,
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot
from src.contexts.world.domain.errors import (
    IntentGenerationError,
    RepositoryError,
    SaveFailedError,
    SimulationError,
    WorldNotFoundError,
)
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.simulation_tick import SimulationTick
from src.core.result import Err, Ok, Result

from ..faction_intent_generator import FactionIntentGenerator
from .exceptions import InvalidDaysError, SnapshotFailedError
from .models import ResolutionResult
from .protocols import IFactionRepository, ISnapshotService, IWorldStateRepository

if TYPE_CHECKING:
    from ..rumor_propagation_service import RumorPropagationService
    from ..simulation_sanity_checker import SimulationSanityChecker

logger = structlog.get_logger()


class WorldSimulationService:
    """Service for advancing world simulation.

    This service provides basic simulation functionality including:
    - Calendar advancement (read-only preview)
    - Faction intent generation based on world state
    - Simulation tick result creation
    - Full simulation commit with snapshots and events (SIM-017)

    This is a preview implementation that does NOT apply changes to the world.
    Use commit_simulation (SIM-017) for full simulation with state persistence.

    Attributes:
        MIN_DAYS: Minimum days allowed for simulation (1).
        MAX_DAYS: Maximum days allowed for simulation (365).
        MAX_HISTORY_PER_WORLD: Maximum tick history entries per world (100).

    Example:
        >>> service = WorldSimulationService(world_repo, faction_repo, intent_generator)
        >>> result = service.advance_simulation("world-123", days=7)
        >>> if result.is_ok:
        ...     tick = result.value
        ...     print(f"Generated {len(tick.events_generated)} events")
    """

    MIN_DAYS = 1
    MAX_DAYS = 365
    MAX_HISTORY_PER_WORLD = 100

    def __init__(
        self,
        world_repo: IWorldStateRepository,
        faction_repo: IFactionRepository,
        intent_generator: FactionIntentGenerator,
        snapshot_service: Optional[ISnapshotService] = None,
        rumor_service: Optional["RumorPropagationService"] = None,
        sanity_checker: Optional["SimulationSanityChecker"] = None,
    ) -> None:
        """Initialize the simulation service.

        Args:
            world_repo: Repository for WorldState aggregates
            faction_repo: Repository for Faction entities
            intent_generator: Service for generating faction intents
            snapshot_service: Optional service for managing snapshots (for commit_simulation)
            rumor_service: Optional service for propagating rumors (for commit_simulation)
            sanity_checker: Optional service for validating world state (for commit_simulation)
        """
        self._world_repo = world_repo
        self._faction_repo = faction_repo
        self._intent_generator = intent_generator
        self._snapshot_service = snapshot_service
        self._rumor_service = rumor_service
        self._sanity_checker = sanity_checker

        # Tick history tracking: world_id -> OrderedDict of tick_id -> SimulationTick
        self._tick_history: Dict[str, "OrderedDict[str, SimulationTick]"] = {}

        # Tick number tracking per world
        self._tick_numbers: Dict[str, int] = {}

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
            return Err(
                InvalidDaysError(
                    f"Days must be between {self.MIN_DAYS} and {self.MAX_DAYS}, got {days}"
                )
            )

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

            intents_result = self._intent_generator.generate_intents(
                faction=faction,
                world=world,
                diplomacy=diplomacy,
            )
            if intents_result.is_error:
                error = intents_result.error
                if error is not None:
                    return Err(Exception(error.message))
                return Err(IntentGenerationError("Unknown intent generation error"))
            intent_values = intents_result.value
            if intent_values is not None:
                all_intents.extend(intent_values)

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
            if intent.action_type == ActionType.ATTACK and intent.target_id:
                if intent.target_id not in attack_targets:
                    attack_targets[intent.target_id] = []
                attack_targets[intent.target_id].append(intent)

        # Second pass: resolve each intent
        for intent in sorted_intents:
            faction = faction_map.get(intent.faction_id)
            if faction is None:
                result.mark_intent_failed(intent.id)
                continue

            if intent.action_type == ActionType.ATTACK:
                self._resolve_attack(
                    intent, faction, faction_map, attack_targets, diplomacy, result
                )
            elif intent.action_type == ActionType.EXPAND:
                self._resolve_expand(intent, faction, result)
            elif intent.action_type == ActionType.TRADE:
                self._resolve_trade(intent, faction, faction_map, diplomacy, result)
            elif intent.action_type == ActionType.STABILIZE:
                self._resolve_stabilize(intent, faction, result)
            elif intent.action_type == ActionType.SABOTAGE:
                # SABOTAGE has no immediate effect in current implementation
                result.mark_intent_success(intent.id)

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
            result.mark_intent_failed(intent.id)
            return

        defender = faction_map.get(target_id)
        if defender is None:
            result.mark_intent_failed(intent.id)
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
            if intent.id != strongest.intent_id:
                # This attacker loses the conflict (military loss already applied)
                result.mark_intent_failed(intent.id)
                return

        # Check for territory change
        if attacker.military_strength > defender.military_strength:
            # Attacker wins - transfer one territory if available
            if defender.territories and len(defender.territories) > 0:
                # Take the first territory
                captured_territory = defender.territories[0]
                result.add_territory_change(captured_territory, attacker.id)

        result.mark_intent_success(intent.id)

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
            result.mark_intent_failed(intent.id)
            return

        # Reduce wealth for expansion cost
        result.add_resource_change(faction.id, wealth_delta=-10)

        # Note: Actual territory assignment requires location repository
        # For now, we just record the intent as successful
        result.mark_intent_success(intent.id)

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
            result.mark_intent_failed(intent.id)
            return

        target = faction_map.get(target_id)
        if target is None:
            result.mark_intent_failed(intent.id)
            return

        # Check for conflicting relations
        current_status = diplomacy.get_status(faction.id, target_id)
        if current_status in (DiplomaticStatus.AT_WAR, DiplomaticStatus.HOSTILE):
            result.mark_intent_failed(intent.id)
            return

        # Create alliance
        status_before = current_status or DiplomaticStatus.NEUTRAL
        result.add_diplomacy_change(
            faction.id,
            target_id,
            status_before,
            DiplomaticStatus.ALLIED,
        )

        result.mark_intent_success(intent.id)

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

        result.mark_intent_success(intent.id)

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

        result.mark_intent_success(intent.id)

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
        result.mark_intent_success(intent.id)

    def _resolve_stabilize(
        self,
        intent: FactionIntent,
        faction: Faction,
        result: ResolutionResult,
    ) -> None:
        """Resolve a STABILIZE intent.

        STABILIZE is the canonical action for internal consolidation.
        Combines legacy DEFEND, CONSOLIDATE, RECOVER behaviors:
        - Small wealth gain: +2
        - Small military gain: +1
        - Always succeeds (default fallback intent).

        Args:
            intent: The STABILIZE intent to resolve.
            faction: The stabilizing faction.
            result: ResolutionResult to accumulate changes.
        """
        result.add_resource_change(faction.id, wealth_delta=2, military_delta=1)
        result.mark_intent_success(intent.id)

    def _resolve_trade(
        self,
        intent: FactionIntent,
        faction: Faction,
        faction_map: Dict[str, Faction],
        diplomacy: DiplomacyMatrix,
        result: ResolutionResult,
    ) -> None:
        """Resolve a TRADE intent.

        TRADE is the canonical action for diplomatic/economic exchanges.
        Implements ALLY behavior:
        - Creates bilateral ALLIED status if target exists and relations allow.
        - Fails if target has conflicting relations (AT_WAR or HOSTILE).
        - Fails if target doesn't exist or no target specified.

        Args:
            intent: The TRADE intent to resolve.
            faction: The trading faction.
            faction_map: Lookup dict for all factions.
            diplomacy: Current diplomacy matrix.
            result: ResolutionResult to accumulate changes.
        """
        target_id = intent.target_id
        if not target_id:
            result.mark_intent_failed(intent.id)
            return

        target = faction_map.get(target_id)
        if target is None:
            result.mark_intent_failed(intent.id)
            return

        # Check for conflicting relations
        current_status = diplomacy.get_status(faction.id, target_id)
        if current_status in (DiplomaticStatus.AT_WAR, DiplomaticStatus.HOSTILE):
            result.mark_intent_failed(intent.id)
            return

        # Create alliance (trade/diplomatic relationship)
        status_before = current_status or DiplomaticStatus.NEUTRAL
        result.add_diplomacy_change(
            faction.id,
            target_id,
            status_before,
            DiplomaticStatus.ALLIED,
        )

        result.mark_intent_success(intent.id)

    async def commit_simulation(
        self,
        world_id: str,
        days: int = 1,
    ) -> Result[SimulationTick, Exception]:
        """Commit a simulation tick with full state persistence.

        This method performs a complete simulation commit including:
        1. Validate inputs and create pre-commit snapshot
        2. Run advance_simulation to get preview tick
        3. Resolve intents and apply changes to world state
        4. Generate HistoricalEvents for significant changes
        5. Run sanity checker (warnings logged, not blocking)
        6. Propagate rumors and create rumors from new events
        7. Save world state to repository
        8. Track simulation history

        If any step fails after snapshot creation, attempts rollback.

        Args:
            world_id: ID of the world to simulate
            days: Number of days to advance (1-365)

        Returns:
            Result containing SimulationTick on success, or Exception on failure:
            - WorldNotFoundError: World with given ID not found
            - InvalidDaysError: Days parameter out of valid range
            - SnapshotFailedError: Failed to create pre-commit snapshot
            - SaveFailedError: Failed to save world state
            - RollbackError: Failed to rollback after save failure

        Example:
            >>> result = await service.commit_simulation("world-123", days=7)
            >>> if result.is_ok:
            ...     tick = result.value
            ...     print(f"Committed tick with {len(tick.events_generated)} events")
        """
        # Step 1: Validate days
        if not self.MIN_DAYS <= days <= self.MAX_DAYS:
            return Err(
                InvalidDaysError(
                    f"Days must be between {self.MIN_DAYS} and {self.MAX_DAYS}, got {days}"
                )
            )

        # Step 2: Load WorldState
        world = await self._world_repo.get_by_id(world_id)
        if world is None:
            return Err(WorldNotFoundError(f"World not found: {world_id}"))

        # Step 3: Create pre-commit snapshot (if snapshot service available)
        snapshot: Optional[WorldSnapshot] = None
        if self._snapshot_service is not None:
            tick_number = self._tick_numbers.get(world_id, 0)
            snapshot_result = self._snapshot_service.create_snapshot(
                world_id=world_id,
                tick_number=tick_number,
                description=f"Pre-commit snapshot before {days} day(s) advancement",
            )
            if snapshot_result.is_error:
                error = snapshot_result.error
                logger.error(
                    "simulation_snapshot_failed",
                    world_id=world_id,
                    error=str(error),
                )
                if error is not None:
                    return Err(
                        SnapshotFailedError(f"Failed to create snapshot: {error}")
                    )
                return Err(
                    SnapshotFailedError("Failed to create snapshot: unknown error")
                )
            snapshot = snapshot_result.value
            logger.info(
                "simulation_snapshot_created",
                world_id=world_id,
                snapshot_id=snapshot.snapshot_id,
            )

        # Step 4: Run advance_simulation preview
        preview_result = await self.advance_simulation(world_id, days)
        if preview_result.is_error:
            error = preview_result.error
            if error is not None:
                return Err(error)
            return Err(SimulationError("Unknown preview simulation error"))

        # Step 5: Load factions and build diplomacy
        try:
            factions = await self._faction_repo.get_by_world_id(world_id)
        except Exception as e:
            return Err(RepositoryError(f"Failed to load factions: {e}"))

        diplomacy = self._build_diplomacy_matrix(world_id, factions)

        # Step 6: Generate intents and resolve them
        all_intents: List[FactionIntent] = []
        for faction in factions:
            if faction.status == FactionStatus.DISBANDED:
                continue
            intents_result = self._intent_generator.generate_intents(
                faction=faction,
                world=world,
                diplomacy=diplomacy,
            )
            if intents_result.is_error:
                error = intents_result.error
                if error is not None:
                    return Err(Exception(error.message))
                return Err(IntentGenerationError("Unknown intent generation error"))
            intent_values = intents_result.value
            if intent_values is not None:
                all_intents.extend(intent_values)

        resolution = self._resolve_intents(all_intents, world, factions, diplomacy)

        # Step 7: Apply changes to world and factions
        updated_factions = self._apply_resolution_to_factions(factions, resolution)
        world_advance_result = world.advance_time(days)
        if world_advance_result.is_error:
            error = world_advance_result.error
            if error is not None:
                return Err(error)
            return Err(SimulationError("Failed to advance world time"))

        # Step 8: Generate HistoricalEvents for significant changes
        events = self._generate_events_from_resolution(
            resolution=resolution,
            world=world,
            factions=updated_factions,
        )

        # Step 9: Run sanity checker (warnings logged, not blocking)
        if self._sanity_checker is not None:
            try:
                check_result = self._sanity_checker.check(world)
                if check_result.is_ok and check_result.value:
                    for violation in check_result.value:
                        logger.warning(
                            "simulation_sanity_violation",
                            world_id=world_id,
                            rule_name=violation.rule_name,
                            severity=violation.severity.value,
                            message=violation.message,
                        )
            except Exception as e:
                logger.warning(
                    "simulation_sanity_check_error",
                    world_id=world_id,
                    error=str(e),
                )

        # Step 10: Propagate rumors and create rumors from events
        rumors_created_count = 0
        if self._rumor_service is not None:
            try:
                # Propagate existing rumors
                await self._rumor_service.propagate_rumors(world)

                # Create rumors from new events
                for event in events:
                    try:
                        self._rumor_service.create_rumor_from_event(event, world)
                        rumors_created_count += 1
                    except Exception as e:
                        logger.warning(
                            "simulation_rumor_creation_failed",
                            event_id=event.id,
                            error=str(e),
                        )
            except Exception as e:
                logger.warning(
                    "simulation_rumor_propagation_failed",
                    world_id=world_id,
                    error=str(e),
                )

        # Step 11: Save world state and factions
        try:
            await self._faction_repo.save_all(updated_factions)
            # Note: world_repo.save() would be called here if it existed
            # For now, the world state is updated in-memory only
            logger.info(
                "simulation_committed",
                world_id=world_id,
                days_advanced=days,
                events_count=len(events),
                rumors_created=rumors_created_count,
            )
        except Exception as e:
            logger.error(
                "simulation_save_failed",
                world_id=world_id,
                error=str(e),
            )
            # Attempt rollback if snapshot exists
            if snapshot is not None and self._snapshot_service is not None:
                try:
                    restore_result = self._snapshot_service.restore_snapshot(
                        snapshot.snapshot_id
                    )
                    if restore_result.is_ok:
                        logger.info(
                            "simulation_rollback_success",
                            world_id=world_id,
                            snapshot_id=snapshot.snapshot_id,
                        )
                    else:
                        logger.error(
                            "simulation_rollback_failed",
                            world_id=world_id,
                            snapshot_id=snapshot.snapshot_id,
                        )
                except Exception as rollback_error:
                    logger.error(
                        "simulation_rollback_exception",
                        world_id=world_id,
                        error=str(rollback_error),
                    )
            return Err(SaveFailedError(f"Failed to save world state: {e}"))

        # Step 12: Create final SimulationTick with complete data
        preview_tick = preview_result.value
        if preview_tick is None:
            return Err(SimulationError("Preview tick was unexpectedly None"))

        tick = SimulationTick(
            world_id=world_id,
            calendar_before=preview_tick.calendar_before,
            calendar_after=world.calendar,
            days_advanced=days,
            events_generated=[e.id for e in events],
            resource_changes=resolution.resource_changes,
            diplomacy_changes=resolution.diplomacy_changes,
            character_reactions=[],  # Character reactions handled separately
            rumors_created=rumors_created_count,
        )

        # Step 13: Track simulation history
        self._add_to_history(world_id, tick)

        # Update tick number for next run
        self._tick_numbers[world_id] = self._tick_numbers.get(world_id, 0) + 1

        return Ok(tick)

    def _apply_resolution_to_factions(
        self,
        factions: List[Faction],
        resolution: ResolutionResult,
    ) -> List[Faction]:
        """Apply resolution changes to faction entities.

        Creates updated copies of factions with resource changes applied.
        Territory changes are recorded but actual location assignment
        requires location repository.

        Args:
            factions: List of current Faction entities
            resolution: ResolutionResult with changes to apply

        Returns:
            List of updated Faction entities
        """
        updated_factions: List[Faction] = []

        for faction in factions:
            # Check if this faction has resource changes
            if faction.id in resolution.resource_changes:
                changes = resolution.resource_changes[faction.id]
                # Apply resource changes (clamped to valid ranges)
                new_economic_power = max(
                    0,
                    min(100, faction.economic_power + changes.wealth_delta),
                )
                new_military_strength = max(
                    0,
                    min(100, faction.military_strength + changes.military_delta),
                )
                new_influence = max(
                    0,
                    min(100, faction.influence + changes.influence_delta),
                )

                # Create updated faction using copy with modifications
                faction = Faction(
                    id=faction.id,
                    name=faction.name,
                    description=faction.description,
                    faction_type=faction.faction_type,
                    alignment=faction.alignment,
                    status=faction.status,
                    headquarters_id=faction.headquarters_id,
                    leader_name=faction.leader_name,
                    leader_id=faction.leader_id,
                    founding_date=faction.founding_date,
                    values=faction.values.copy() if faction.values else [],
                    goals=faction.goals.copy() if faction.goals else [],
                    resources=faction.resources.copy() if faction.resources else [],
                    economic_power=new_economic_power,
                    military_strength=new_military_strength,
                    influence=new_influence,
                    territories=faction.territories.copy(),
                    relations=faction.relations.copy(),
                    member_count=faction.member_count,
                    secrets=faction.secrets.copy() if faction.secrets else [],
                    created_at=faction.created_at,
                    updated_at=datetime.now(),
                )

            # Check if this faction has territory changes (gained)
            for location_id, new_owner_id in resolution.territory_changes.items():
                if (
                    new_owner_id == faction.id
                    and location_id not in faction.territories
                ):
                    faction.territories.append(location_id)
                # Handle territory loss
                if new_owner_id != faction.id and location_id in faction.territories:
                    faction.territories.remove(location_id)

            updated_factions.append(faction)

        return updated_factions

    def _generate_events_from_resolution(
        self,
        resolution: ResolutionResult,
        world: WorldState,
        factions: List[Faction],
    ) -> List[HistoryEvent]:
        """Generate HistoricalEvents from significant resolution changes.

        Creates events for:
        - WAR: ATTACK intents that resulted in territory change
        - ALLIANCE: ALLY intents that succeeded
        - POLITICAL: Faction status changes

        Args:
            resolution: ResolutionResult with changes
            world: Current WorldState
            factions: List of updated factions

        Returns:
            List of generated HistoryEvent entities
        """
        events: List[HistoryEvent] = []
        faction_map = {f.id: f for f in factions}

        # Generate WAR events for territory changes
        for location_id, new_owner_id in resolution.territory_changes.items():
            attacker = faction_map.get(new_owner_id)
            if attacker:
                event = HistoryEvent(
                    id=str(uuid4()),
                    name=f"Territory Conflict: {attacker.name}",
                    description=f"{attacker.name} captured territory at {location_id}",
                    event_type=EventType.WAR,
                    impact_scope=ImpactScope.REGIONAL,
                    date_description=world.calendar.format(),
                    faction_ids=[new_owner_id],
                    location_ids=[location_id],
                    affected_faction_ids=[new_owner_id],
                    affected_location_ids=[location_id],
                    key_figures=[attacker.name],
                )
                events.append(event)
                resolution.events_generated.append(event.id)

        # Generate ALLIANCE events for successful alliances
        for diplo_change in resolution.diplomacy_changes:
            if diplo_change.status_after == DiplomaticStatus.ALLIED:
                faction_a = faction_map.get(diplo_change.faction_a)
                faction_b = faction_map.get(diplo_change.faction_b)

                if faction_a and faction_b:
                    event = HistoryEvent(
                        id=str(uuid4()),
                        name=f"Alliance Formed: {faction_a.name} and {faction_b.name}",
                        description=(
                            f"{faction_a.name} and {faction_b.name} have formed "
                            f"a formal alliance, strengthening their diplomatic ties."
                        ),
                        event_type=EventType.ALLIANCE,
                        impact_scope=ImpactScope.REGIONAL,
                        date_description=world.calendar.format(),
                        faction_ids=[faction_a.id, faction_b.id],
                        affected_faction_ids=[faction_a.id, faction_b.id],
                        key_figures=[faction_a.name, faction_b.name],
                    )
                    events.append(event)
                    resolution.events_generated.append(event.id)

        logger.info(
            "simulation_events_generated",
            world_id=world.id,
            event_count=len(events),
            event_types=[e.event_type.value for e in events],
        )

        return events

    def _add_to_history(self, world_id: str, tick: SimulationTick) -> None:
        """Add a tick to simulation history.

        Maintains a maximum of MAX_HISTORY_PER_WORLD entries per world
        using FIFO eviction.

        Args:
            world_id: ID of the world
            tick: SimulationTick to add to history
        """
        if world_id not in self._tick_history:
            self._tick_history[world_id] = OrderedDict()

        history = self._tick_history[world_id]

        # Add new tick
        history[tick.tick_id] = tick

        # Enforce max size with FIFO eviction
        while len(history) > self.MAX_HISTORY_PER_WORLD:
            # Remove oldest entry
            oldest_key = next(iter(history))
            del history[oldest_key]

    def get_tick_history(self, world_id: str, limit: int = 20) -> List[SimulationTick]:
        """Get simulation tick history for a world.

        Args:
            world_id: ID of the world
            limit: Maximum number of ticks to return (default 20)

        Returns:
            List of SimulationTick entities, most recent first
        """
        if world_id not in self._tick_history:
            return []

        history = self._tick_history[world_id]
        # Return most recent first
        ticks = list(history.values())
        return ticks[-limit:][::-1]

    def get_tick_by_id(self, world_id: str, tick_id: str) -> Optional[SimulationTick]:
        """Get a specific tick by ID.

        Args:
            world_id: ID of the world
            tick_id: ID of the tick to retrieve

        Returns:
            SimulationTick if found, None otherwise
        """
        if world_id not in self._tick_history:
            return None

        return self._tick_history[world_id].get(tick_id)

    def clear_history(self, world_id: str) -> int:
        """Clear simulation history for a world.

        Args:
            world_id: ID of the world

        Returns:
            Number of entries cleared
        """
        if world_id not in self._tick_history:
            return 0

        count = len(self._tick_history[world_id])
        del self._tick_history[world_id]
        return count
