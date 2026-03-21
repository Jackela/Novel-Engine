"""Tests for the ValueObject base class.

This module contains comprehensive tests for the ValueObject class,
ensuring proper attribute-based equality, immutability, and validation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from decimal import Decimal
from typing import override
from uuid import uuid4

import pytest

from src.shared.domain.base.value_object import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    """Money value object for testing."""

    amount: Decimal
    currency: str

    @override
    def validate(self) -> None:
        """Validate money value."""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3 characters")


@dataclass(frozen=True)
class Email(ValueObject):
    """Email value object for testing."""

    address: str

    @override
    def validate(self) -> None:
        """Validate email format."""
        if "@" not in self.address:
            raise ValueError("Invalid email format")


class TestValueObject:
    """Test cases for ValueObject base class."""

    def test_value_object_equality(self) -> None:
        """Test that value objects with same attributes are equal."""
        money1 = Money(Decimal("10.00"), "USD")
        money2 = Money(Decimal("10.00"), "USD")
        money3 = Money(Decimal("20.00"), "USD")

        assert money1 == money2
        assert money1 != money3
        assert money1 != "not a value object"
        assert money1 != None

    def test_value_object_inequality_with_different_types(self) -> None:
        """Test that different types are never equal."""

        @dataclass(frozen=True)
        class Price(ValueObject):
            amount: Decimal
            currency: str

            def validate(self) -> None:
                pass

        money = Money(Decimal("10.00"), "USD")
        price = Price(Decimal("10.00"), "USD")

        assert money != price

    def test_value_object_hash(self) -> None:
        """Test that value objects with same attributes have same hash."""
        money1 = Money(Decimal("10.00"), "USD")
        money2 = Money(Decimal("10.00"), "USD")

        assert hash(money1) == hash(money2)

    def test_value_object_can_be_dict_key(self) -> None:
        """Test that value objects can be used as dictionary keys."""
        money = Money(Decimal("10.00"), "USD")
        price_map = {money: "ten dollars"}

        same_money = Money(Decimal("10.00"), "USD")

        assert price_map[same_money] == "ten dollars"

    def test_value_object_validation_on_creation(self) -> None:
        """Test that validation runs on creation."""
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            Money(Decimal("-10.00"), "USD")

    def test_value_object_validation_with_email(self) -> None:
        """Test email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("notanemail")

    def test_value_object_immutability(self) -> None:
        """Test that value objects are immutable."""
        money = Money(Decimal("10.00"), "USD")

        with pytest.raises(FrozenInstanceError):
            money.amount = Decimal("20.00")  # type: ignore[misc]

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        money = Money(Decimal("10.50"), "USD")

        result = money.to_dict()

        assert result == {"amount": Decimal("10.50"), "currency": "USD"}

    def test_copy_with_changes(self) -> None:
        """Test creating copy with modified attributes."""
        money = Money(Decimal("10.00"), "USD")

        new_money = money.copy(amount=Decimal("20.00"))

        assert new_money.amount == Decimal("20.00")
        assert new_money.currency == "USD"
        assert money.amount == Decimal("10.00")  # Original unchanged

    def test_copy_without_changes(self) -> None:
        """Test creating copy without changes."""
        money = Money(Decimal("10.00"), "USD")

        copy = money.copy()

        assert copy == money
        assert copy is not money

    def test_str_representation(self) -> None:
        """Test string representation."""
        money = Money(Decimal("10.00"), "USD")

        result = str(money)

        assert "Money" in result
        assert "10.00" in result
        assert "USD" in result

    def test_different_value_objects_different_hashes(self) -> None:
        """Test that different value objects have different hashes."""
        money1 = Money(Decimal("10.00"), "USD")
        money2 = Money(Decimal("20.00"), "EUR")

        assert hash(money1) != hash(money2)


class TestAbstractValueObject:
    """Test cases for abstract ValueObject behavior."""

    def test_cannot_instantiate_abstract_value_object(self) -> None:
        """Test that ValueObject cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ValueObject()  # type: ignore[abstract]

    def test_validate_must_be_implemented(self) -> None:
        """Test that concrete classes must implement validate."""

        @dataclass(frozen=True)
        class IncompleteVO(ValueObject):
            value: str
            # Missing validate implementation

        with pytest.raises(TypeError):
            IncompleteVO("test")  # type: ignore[abstract]
