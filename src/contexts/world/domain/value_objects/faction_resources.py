"""Faction resources value object for tracking faction assets.

This module provides a value object to track and manage the complete
resource portfolio of a faction.

Typical usage example:
    >>> from src.contexts.world.domain.value_objects import (
    ...     FactionResources, ResourceType
    ... )
    >>> resources = FactionResources(faction_id="faction-123")
    >>> resources = resources.add(ResourceType.GOLD, 1000)
    >>> resources.get_amount(ResourceType.GOLD)
    1000
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping

from .resource_type import ResourceType


@dataclass(frozen=True)
class FactionResources:
    """Domain value object representing a faction's complete resource portfolio.

    Provides an immutable snapshot of all resources owned by a faction,
    with operations for adding, spending, and querying resources.

    Attributes:
        faction_id: The unique identifier of the faction owning these resources.
        resources: Dictionary mapping resource types to amounts.

    Example:
        >>> resources = FactionResources(
        ...     faction_id="faction-123",
        ...     resources={ResourceType.GOLD: 500, ResourceType.FOOD: 200}
        ... )
        >>> resources.get_amount(ResourceType.GOLD)
        500
    """

    faction_id: str
    resources: Dict[ResourceType, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate resources after initialization."""
        for resource_type, amount in self.resources.items():
            if amount < 0:
                raise ValueError(
                    f"Resource amount cannot be negative: {resource_type}={amount}"
                )

    def get_amount(self, resource_type: ResourceType) -> int:
        """Get the amount of a specific resource.

        Args:
            resource_type: The type of resource to query.

        Returns:
            The amount of that resource, or 0 if not present.
        """
        return self.resources.get(resource_type, 0)

    def add(self, resource_type: ResourceType, amount: int) -> FactionResources:
        """Create a new FactionResources with added resources.

        Args:
            resource_type: The type of resource to add.
            amount: The amount to add (must be non-negative).

        Returns:
            A new FactionResources instance with updated amounts.

        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError("Cannot add negative amount, use spend() instead")

        new_resources = dict(self.resources)
        current = new_resources.get(resource_type, 0)
        new_resources[resource_type] = current + amount

        return FactionResources(faction_id=self.faction_id, resources=new_resources)

    def spend(self, resource_type: ResourceType, amount: int) -> FactionResources:
        """Create a new FactionResources with spent resources.

        Args:
            resource_type: The type of resource to spend.
            amount: The amount to spend (must be non-negative).

        Returns:
            A new FactionResources instance with updated amounts.

        Raises:
            ValueError: If amount is negative or exceeds available resources.
        """
        if amount < 0:
            raise ValueError("Cannot spend negative amount, use add() instead")

        current = self.resources.get(resource_type, 0)
        if amount > current:
            raise ValueError(
                f"Insufficient {resource_type.value}: have {current}, need {amount}"
            )

        new_resources = dict(self.resources)
        new_resources[resource_type] = current - amount

        # Remove resource type if amount is zero
        if new_resources[resource_type] == 0:
            del new_resources[resource_type]

        return FactionResources(faction_id=self.faction_id, resources=new_resources)

    def can_afford(self, resource_type: ResourceType, amount: int) -> bool:
        """Check if the faction has enough of a specific resource.

        Args:
            resource_type: The type of resource to check.
            amount: The amount needed.

        Returns:
            True if the faction has enough, False otherwise.
        """
        return self.get_amount(resource_type) >= amount

    def can_afford_all(self, costs: Mapping[ResourceType, int]) -> bool:
        """Check if the faction can afford multiple resource costs.

        Args:
            costs: Dictionary of resource types and amounts needed.

        Returns:
            True if the faction has enough of all resources, False otherwise.
        """
        return all(
            self.can_afford(resource_type, amount)
            for resource_type, amount in costs.items()
        )

    def total_value(self) -> int:
        """Calculate total resource value in gold-equivalent terms.

        Uses approximate conversion rates to provide a single metric
        for comparing faction wealth.

        Returns:
            Approximate total value in gold-equivalent units.
        """
        # Conversion rates (approximate gold-equivalent values)
        conversion_rates = {
            ResourceType.GOLD: 1.0,
            ResourceType.FOOD: 0.01,
            ResourceType.MANA: 5.0,
            ResourceType.IRON: 0.5,
            ResourceType.WOOD: 0.1,
            ResourceType.POPULATION: 0.5,
            ResourceType.KNOWLEDGE: 10.0,
            ResourceType.MILITARY: 2.0,
            ResourceType.TRADE_GOODS: 1.5,
            ResourceType.CULTURAL_INFLUENCE: 3.0,
        }

        return int(
            sum(
                self.get_amount(rt) * conversion_rates.get(rt, 1.0)
                for rt in ResourceType
            )
        )

    def merge(self, other: FactionResources) -> FactionResources:
        """Merge resources from another FactionResources object.

        Args:
            other: Another FactionResources to merge with.

        Returns:
            A new FactionResources with combined amounts.

        Raises:
            ValueError: If faction_ids don't match.
        """
        if other.faction_id != self.faction_id:
            raise ValueError("Cannot merge resources from different factions")

        new_resources = dict(self.resources)
        for resource_type, amount in other.resources.items():
            current = new_resources.get(resource_type, 0)
            new_resources[resource_type] = current + amount

        return FactionResources(faction_id=self.faction_id, resources=new_resources)

    def to_dict(self) -> Dict[str, int]:
        """Convert resources to a dictionary with string keys.

        Returns:
            Dictionary mapping resource type names to amounts.
        """
        return {rt.value: amount for rt, amount in self.resources.items()}

    @classmethod
    def from_dict(cls, faction_id: str, data: Dict[str, int]) -> FactionResources:
        """Create FactionResources from a dictionary with string keys.

        Args:
            faction_id: The faction's unique identifier.
            data: Dictionary mapping resource type names to amounts.

        Returns:
            A new FactionResources instance.
        """
        resources: dict[Any, Any] = {}
        for key, value in data.items():
            try:
                resource_type = ResourceType(key)
                resources[resource_type] = value
            except ValueError:
                # Skip unknown resource types
                pass

        return cls(faction_id=faction_id, resources=resources)
