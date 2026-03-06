#!/usr/bin/env python3
"""SimulationSanityChecker - World State Consistency Validation.

This module provides the SimulationSanityChecker for validating world state
consistency before and after simulation commits. It detects anomalies that
may indicate bugs in the simulation logic.

Typical usage example:
    >>> from src.contexts.world.application.services import SimulationSanityChecker
    >>> checker = SimulationSanityChecker()
    >>> result = checker.check(world_state)
    >>> if result.is_ok:
    ...     violations = result.value
    ...     for v in violations:
    ...         print(f"{v.severity.value}: {v.message}")

Result Pattern:
    The check() method returns Result[List[SanityViolation], Error] for explicit
    error handling. The legacy check_and_raise() method is deprecated in favor
    of Result pattern.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import structlog

from src.contexts.world.domain.errors import SanityCheckError
from src.core.result import Err, Error, Ok, Result

if TYPE_CHECKING:
    from src.contexts.character.domain.aggregates.character import Character
    from src.contexts.world.domain.aggregates.world_state import WorldState
    from src.contexts.world.domain.entities.faction import Faction
    from src.contexts.world.domain.entities.location import Location

logger = structlog.get_logger()


# Note: SanityCheckError is now imported from src.contexts.world.domain.errors


class Severity(Enum):
    """Severity level of a sanity violation.

    Attributes:
        WARNING: Anomaly detected but simulation can continue.
        ERROR: Critical violation that should block simulation.
    """

    WARNING = "warning"
    ERROR = "error"


@dataclass
class SanityViolation:
    """Represents a single sanity rule violation.

    Attributes:
        rule_name: Identifier for the violated rule.
        severity: How serious the violation is.
        message: Human-readable description of the issue.
        affected_ids: List of entity IDs involved in the violation.
    """

    rule_name: str
    severity: Severity
    message: str
    affected_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary representation.

        Returns:
            Dictionary with all violation fields.
        """
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "affected_ids": self.affected_ids,
        }





