"""Resource yield value object for territory production.

This module defines how territories produce resources over time.
Resource yields represent the production capacity of a location.

Typical usage example:
    >>> from src.contexts.world.domain.value_objects import ResourceYield, ResourceType
    >>> gold_yield = ResourceYield(
    ...     resource_type=ResourceType.GOLD,
    ...     base_amount=100,
    ...     modifier=1.5
    ... )
    >>> gold_yield.calculate_yield()
    150
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .resource_type import ResourceType


@dataclass(frozen=True)
class ResourceYield:
    """Domain value object representing resource production from a territory.

    Captures the production parameters for a specific resource type,
    including base production and efficiency modifiers.

    Attributes:
        resource_type: The type of resource being produced.
        base_amount: Base production amount per tick/turn.
        modifier: Efficiency multiplier (1.0 = 100%, 1.5 = 150%).
        current_stock: Current accumulated amount of this resource.

    Example:
        >>> yield_obj = ResourceYield(
        ...     resource_type=ResourceType.FOOD,
        ...     base_amount=50,
        ...     modifier=1.2
        ... )
        >>> yield_obj.calculate_yield()
        60
    """

    resource_type: ResourceType
    base_amount: int
    modifier: float = 1.0
    current_stock: int = 0

    def __post_init__(self) -> None:
        """Validate the resource yield after initialization."""
        if self.base_amount < 0:
            raise ValueError("Base amount cannot be negative")
        if self.modifier < 0:
            raise ValueError("Modifier cannot be negative")
        if self.current_stock < 0:
            raise ValueError("Current stock cannot be negative")

    def calculate_yield(self) -> int:
        """Calculate the actual yield amount.

        Applies the modifier to the base amount to determine
        effective production.

        Returns:
            The calculated yield as an integer.
        """
        return int(self.base_amount * self.modifier)

    def with_modifier(self, new_modifier: float) -> ResourceYield:
        """Create a new ResourceYield with an updated modifier.

        Args:
            new_modifier: The new efficiency modifier to apply.

        Returns:
            A new ResourceYield instance with the updated modifier.
        """
        return ResourceYield(
            resource_type=self.resource_type,
            base_amount=self.base_amount,
            modifier=new_modifier,
            current_stock=self.current_stock,
        )

    def add_to_stock(self, amount: int) -> ResourceYield:
        """Create a new ResourceYield with increased stock.

        Args:
            amount: The amount to add to current stock.

        Returns:
            A new ResourceYield instance with updated stock.
        """
        return ResourceYield(
            resource_type=self.resource_type,
            base_amount=self.base_amount,
            modifier=self.modifier,
            current_stock=self.current_stock + amount,
        )

    def collect_yield(self) -> ResourceYield:
        """Collect the current yield and add to stock.

        Returns:
            A new ResourceYield instance with yield added to stock.
        """
        return self.add_to_stock(self.calculate_yield())

    def consume(self, amount: int) -> ResourceYield:
        """Consume resources from stock.

        Args:
            amount: The amount to consume.

        Returns:
            A new ResourceYield instance with reduced stock.

        Raises:
            ValueError: If trying to consume more than available stock.
        """
        if amount > self.current_stock:
            raise ValueError(
                f"Cannot consume {amount}, only {self.current_stock} available"
            )
        return ResourceYield(
            resource_type=self.resource_type,
            base_amount=self.base_amount,
            modifier=self.modifier,
            current_stock=self.current_stock - amount,
        )
