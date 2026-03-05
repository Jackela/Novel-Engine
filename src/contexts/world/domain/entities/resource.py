"""Resource Domain Entity.

This module defines the Resource entity which represents a stockpile of
a specific resource type within the world economy system.

Typical usage example:
    >>> from src.contexts.world.domain.entities import Resource
    >>> from src.contexts.world.domain.value_objects import ResourceType
    >>> gold_vault = Resource(
    ...     resource_type=ResourceType.GOLD,
    ...     amount=1000,
    ...     max_capacity=5000
    ... )
    >>> gold_vault.add(500)
    >>> gold_vault.amount
    1500
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.contexts.world.domain.value_objects.resource_type import ResourceType

from .entity import Entity


@dataclass(eq=False)
class Resource(Entity):
    """Resource Entity.

    Represents a stockpile of a specific resource type. Resources are
    tracked with amounts and capacity limits, supporting add/consume
    operations for economic simulation.

    Attributes:
        resource_type: The type of this resource.
        amount: Current amount of the resource.
        max_capacity: Maximum storage capacity (None = unlimited).
        name: Optional display name for the resource stockpile.
        location_id: Optional ID of the location where resource is stored.
        owner_faction_id: Optional ID of the faction that owns this resource.
    """

    resource_type: ResourceType = ResourceType.GOLD
    amount: int = 0
    max_capacity: Optional[int] = None
    name: Optional[str] = None
    location_id: Optional[str] = None
    owner_faction_id: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        """Compare resources by identity, not by mutable attributes."""
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate Resource-specific business rules."""
        errors = []

        if self.amount < 0:
            errors.append("Resource amount cannot be negative")

        if self.max_capacity is not None and self.max_capacity < 0:
            errors.append("Max capacity cannot be negative")

        if self.max_capacity is not None and self.amount > self.max_capacity:
            errors.append(
                f"Amount ({self.amount}) exceeds max capacity ({self.max_capacity})"
            )

        return errors

    def add(self, quantity: int) -> None:
        """Add resources to the stockpile.

        Args:
            quantity: Amount to add (must be non-negative).

        Raises:
            ValueError: If quantity is negative or would exceed capacity.
        """
        if quantity < 0:
            raise ValueError("Cannot add negative quantity, use consume() instead")

        new_amount = self.amount + quantity
        if self.max_capacity is not None and new_amount > self.max_capacity:
            raise ValueError(
                f"Cannot add {quantity}: would exceed max capacity of {self.max_capacity}"
            )

        self.amount = new_amount
        self.touch()

    def consume(self, quantity: int) -> None:
        """Consume resources from the stockpile.

        Args:
            quantity: Amount to consume (must be non-negative).

        Raises:
            ValueError: If quantity is negative or exceeds available amount.
        """
        if quantity < 0:
            raise ValueError("Cannot consume negative quantity, use add() instead")

        if quantity > self.amount:
            raise ValueError(f"Cannot consume {quantity}: only {self.amount} available")

        self.amount -= quantity
        self.touch()

    def can_add(self, quantity: int) -> bool:
        """Check if the given quantity can be added.

        Args:
            quantity: Amount to potentially add.

        Returns:
            True if the quantity can be added without exceeding capacity.
        """
        if quantity < 0:
            return False

        if self.max_capacity is None:
            return True

        return self.amount + quantity <= self.max_capacity

    def can_consume(self, quantity: int) -> bool:
        """Check if the given quantity can be consumed.

        Args:
            quantity: Amount to potentially consume.

        Returns:
            True if the quantity can be consumed from current stock.
        """
        return 0 <= quantity <= self.amount

    def available_capacity(self) -> Optional[int]:
        """Calculate remaining storage capacity.

        Returns:
            Remaining capacity, or None if unlimited.
        """
        if self.max_capacity is None:
            return None
        return max(0, self.max_capacity - self.amount)

    def is_full(self) -> bool:
        """Check if the resource is at max capacity.

        Returns:
            True if at max capacity, False otherwise.
        """
        if self.max_capacity is None:
            return False
        return self.amount >= self.max_capacity

    def is_empty(self) -> bool:
        """Check if the resource is depleted.

        Returns:
            True if amount is zero, False otherwise.
        """
        return self.amount == 0

    def fill_to_capacity(self) -> int:
        """Fill the resource to max capacity.

        Returns:
            The amount added to reach capacity.

        Raises:
            ValueError: If resource has no max capacity.
        """
        if self.max_capacity is None:
            raise ValueError("Cannot fill resource with unlimited capacity")

        added = self.max_capacity - self.amount
        if added > 0:
            self.amount = self.max_capacity
            self.touch()

        return added

    def set_capacity(self, new_capacity: Optional[int]) -> None:
        """Set a new max capacity.

        Args:
            new_capacity: New maximum capacity, or None for unlimited.

        Raises:
            ValueError: If new capacity is less than current amount.
        """
        if new_capacity is not None and new_capacity < self.amount:
            raise ValueError(
                f"Cannot set capacity to {new_capacity}: "
                f"current amount is {self.amount}"
            )

        self.max_capacity = new_capacity
        self.touch()

    def transfer_to(self, target: Resource, quantity: int) -> None:
        """Transfer resources to another stockpile.

        Args:
            target: The target Resource to transfer to.
            quantity: Amount to transfer.

        Raises:
            ValueError: If resource types don't match, or if transfer
                would fail due to insufficient source or target capacity.
        """
        if target.resource_type != self.resource_type:
            raise ValueError(
                f"Cannot transfer {self.resource_type.value} to "
                f"{target.resource_type.value} stockpile"
            )

        if not self.can_consume(quantity):
            raise ValueError(f"Insufficient {self.resource_type.value} to transfer")

        if not target.can_add(quantity):
            raise ValueError(
                f"Target cannot accept {quantity} {self.resource_type.value}"
            )

        self.consume(quantity)
        target.add(quantity)

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert Resource-specific data to dictionary."""
        return {
            "resource_type": self.resource_type.value,
            "amount": self.amount,
            "max_capacity": self.max_capacity,
            "name": self.name,
            "location_id": self.location_id,
            "owner_faction_id": self.owner_faction_id,
        }

    @classmethod
    def create_gold_vault(
        cls,
        initial_amount: int = 0,
        max_capacity: int = 10000,
        owner_faction_id: Optional[str] = None,
    ) -> Resource:
        """Create a gold vault resource.

        Factory method for creating gold resource stockpiles.

        Args:
            initial_amount: Starting gold amount.
            max_capacity: Maximum gold storage.
            owner_faction_id: Owner faction ID.

        Returns:
            A new Resource configured as a gold vault.
        """
        return cls(
            resource_type=ResourceType.GOLD,
            amount=initial_amount,
            max_capacity=max_capacity,
            name="Gold Vault",
            owner_faction_id=owner_faction_id,
        )

    @classmethod
    def create_food_storage(
        cls,
        initial_amount: int = 0,
        max_capacity: int = 5000,
        owner_faction_id: Optional[str] = None,
    ) -> Resource:
        """Create a food storage resource.

        Factory method for creating food resource stockpiles.

        Args:
            initial_amount: Starting food amount.
            max_capacity: Maximum food storage.
            owner_faction_id: Owner faction ID.

        Returns:
            A new Resource configured as food storage.
        """
        return cls(
            resource_type=ResourceType.FOOD,
            amount=initial_amount,
            max_capacity=max_capacity,
            name="Food Storage",
            owner_faction_id=owner_faction_id,
        )

    @classmethod
    def create_military_force(
        cls,
        initial_amount: int = 0,
        max_capacity: Optional[int] = None,
        owner_faction_id: Optional[str] = None,
    ) -> Resource:
        """Create a military force resource.

        Factory method for creating military resource stockpiles.
        Military forces typically don't have a strict capacity limit.

        Args:
            initial_amount: Starting military strength.
            max_capacity: Maximum military capacity (optional).
            owner_faction_id: Owner faction ID.

        Returns:
            A new Resource configured as military force.
        """
        return cls(
            resource_type=ResourceType.MILITARY,
            amount=initial_amount,
            max_capacity=max_capacity,
            name="Military Force",
            owner_faction_id=owner_faction_id,
        )
