"""Tests for domain semantic types.

This module contains comprehensive tests for the semantic type definitions,
ensuring proper type safety and validation.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.shared.domain.types import (
    ChapterId,
    ChapterNumber,
    ChapterTitle,
    CharacterId,
    CharacterName,
    ContentText,
    Email,
    Money,
    NovelId,
    NovelTitle,
    ProgressPercentage,
    Rating,
    SceneDescription,
    SceneId,
    SceneOrder,
    UserId,
    WordCount,
)


class TestSemanticIdTypes:
    """Test cases for semantic ID types."""

    def test_user_id_creation(self) -> None:
        """Test UserId type creation."""
        uuid = uuid4()
        user_id: UserId = UserId(uuid)

        assert isinstance(user_id, UUID)
        assert user_id == uuid

    def test_novel_id_creation(self) -> None:
        """Test NovelId type creation."""
        uuid = uuid4()
        novel_id: NovelId = NovelId(uuid)

        assert isinstance(novel_id, UUID)

    def test_chapter_id_creation(self) -> None:
        """Test ChapterId type creation."""
        uuid = uuid4()
        chapter_id: ChapterId = ChapterId(uuid)

        assert isinstance(chapter_id, UUID)

    def test_character_id_creation(self) -> None:
        """Test CharacterId type creation."""
        uuid = uuid4()
        character_id: CharacterId = CharacterId(uuid)

        assert isinstance(character_id, UUID)

    def test_scene_id_creation(self) -> None:
        """Test SceneId type creation."""
        uuid = uuid4()
        scene_id: SceneId = SceneId(uuid)

        assert isinstance(scene_id, UUID)


class TestSemanticContentTypes:
    """Test cases for semantic content types."""

    def test_novel_title_creation(self) -> None:
        """Test NovelTitle type creation."""
        title: NovelTitle = NovelTitle("The Great Novel")

        assert isinstance(title, str)
        assert title == "The Great Novel"

    def test_chapter_title_creation(self) -> None:
        """Test ChapterTitle type creation."""
        title: ChapterTitle = ChapterTitle("Chapter 1: The Beginning")

        assert isinstance(title, str)

    def test_character_name_creation(self) -> None:
        """Test CharacterName type creation."""
        name: CharacterName = CharacterName("John Doe")

        assert isinstance(name, str)

    def test_scene_description_creation(self) -> None:
        """Test SceneDescription type creation."""
        desc: SceneDescription = SceneDescription("A dark and stormy night...")

        assert isinstance(desc, str)

    def test_content_text_creation(self) -> None:
        """Test ContentText type creation."""
        text: ContentText = ContentText("Once upon a time...")

        assert isinstance(text, str)


class TestSemanticNumericTypes:
    """Test cases for semantic numeric types."""

    def test_word_count_creation(self) -> None:
        """Test WordCount type creation."""
        count: WordCount = WordCount(1000)

        assert isinstance(count, int)
        assert count == 1000

    def test_chapter_number_creation(self) -> None:
        """Test ChapterNumber type creation."""
        num: ChapterNumber = ChapterNumber(5)

        assert isinstance(num, int)

    def test_scene_order_creation(self) -> None:
        """Test SceneOrder type creation."""
        order: SceneOrder = SceneOrder(3)

        assert isinstance(order, int)

    def test_progress_percentage_creation(self) -> None:
        """Test ProgressPercentage type creation."""
        progress: ProgressPercentage = ProgressPercentage(75.5)

        assert isinstance(progress, float)


class TestMoney:
    """Test cases for Money value object."""

    def test_money_creation(self) -> None:
        """Test Money creation with valid values."""
        money = Money(amount=Decimal("19.99"), currency="USD")

        assert money.amount == Decimal("19.99")
        assert money.currency == "USD"

    def test_money_invalid_currency_length(self) -> None:
        """Test Money creation with invalid currency length."""
        with pytest.raises(ValueError, match="3 characters"):
            Money(amount=Decimal("10.00"), currency="US")

    def test_money_invalid_currency_case(self) -> None:
        """Test Money creation with lowercase currency."""
        with pytest.raises(ValueError, match="uppercase"):
            Money(amount=Decimal("10.00"), currency="usd")

    def test_money_add_same_currency(self) -> None:
        """Test adding money with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.00"), currency="USD")

        result = m1.add(m2)

        assert result.amount == Decimal("15.00")
        assert result.currency == "USD"

    def test_money_add_different_currency_raises(self) -> None:
        """Test adding money with different currency raises error."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.00"), currency="EUR")

        with pytest.raises(ValueError, match="Cannot add"):
            m1.add(m2)

    def test_money_subtract_same_currency(self) -> None:
        """Test subtracting money with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("3.00"), currency="USD")

        result = m1.subtract(m2)

        assert result.amount == Decimal("7.00")

    def test_money_subtract_different_currency_raises(self) -> None:
        """Test subtracting money with different currency raises error."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.00"), currency="EUR")

        with pytest.raises(ValueError, match="Cannot subtract"):
            m1.subtract(m2)

    def test_money_multiply_by_decimal(self) -> None:
        """Test multiplying money by decimal."""
        m = Money(amount=Decimal("10.00"), currency="USD")

        result = m.multiply(Decimal("2.5"))

        assert result.amount == Decimal("25.00")

    def test_money_multiply_by_int(self) -> None:
        """Test multiplying money by integer."""
        m = Money(amount=Decimal("10.00"), currency="USD")

        result = m.multiply(3)

        assert result.amount == Decimal("30.00")

    def test_money_multiply_by_float(self) -> None:
        """Test multiplying money by float."""
        m = Money(amount=Decimal("10.00"), currency="USD")

        result = m.multiply(1.5)

        assert result.amount == Decimal("15.00")


class TestRating:
    """Test cases for Rating value object."""

    def test_rating_creation_valid(self) -> None:
        """Test Rating creation with valid value."""
        rating = Rating(value=4, scale_min=1, scale_max=5)

        assert rating.value == 4
        assert rating.scale_min == 1
        assert rating.scale_max == 5

    def test_rating_creation_invalid_value(self) -> None:
        """Test Rating creation with invalid value."""
        with pytest.raises(ValueError, match="must be between"):
            Rating(value=10, scale_min=1, scale_max=5)

    def test_rating_creation_below_min(self) -> None:
        """Test Rating creation below minimum."""
        with pytest.raises(ValueError):
            Rating(value=0, scale_min=1, scale_max=5)

    def test_is_valid_returns_true_for_valid(self) -> None:
        """Test is_valid returns True for valid rating."""
        rating = Rating(value=3)

        assert rating.is_valid() is True

    def test_is_valid_returns_false_for_invalid(self) -> None:
        """Test is_valid returns False for invalid rating."""
        # We can't create an invalid rating through normal constructor,
        # so we test the method directly
        rating = Rating(value=3, scale_min=1, scale_max=5)
        rating = object.__new__(Rating)
        object.__setattr__(rating, "value", 10)
        object.__setattr__(rating, "scale_min", 1)
        object.__setattr__(rating, "scale_max", 5)

        assert rating.is_valid() is False

    def test_to_percentage_full_scale(self) -> None:
        """Test conversion to percentage at max value."""
        rating = Rating(value=5, scale_min=1, scale_max=5)

        assert rating.to_percentage() == 100.0

    def test_to_percentage_min_scale(self) -> None:
        """Test conversion to percentage at min value."""
        rating = Rating(value=1, scale_min=1, scale_max=5)

        assert rating.to_percentage() == 0.0

    def test_to_percentage_mid_scale(self) -> None:
        """Test conversion to percentage at mid value."""
        rating = Rating(value=3, scale_min=1, scale_max=5)

        assert rating.to_percentage() == 50.0

    def test_to_percentage_zero_range(self) -> None:
        """Test percentage with zero range (edge case)."""
        rating = Rating(value=5, scale_min=5, scale_max=5)

        assert rating.to_percentage() == 100.0


class TestEmail:
    """Test cases for Email value object."""

    def test_email_creation_valid(self) -> None:
        """Test Email creation with valid address."""
        email = Email(address="user@example.com")

        assert email.address == "user@example.com"

    def test_email_creation_invalid_no_at(self) -> None:
        """Test Email creation without @ symbol."""
        with pytest.raises(ValueError, match="Invalid email"):
            Email(address="invalid.email")

    def test_email_creation_invalid_empty_local(self) -> None:
        """Test Email creation with empty local part."""
        with pytest.raises(ValueError, match="Invalid email"):
            Email(address="@example.com")

    def test_email_creation_invalid_empty_domain(self) -> None:
        """Test Email creation with empty domain part."""
        with pytest.raises(ValueError, match="Invalid email"):
            Email(address="user@")

    def test_email_domain_property(self) -> None:
        """Test domain property extraction."""
        email = Email(address="user@example.com")

        assert email.domain == "example.com"

    def test_email_local_part_property(self) -> None:
        """Test local part property extraction."""
        email = Email(address="user@example.com")

        assert email.local_part == "user"

    def test_email_with_multiple_at_symbols(self) -> None:
        """Test email with multiple @ symbols."""
        # This should actually fail, but let's test current behavior
        with pytest.raises(ValueError, match="Invalid email"):
            Email(address="user@domain@example.com")