class SimulationSanityChecker:
    """Service for validating world state consistency.

    This service checks various invariants and consistency rules for the
    world state, detecting issues that may indicate bugs in simulation
    logic or data corruption.

    Rules checked:
    1. dead_character_has_location: ERROR if deceased character has
       current_location_id set
    2. faction_no_influence_has_territories: WARNING if faction with
       zero influence controls territories
    3. circular_location_hierarchy: ERROR if location parent chain
       contains cycles
    4. orphaned_entities: WARNING if entity references non-existent parent
    5. duplicate_faction_relations: ERROR if faction has duplicate
       relation entries with same target

    Example:
        >>> checker = SimulationSanityChecker()
        >>> violations = checker.check(world)
        >>> errors = [v for v in violations if v.severity == Severity.ERROR]
        >>> if errors:
        ...     checker.check_and_raise(world)  # Will raise
    """

    def __init__(
        self,
        characters: Optional[List["Character"]] = None,
        factions: Optional[List["Faction"]] = None,
        locations: Optional[List["Location"]] = None,
    ) -> None:
        """Initialize the sanity checker with optional entity lists.

        Args:
            characters: List of Character aggregates to check.
            factions: List of Faction entities to check.
            locations: List of Location entities to check.
        """
        self._characters = characters or []
        self._factions = factions or []
        self._locations = locations or []

    def set_entities(
        self,
        characters: Optional[List["Character"]] = None,
        factions: Optional[List["Faction"]] = None,
        locations: Optional[List["Location"]] = None,
    ) -> None:
        """Update entity lists for checking.

        Args:
            characters: List of Character aggregates to check.
            factions: List of Faction entities to check.
            locations: List of Location entities to check.
        """
        if characters is not None:
            self._characters = characters
        if factions is not None:
            self._factions = factions
        if locations is not None:
            self._locations = locations

    def check(
        self, world: Optional["WorldState"] = None
    ) -> Result[List[SanityViolation], Error]:
        """Check all sanity rules and return violations.

        Runs all defined sanity checks against the configured entities
        and returns a list of any violations found.

        Args:
            world: Optional WorldState for context (currently unused).

        Returns:
            Result containing:
            - Ok: List of SanityViolation instances, empty if no issues
            - Err: Error if check execution fails

        Example:
            >>> result = checker.check(world)
            >>> if result.is_ok:
            ...     violations = result.value
            ...     for v in violations:
            ...         print(f"[{v.severity.value}] {v.rule_name}: {v.message}")
        """
        try:
            violations: List[SanityViolation] = []

            # Rule 1: Dead character has location
            violations.extend(self._check_dead_character_has_location())

            # Rule 2: Faction with no influence has territories
            violations.extend(self._check_faction_no_influence_has_territories())

            # Rule 3: Circular location hierarchy
            violations.extend(self._check_circular_location_hierarchy())

            # Rule 4: Orphaned entities
            violations.extend(self._check_orphaned_entities())

            # Rule 5: Duplicate faction relations
            violations.extend(self._check_duplicate_faction_relations())

            if violations:
                logger.warning(
                    "sanity_check_violations_found",
                    total_violations=len(violations),
                    errors=sum(1 for v in violations if v.severity == Severity.ERROR),
                    warnings=sum(
                        1 for v in violations if v.severity == Severity.WARNING
                    ),
                )

            return Ok(violations)
        except Exception as e:
            logger.error("sanity_check_failed", error=str(e))
            return Err(
                SanityCheckError(
                    f"Failed to execute sanity check: {e}",
                )
            )

    def has_error_violations(
        self, world: Optional["WorldState"] = None
    ) -> Result[bool, Error]:
        """Check if any ERROR-level violations exist.

        This is the Result-pattern replacement for check_and_raise().
        Returns True if any ERROR-level violations are found.

        Args:
            world: Optional WorldState for context.

        Returns:
            Result containing:
            - Ok: True if ERROR-level violations exist, False otherwise
            - Err: Error if check execution fails

        Example:
            >>> result = checker.has_error_violations(world)
            >>> if result.is_ok and result.value:
            ...     print("Error-level violations found!")
        """
        check_result = self.check(world)
        if check_result.is_error:
            return check_result  # type: ignore

        violations = check_result.value
        errors = [v for v in violations if v.severity == Severity.ERROR]

        if errors:
            logger.error(
                "sanity_check_errors_found",
                error_count=len(errors),
                rules=[v.rule_name for v in errors],
            )

        return Ok(len(errors) > 0)

    def _check_dead_character_has_location(self) -> List[SanityViolation]:
        """Check that deceased characters don't have current_location_id.

        A deceased character should not have a current location set,
        as they are no longer present in the world.

        Returns:
            List of violations for deceased characters with locations.
        """
        violations: List[SanityViolation] = []

        for character in self._characters:
            if character.is_deceased and character.current_location_id is not None:
                violations.append(
                    SanityViolation(
                        rule_name="dead_character_has_location",
                        severity=Severity.ERROR,
                        message=(
                            f"Deceased character '{character.profile.name}' "
                            f"has current_location_id set to '{character.current_location_id}'"
                        ),
                        affected_ids=[str(character.character_id)],
                    )
                )

        return violations

    def _check_faction_no_influence_has_territories(self) -> List[SanityViolation]:
        """Check that factions with no influence don't control territories.

        A faction with zero influence should not control any territories,
        as this indicates a logical inconsistency in the world state.

        Returns:
            List of violations for zero-influence factions with territories.
        """
        violations: List[SanityViolation] = []

        for faction in self._factions:
            if faction.influence == 0 and faction.territories:
                violations.append(
                    SanityViolation(
                        rule_name="faction_no_influence_has_territories",
                        severity=Severity.WARNING,
                        message=(
                            f"Faction '{faction.name}' has zero influence "
                            f"but controls {len(faction.territories)} territory(ies)"
                        ),
                        affected_ids=[faction.id, *faction.territories],
                    )
                )

        return violations

    def _check_circular_location_hierarchy(self) -> List[SanityViolation]:
        """Check for cycles in location parent hierarchy.

        Location parent chains should never form cycles (A -> B -> A).

        Returns:
            List of violations for locations in cycles.
        """
        violations: List[SanityViolation] = []

        # Build location lookup map
        location_map: Dict[str, "Location"] = {loc.id: loc for loc in self._locations}

        # Track visited locations to detect cycles
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def detect_cycle(location_id: str, path: List[str]) -> Optional[List[str]]:
            """Detect cycle starting from location_id.

            Args:
                location_id: Starting location ID.
                path: Current path of location IDs.

            Returns:
                Cycle path if found, None otherwise.
            """
            if location_id in rec_stack:
                # Found cycle - return the cycle portion
                cycle_start = path.index(location_id)
                return path[cycle_start:] + [location_id]

            if location_id in visited:
                return None

            visited.add(location_id)
            rec_stack.add(location_id)
            path.append(location_id)

            location = location_map.get(location_id)
            if location and location.parent_location_id:
                cycle = detect_cycle(location.parent_location_id, path)
                if cycle:
                    return cycle

            path.pop()
            rec_stack.remove(location_id)
            return None

        # Check each location for cycles
        for location in self._locations:
            if location.id not in visited:
                cycle = detect_cycle(location.id, [])
                if cycle:
                    violations.append(
                        SanityViolation(
                            rule_name="circular_location_hierarchy",
                            severity=Severity.ERROR,
                            message=(
                                f"Circular location hierarchy detected: "
                                f"{' -> '.join(cycle)}"
                            ),
                            affected_ids=list(set(cycle)),
                        )
                    )
                    # Mark all cycle locations as visited to avoid duplicate reports
                    visited.update(cycle)

        return violations

    def _check_orphaned_entities(self) -> List[SanityViolation]:
        """Check for entities referencing non-existent parents.

        Entities should not reference parent IDs that don't exist:
        - Locations with non-existent parent_location_id
        - Characters in non-existent locations

        Returns:
            List of violations for orphaned entities.
        """
        violations: List[SanityViolation] = []

        # Build sets of valid IDs
        location_ids: Set[str] = {loc.id for loc in self._locations}

        # Check locations with non-existent parents
        for location in self._locations:
            if location.parent_location_id:
                if location.parent_location_id not in location_ids:
                    violations.append(
                        SanityViolation(
                            rule_name="orphaned_entities",
                            severity=Severity.WARNING,
                            message=(
                                f"Location '{location.name}' references "
                                f"non-existent parent_location_id '{location.parent_location_id}'"
                            ),
                            affected_ids=[location.id, location.parent_location_id],
                        )
                    )

        # Check characters in non-existent locations
        for character in self._characters:
            if character.current_location_id:
                if character.current_location_id not in location_ids:
                    violations.append(
                        SanityViolation(
                            rule_name="orphaned_entities",
                            severity=Severity.WARNING,
                            message=(
                                f"Character '{character.profile.name}' is in "
                                f"non-existent location '{character.current_location_id}'"
                            ),
                            affected_ids=[
                                str(character.character_id),
                                character.current_location_id,
                            ],
                        )
                    )

        return violations

    def _check_duplicate_faction_relations(self) -> List[SanityViolation]:
        """Check for duplicate faction relation entries.

        A faction should not have multiple relations with the same
        target faction.

        Returns:
            List of violations for factions with duplicate relations.
        """
        violations: List[SanityViolation] = []

        for faction in self._factions:
            seen_targets: Set[str] = set()
            duplicate_targets: Set[str] = set()

            for relation in faction.relations:
                target = relation.target_faction_id
                if target in seen_targets:
                    duplicate_targets.add(target)
                seen_targets.add(target)

            if duplicate_targets:
                violations.append(
                    SanityViolation(
                        rule_name="duplicate_faction_relations",
                        severity=Severity.ERROR,
                        message=(
                            f"Faction '{faction.name}' has duplicate relations "
                            f"with {len(duplicate_targets)} target(s): "
                            f"{', '.join(sorted(duplicate_targets))}"
                        ),
                        affected_ids=[faction.id, *duplicate_targets],
                    )
                )

        return violations
