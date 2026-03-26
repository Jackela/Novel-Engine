"""Semantic type definitions for Novel Engine domain layer.

This module defines semantic types that provide type safety and
clear meaning to primitive values used throughout the domain layer.
Semantic types prevent primitive obsession and make the code more
self-documenting.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import NewType, TypeVar
from uuid import UUID

# ID Types - Semantic identifiers for different domain concepts
UserId = NewType("UserId", UUID)
"""Unique identifier for a User entity."""

StoryId = NewType("StoryId", UUID)
"""Unique identifier for a Story entity."""

NovelId = NewType("NovelId", UUID)
"""Unique identifier for a Novel entity."""

ChapterId = NewType("ChapterId", UUID)
"""Unique identifier for a Chapter entity."""

CharacterId = NewType("CharacterId", UUID)
"""Unique identifier for a Character entity."""

SceneId = NewType("SceneId", UUID)
"""Unique identifier for a Scene entity."""

# Content Types - Semantic wrappers for text and content
NovelTitle = NewType("NovelTitle", str)
"""Title of a novel with validation rules."""

ChapterTitle = NewType("ChapterTitle", str)
"""Title of a chapter."""

CharacterName = NewType("CharacterName", str)
"""Name of a character."""

SceneDescription = NewType("SceneDescription", str)
"""Description text for a scene."""

ContentText = NewType("ContentText", str)
"""Body text content (e.g., chapter content)."""

# Numeric Types - Semantic wrappers for numeric values
WordCount = NewType("WordCount", int)
"""Count of words in a content piece."""

ChapterNumber = NewType("ChapterNumber", int)
"""Sequential number of a chapter in a novel."""

SceneOrder = NewType("SceneOrder", int)
"""Order/position of a scene within a chapter."""

ProgressPercentage = NewType("ProgressPercentage", float)
"""Progress expressed as a percentage (0.0 to 100.0)."""

# Generic Type Variables
T = TypeVar("T")
"""Generic type variable for general use."""

ID = TypeVar("ID")
"""Generic type variable for identifier types."""

E = TypeVar("E")
"""Generic type variable for entity types."""


@dataclass(frozen=True)
class Money:
    """Value object representing monetary value.

    Attributes:
        amount: The monetary amount.
        currency: ISO 4217 currency code (e.g., 'USD', 'EUR').

    Example:
        >>> price = Money(amount=Decimal('19.99'), currency='USD')
        >>> price.amount
        Decimal('19.99')
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        """Validate money values after initialization."""
        if len(self.currency) != 3:
            raise ValueError(
                f"Currency code must be 3 characters, got: {self.currency}"
            )
        if self.currency.upper() != self.currency:
            raise ValueError(f"Currency code must be uppercase, got: {self.currency}")

    def add(self, other: Money) -> Money:
        """Add two money values of the same currency.

        Args:
            other: The money to add.

        Returns:
            New Money instance with the sum.

        Raises:
            ValueError: If currencies don't match.
        """
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: Money) -> Money:
        """Subtract one money value from another.

        Args:
            other: The money to subtract.

        Returns:
            New Money instance with the difference.

        Raises:
            ValueError: If currencies don't match.
        """
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def multiply(self, factor: Decimal | int | float) -> Money:
        """Multiply money by a factor.

        Args:
            factor: The multiplier.

        Returns:
            New Money instance with the product.
        """
        if isinstance(factor, (int, float)):
            factor = Decimal(str(factor))
        return Money(amount=self.amount * factor, currency=self.currency)


@dataclass(frozen=True)
class Rating:
    """Value object representing a rating value.

    Attributes:
        value: The rating value, typically 1-5 or 1-10.
        scale_min: Minimum value of the rating scale.
        scale_max: Maximum value of the rating scale.

    Example:
        >>> rating = Rating(value=4, scale_min=1, scale_max=5)
        >>> rating.is_valid()
        True
    """

    value: int
    scale_min: int = 1
    scale_max: int = 5

    def __post_init__(self) -> None:
        """Validate rating after initialization."""
        if not self.is_valid():
            raise ValueError(
                f"Rating value {self.value} must be between "
                f"{self.scale_min} and {self.scale_max}"
            )

    def is_valid(self) -> bool:
        """Check if the rating value is within valid range.

        Returns:
            True if rating is valid, False otherwise.
        """
        return self.scale_min <= self.value <= self.scale_max

    def to_percentage(self) -> float:
        """Convert rating to percentage of the scale.

        Returns:
            Percentage value (0.0 to 100.0).
        """
        range_size = self.scale_max - self.scale_min
        if range_size == 0:
            return 100.0
        return ((self.value - self.scale_min) / range_size) * 100.0


@dataclass(frozen=True)
class Email:
    """Value object representing an email address.

    Attributes:
        address: The email address string.

    Example:
        >>> email = Email(address="user@example.com")
        >>> email.domain
        'example.com'
    """

    address: str

    def __post_init__(self) -> None:
        """Validate email format."""
        if "@" not in self.address:
            raise ValueError(f"Invalid email address: {self.address}")
        parts = self.address.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid email address: {self.address}")

    @property
    def domain(self) -> str:
        """Get the domain part of the email.

        Returns:
            Domain portion after @.
        """
        return self.address.split("@")[1]

    @property
    def local_part(self) -> str:
        """Get the local part of the email.

        Returns:
            Local portion before @.
        """
        return self.address.split("@")[0]
