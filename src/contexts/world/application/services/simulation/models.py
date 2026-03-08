"""World Simulation Models.

Data classes for simulation results.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List

from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.simulation_tick import (
    DiplomacyChange,
    ResourceChanges,
)

if TYPE_CHECKING:
    pass


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
