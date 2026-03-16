"""Domain value object base class for Novel Engine.

This module defines the abstract base class for all domain value objects.
Value objects are immutable objects that are defined by their attributes
rather than an identity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Any, final


@dataclass(frozen=True)
class ValueObject(ABC):
    """Abstract base class for all domain value objects.

    Value objects are immutable, defined by their attributes,
    and have no conceptual identity. Two value objects with the
    same attributes are considered equal.

    Attributes:
        All attributes are frozen (immutable) after creation.

    Example:
        >>> @dataclass(frozen=True)
        ... class Money(ValueObject):
        ...     amount: Decimal
        ...     currency: str
        ...
        >>> m1 = Money(Decimal('10.00'), 'USD')
        >>> m2 = Money(Decimal('10.00'), 'USD')
        >>> m1 == m2  # True

    Note:
        Value objects must be decorated with @dataclass(frozen=True)
        or equivalent to ensure immutability.
    """

    def __eq__(self, other: object) -> bool:
        """Check equality based on attributes.

        Two value objects are equal if they have the same type
        and all attributes are equal.

        Args:
            other: The object to compare with.

        Returns:
            True if the value objects are equal, False otherwise.
        """
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """Return hash based on all attributes.

        Returns:
            Hash value for the value object.
        """
        return hash(tuple(sorted(self.__dict__.items())))

    @abstractmethod
    def validate(self) -> None:
        """Validate the value object's invariants.

        This method must be implemented by concrete value object classes
        to ensure the value object maintains valid state upon creation.

        Raises:
            DomainException: If the value object is in an invalid state.
        """
        ...

    def __post_init__(self) -> None:
        """Post-initialization hook to validate the value object.

        This is called automatically after the dataclass is initialized.
        """
        self.validate()

    @final
    def to_dict(self) -> dict[str, Any]:
        """Convert the value object to a dictionary.

        Returns:
            Dictionary representation of the value object.
        """
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @final
    def copy(self, **kwargs: Any) -> "ValueObject":
        """Create a new value object with updated attributes.

        Since value objects are immutable, this creates a new instance
        rather than modifying the current one.

        Args:
            **kwargs: Attributes to update in the new instance.

        Returns:
            A new value object with the updated attributes.

        Example:
            >>> m1 = Money(Decimal('10.00'), 'USD')
            >>> m2 = m1.copy(amount=Decimal('20.00'))
        """
        current_values = self.to_dict()
        current_values.update(kwargs)
        return self.__class__(**current_values)

    def __str__(self) -> str:
        """Return string representation of the value object.

        Returns:
            Human-readable string representation.
        """
        attributes = ", ".join(
            f"{field.name}={getattr(self, field.name)}" for field in fields(self)
        )
        return f"{self.__class__.__name__}({attributes})"
