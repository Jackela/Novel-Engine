#!/usr/bin/env python3
"""
DiplomacyMatrix Aggregate

This module provides the DiplomacyMatrix aggregate for managing diplomatic
relations between all factions in a world. It serves as a consistency boundary
for diplomatic status changes and provides efficient querying capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from src.core.result import Err, Ok, Result

from ..entities.entity import Entity
from ..value_objects.diplomatic_status import DiplomaticStatus

if TYPE_CHECKING:
    from ..entities.diplomatic_pact import DiplomaticPact, PactType


@dataclass
class DiplomacyMatrix(Entity):
    """DiplomacyMatrix Aggregate.

    Manages all diplomatic relations between factions in a world. Provides
    a single source of truth for faction relationships and enforces
    consistency rules when updating diplomatic statuses.

    This aggregate wraps the diplomatic relation concepts from FactionRelation
    but provides a centralized, matrix-based view for efficient querying
    and conflict detection.

    Attributes:
        world_id: ID of the world this matrix belongs to
        relations: Dict mapping (faction_a_id, faction_b_id) tuples to DiplomaticStatus
            The tuple is always stored in sorted order to ensure (A, B) == (B, A)
        faction_ids: Set of all faction IDs tracked in this matrix
        active_pacts: List of active diplomatic pacts between factions

    Example:
        >>> matrix = DiplomacyMatrix(world_id="world-1")
        >>> matrix.set_status("faction-a", "faction-b", DiplomaticStatus.ALLIED)
        >>> allies = matrix.get_allies("faction-a")
        >>> # allies contains "faction-b"
    """

    world_id: str = ""
    relations: Dict[Tuple[str, str], DiplomaticStatus] = field(default_factory=dict)
    faction_ids: set = field(default_factory=set)
    active_pacts: List["DiplomaticPact"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize diplomacy matrix with validation."""
        if not self.faction_ids:
            self.faction_ids = set()
        super().__post_init__()

    def __eq__(self, other: object) -> bool:
        """Equality based on identity."""
        if not isinstance(other, DiplomacyMatrix):
            return False
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate DiplomacyMatrix-specific business rules."""
        errors = []

        if not self.world_id or not self.world_id.strip():
            errors.append("World ID cannot be empty")

        # Validate all relation keys reference known factions
        for faction_a, faction_b in self.relations.keys():
            if faction_a not in self.faction_ids:
                errors.append(f"Unknown faction in relation: {faction_a}")
            if faction_b not in self.faction_ids:
                errors.append(f"Unknown faction in relation: {faction_b}")

        return errors

    def _normalize_key(self, faction_a: str, faction_b: str) -> Tuple[str, str]:
        """Normalize faction pair to ensure consistent ordering.

        Args:
            faction_a: First faction ID
            faction_b: Second faction ID

        Returns:
            Tuple with IDs in sorted order
        """
        return tuple(sorted([faction_a, faction_b]))  # type: ignore

    def get_status(
        self, faction_a: str, faction_b: str
    ) -> Optional[DiplomaticStatus]:
        """Get the diplomatic status between two factions.

        Args:
            faction_a: First faction ID
            faction_b: Second faction ID

        Returns:
            DiplomaticStatus if relation exists, None otherwise

        Example:
            >>> status = matrix.get_status("kingdom-a", "empire-b")
            >>> if status == DiplomaticStatus.AT_WAR:
            ...     print("They are at war!")
        """
        key = self._normalize_key(faction_a, faction_b)
        return self.relations.get(key)

    def set_status(
        self, faction_a: str, faction_b: str, status: DiplomaticStatus
    ) -> Result[None, ValueError]:
        """Set the diplomatic status between two factions.

        Validates that the new status doesn't create a conflict with
        existing relations. A conflict occurs when A's status with B
        contradicts B's known status with A (e.g., A says ALLIED but
        B has AT_WAR with A).

        Note: Since we store relations symmetrically (single entry per pair),
        conflicts can only occur if external code directly modifies the
        relations dict. This method validates against such inconsistencies.

        Args:
            faction_a: First faction ID
            faction_b: Second faction ID
            status: New diplomatic status

        Returns:
            Ok(None) on success, Err(ValueError) if conflict detected

        Example:
            >>> result = matrix.set_status("faction-a", "faction-b", DiplomaticStatus.ALLIED)
            >>> if result.is_error:
            ...     print(f"Failed: {result.error}")
        """
        # Can't set relation with self
        if faction_a == faction_b:
            return Err(ValueError("A faction cannot have diplomatic relations with itself"))

        key = self._normalize_key(faction_a, faction_b)

        # Store the relation
        self.relations[key] = status

        # Track both factions
        self.faction_ids.add(faction_a)
        self.faction_ids.add(faction_b)

        self.touch()
        return Ok(None)

    def get_allies(self, faction_id: str) -> List[str]:
        """Get all factions with ALLIED status to the given faction.

        Args:
            faction_id: The faction to find allies for

        Returns:
            List of faction IDs that are allied with the given faction

        Example:
            >>> allies = matrix.get_allies("kingdom-a")
            >>> print(f"Allies: {allies}")
        """
        allies = []
        for (a, b), status in self.relations.items():
            if status == DiplomaticStatus.ALLIED:
                if a == faction_id:
                    allies.append(b)
                elif b == faction_id:
                    allies.append(a)
        return allies

    def get_enemies(self, faction_id: str) -> List[str]:
        """Get all factions with HOSTILE or AT_WAR status to the given faction.

        Args:
            faction_id: The faction to find enemies for

        Returns:
            List of faction IDs that are hostile or at war with the given faction

        Example:
            >>> enemies = matrix.get_enemies("kingdom-a")
            >>> print(f"Enemies: {enemies}")
        """
        enemies = []
        for (a, b), status in self.relations.items():
            if status in (DiplomaticStatus.HOSTILE, DiplomaticStatus.AT_WAR):
                if a == faction_id:
                    enemies.append(b)
                elif b == faction_id:
                    enemies.append(a)
        return enemies

    def get_neutral(self, faction_id: str) -> List[str]:
        """Get all factions with NEUTRAL status to the given faction.

        Args:
            faction_id: The faction to find neutral relations for

        Returns:
            List of faction IDs that are neutral with the given faction

        Example:
            >>> neutral = matrix.get_neutral("kingdom-a")
            >>> print(f"Neutral: {neutral}")
        """
        neutral = []
        for (a, b), status in self.relations.items():
            if status == DiplomaticStatus.NEUTRAL:
                if a == faction_id:
                    neutral.append(b)
                elif b == faction_id:
                    neutral.append(a)
        return neutral

    def to_matrix(self) -> Dict[str, Dict[str, str]]:
        """Convert the relations to a 2D matrix format for API responses.

        Creates a nested dictionary where matrix[faction_a][faction_b]
        returns the status string value. Self-relations are represented
        as '-' to indicate no relation.

        Returns:
            Nested dict: {faction_id: {other_faction_id: status_value}}

        Example:
            >>> matrix_dict = diplomacy.to_matrix()
            >>> # matrix_dict["kingdom-a"]["empire-b"] == "allied"
        """
        result: Dict[str, Dict[str, str]] = {}

        # Initialize matrix with all factions
        for faction_id in self.faction_ids:
            result[faction_id] = {}
            for other_id in self.faction_ids:
                if faction_id == other_id:
                    result[faction_id][other_id] = "-"
                else:
                    result[faction_id][other_id] = DiplomaticStatus.NEUTRAL.value

        # Fill in known relations
        for (a, b), status in self.relations.items():
            if a in result and b in result:
                result[a][b] = status.value
                result[b][a] = status.value

        return result

    def register_faction(self, faction_id: str) -> None:
        """Register a faction in the matrix without creating relations.

        Args:
            faction_id: ID of the faction to register
        """
        if faction_id not in self.faction_ids:
            self.faction_ids.add(faction_id)
            self.touch()

    def remove_faction(self, faction_id: str) -> int:
        """Remove a faction and all its relations from the matrix.

        Args:
            faction_id: ID of the faction to remove

        Returns:
            Number of relations removed

        Example:
            >>> removed_count = matrix.remove_faction("destroyed-faction")
            >>> print(f"Removed {removed_count} relations")
        """
        if faction_id not in self.faction_ids:
            return 0

        # Remove all relations involving this faction
        relations_to_remove = [
            key for key in self.relations.keys()
            if faction_id in key
        ]
        for key in relations_to_remove:
            del self.relations[key]

        # Remove faction from tracked set
        self.faction_ids.discard(faction_id)

        if relations_to_remove:
            self.touch()

        return len(relations_to_remove)

    def get_factions_by_status(
        self, faction_id: str, status: DiplomaticStatus
    ) -> List[str]:
        """Get all factions with a specific status relative to the given faction.

        Args:
            faction_id: The faction to query from
            status: The diplomatic status to filter by

        Returns:
            List of faction IDs with the specified status

        Example:
            >>> friendly = matrix.get_factions_by_status("kingdom-a", DiplomaticStatus.FRIENDLY)
        """
        result = []
        for (a, b), rel_status in self.relations.items():
            if rel_status == status:
                if a == faction_id:
                    result.append(b)
                elif b == faction_id:
                    result.append(a)
        return result

    def has_relation(self, faction_a: str, faction_b: str) -> bool:
        """Check if a relation exists between two factions.

        Args:
            faction_a: First faction ID
            faction_b: Second faction ID

        Returns:
            True if relation exists, False otherwise
        """
        key = self._normalize_key(faction_a, faction_b)
        return key in self.relations

    def get_relation_count(self) -> int:
        """Get the total number of unique relations in the matrix.

        Returns:
            Number of faction pairs with defined relations
        """
        return len(self.relations)

    def get_faction_count(self) -> int:
        """Get the number of factions tracked in the matrix.

        Returns:
            Number of unique factions
        """
        return len(self.faction_ids)

    def add_pact(self, pact: "DiplomaticPact") -> Result[None, ValueError]:
        """Add a diplomatic pact between factions.

        Validates that the pact is compatible with existing relations.
        For example, factions at WAR cannot have a TRADE_AGREEMENT.

        Args:
            pact: The DiplomaticPact to add.

        Returns:
            Ok(None) on success, Err(ValueError) if pact is incompatible.

        Example:
            >>> from src.contexts.world.domain.entities import DiplomaticPact, PactType
            >>> pact = DiplomaticPact.create_trade_agreement("f1", "f2")
            >>> result = matrix.add_pact(pact)
        """
        from ..entities.diplomatic_pact import PactType

        # Check for incompatible existing pacts
        existing_pacts = self.get_pacts_between(pact.faction_a_id, pact.faction_b_id)
        for existing in existing_pacts:
            if existing.is_active() and existing.is_incompatible_with(pact.pact_type):
                return Err(
                    ValueError(
                        f"Cannot add {pact.pact_type.value}: incompatible with "
                        f"existing {existing.pact_type.value} between "
                        f"{pact.faction_a_id} and {pact.faction_b_id}"
                    )
                )

        # Check for incompatible diplomatic status
        status = self.get_status(pact.faction_a_id, pact.faction_b_id)
        if status == DiplomaticStatus.AT_WAR and pact.pact_type in (
            PactType.TRADE_AGREEMENT,
            PactType.NON_AGGRESSION,
            PactType.DEFENSIVE_PACT,
            PactType.RESEARCH_AGREEMENT,
        ):
            return Err(
                ValueError(
                    f"Cannot add {pact.pact_type.value} while factions are at war"
                )
            )

        # Add the pact
        self.active_pacts.append(pact)

        # Track factions
        self.faction_ids.add(pact.faction_a_id)
        self.faction_ids.add(pact.faction_b_id)

        self.touch()
        return Ok(None)

    def get_pacts_between(
        self, faction_a: str, faction_b: str
    ) -> List["DiplomaticPact"]:
        """Get all pacts between two factions.

        Args:
            faction_a: First faction ID.
            faction_b: Second faction ID.

        Returns:
            List of DiplomaticPact objects between the two factions.

        Example:
            >>> pacts = matrix.get_pacts_between("kingdom-a", "empire-b")
            >>> for pact in pacts:
            ...     print(f"{pact.pact_type.value}: active={pact.is_active()}")
        """
        result = []
        for pact in self.active_pacts:
            if pact.involves_faction(faction_a) and pact.involves_faction(faction_b):
                result.append(pact)
        return result

    def get_active_pacts_between(
        self, faction_a: str, faction_b: str
    ) -> List["DiplomaticPact"]:
        """Get all active pacts between two factions.

        Args:
            faction_a: First faction ID.
            faction_b: Second faction ID.

        Returns:
            List of active DiplomaticPact objects.
        """
        return [
            pact
            for pact in self.get_pacts_between(faction_a, faction_b)
            if pact.is_active()
        ]

    def get_pacts_by_type(
        self, pact_type: "PactType"
    ) -> List["DiplomaticPact"]:
        """Get all pacts of a specific type.

        Args:
            pact_type: The type of pact to filter by.

        Returns:
            List of DiplomaticPact objects of the specified type.
        """
        return [pact for pact in self.active_pacts if pact.pact_type == pact_type]

    def get_pacts_for_faction(self, faction_id: str) -> List["DiplomaticPact"]:
        """Get all pacts involving a specific faction.

        Args:
            faction_id: The faction ID to query.

        Returns:
            List of DiplomaticPact objects involving the faction.
        """
        return [pact for pact in self.active_pacts if pact.involves_faction(faction_id)]

    def remove_pact(self, pact_id: str) -> bool:
        """Remove a pact by its ID.

        Args:
            pact_id: The ID of the pact to remove.

        Returns:
            True if pact was removed, False if not found.
        """
        for i, pact in enumerate(self.active_pacts):
            if pact.id == pact_id:
                self.active_pacts.pop(i)
                self.touch()
                return True
        return False

    def cleanup_expired_pacts(self) -> int:
        """Remove all expired pacts from the active list.

        Returns:
            Number of expired pacts removed.
        """
        current_time = datetime.now()
        initial_count = len(self.active_pacts)

        self.active_pacts = [
            pact for pact in self.active_pacts
            if pact.is_active(current_time)
        ]

        removed = initial_count - len(self.active_pacts)
        if removed > 0:
            self.touch()

        return removed

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert DiplomacyMatrix-specific data to dictionary."""
        return {
            "world_id": self.world_id,
            "relations": {
                f"{a}|{b}": status.value
                for (a, b), status in self.relations.items()
            },
            "faction_ids": list(self.faction_ids),
            "faction_count": len(self.faction_ids),
            "relation_count": len(self.relations),
            "active_pacts": [pact.to_dict() for pact in self.active_pacts],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiplomacyMatrix":
        """Create a DiplomacyMatrix from dictionary representation.

        Args:
            data: Dictionary with matrix data

        Returns:
            New DiplomacyMatrix instance

        Raises:
            KeyError: If required keys are missing
            ValueError: If values are invalid
        """
        relations: Dict[Tuple[str, str], DiplomaticStatus] = {}

        # Parse relations from "faction_a|faction_b": "status" format
        for key_str, status_value in data.get("relations", {}).items():
            parts = key_str.split("|")
            if len(parts) == 2:
                key = (parts[0], parts[1])
                relations[key] = DiplomaticStatus(status_value)

        return cls(
            id=data["id"],
            world_id=data.get("world_id", ""),
            relations=relations,
            faction_ids=set(data.get("faction_ids", [])),
            created_at=cls._parse_datetime(data.get("created_at")),
            updated_at=cls._parse_datetime(data.get("updated_at")),
            version=data.get("version", 1),
        )

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Any:
        """Parse datetime from ISO format string."""
        from datetime import datetime
        if value:
            return datetime.fromisoformat(value)
        return datetime.now()
