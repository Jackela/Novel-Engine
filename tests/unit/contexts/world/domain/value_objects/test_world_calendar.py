#!/usr/bin/env python3
"""
Unit tests for WorldCalendar Value Object

Comprehensive test suite for the WorldCalendar value object covering
date arithmetic, validation, immutability, and formatting.
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Mock problematic dependencies
pytestmark = pytest.mark.unit

sys.modules["aioredis"] = MagicMock()

# Import the value object we're testing
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


class TestWorldCalendarValueObject:
    """Test suite for WorldCalendar value object."""

    # ==================== Basic Creation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_calendar_creation_success(self):
        """Test successful calendar creation."""
        calendar = WorldCalendar(
            year=1042, month=3, day=15, era_name="Third Age"
        )

        assert calendar.year == 1042
        assert calendar.month == 3
        assert calendar.day == 15
        assert calendar.era_name == "Third Age"
        assert calendar.days_per_month == 30
        assert calendar.months_per_year == 12

    @pytest.mark.unit
    @pytest.mark.fast
    def test_calendar_creation_custom_config(self):
        """Test calendar creation with custom month/day configuration."""
        calendar = WorldCalendar(
            year=1,
            month=1,
            day=1,
            era_name="First Era",
            days_per_month=28,
            months_per_year=13,
        )

        assert calendar.days_per_month == 28
        assert calendar.months_per_year == 13

    @pytest.mark.unit
    @pytest.mark.fast
    def test_calendar_creation_boundary_values(self):
        """Test calendar creation at boundary values."""
        # First day of year
        calendar = WorldCalendar(year=1, month=1, day=1, era_name="Start")
        assert calendar.year == 1
        assert calendar.month == 1
        assert calendar.day == 1

        # Last day of year
        calendar = WorldCalendar(
            year=100,
            month=12,
            day=30,
            era_name="End",
            days_per_month=30,
            months_per_year=12,
        )
        assert calendar.month == 12
        assert calendar.day == 30

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_year_zero(self):
        """Test validation fails for year 0."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=0, month=3, day=15, era_name="Third Age")
        assert "Year must be >= 1" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_year_negative(self):
        """Test validation fails for negative year."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=-100, month=3, day=15, era_name="Third Age")
        assert "Year must be >= 1" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_month_zero(self):
        """Test validation fails for month 0."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=1042, month=0, day=15, era_name="Third Age")
        assert "Month must be between 1 and" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_month_thirteen(self):
        """Test validation fails for month 13 (default 12 months/year)."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=1042, month=13, day=15, era_name="Third Age")
        assert "Month must be between 1 and 12" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_day_zero(self):
        """Test validation fails for day 0."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=1042, month=3, day=0, era_name="Third Age")
        assert "Day must be between 1 and" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_day_thirty_one(self):
        """Test validation fails for day 31 (default 30 days/month)."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=1042, month=3, day=32, era_name="Third Age")
        assert "Day must be between 1 and 30" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_empty_era_name(self):
        """Test validation fails for empty era name."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=1042, month=3, day=15, era_name="")
        assert "Era name cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_whitespace_era_name(self):
        """Test validation fails for whitespace-only era name."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(year=1042, month=3, day=15, era_name="   ")
        assert "Era name cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_days_per_month(self):
        """Test validation fails for invalid days_per_month."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(
                year=1042, month=3, day=15, era_name="Third Age", days_per_month=0
            )
        assert "Days per month must be >= 1" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_invalid_months_per_year(self):
        """Test validation fails for invalid months_per_year."""
        with pytest.raises(ValueError) as exc_info:
            WorldCalendar(
                year=1042, month=3, day=15, era_name="Third Age", months_per_year=0
            )
        assert "Months per year must be >= 1" in str(exc_info.value)

    # ==================== Advance Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_within_month(self):
        """Test advancing days within the same month."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        result = calendar.advance(10)

        assert result.is_ok
        new_calendar = result.value
        assert new_calendar.year == 1042
        assert new_calendar.month == 3
        assert new_calendar.day == 25
        assert new_calendar.era_name == "Third Age"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_month_rollover(self):
        """Test advancing days that roll over to next month."""
        calendar = WorldCalendar(year=1042, month=3, day=25, era_name="Third Age")
        result = calendar.advance(10)

        assert result.is_ok
        new_calendar = result.value
        assert new_calendar.year == 1042
        assert new_calendar.month == 4
        assert new_calendar.day == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_year_rollover(self):
        """Test advancing days that roll over to next year."""
        calendar = WorldCalendar(
            year=1042, month=12, day=25, era_name="Third Age", days_per_month=30
        )
        result = calendar.advance(10)

        assert result.is_ok
        new_calendar = result.value
        assert new_calendar.year == 1043
        assert new_calendar.month == 1
        assert new_calendar.day == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_zero_days(self):
        """Test advancing 0 days returns same calendar."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        result = calendar.advance(0)

        assert result.is_ok
        assert result.value == calendar

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_negative_days_returns_error(self):
        """Test advancing negative days returns error."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        result = calendar.advance(-1)

        assert result.is_error
        assert "must be >= 0" in str(result.error)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_large_number_of_days(self):
        """Test advancing a large number of days (multiple year rollovers)."""
        calendar = WorldCalendar(
            year=1, month=1, day=1, era_name="First Age", days_per_month=30
        )
        # Advance 365 days = 1 year + 5 days (12 months * 30 = 360 days)
        result = calendar.advance(365)

        assert result.is_ok
        new_calendar = result.value
        assert new_calendar.year == 2
        assert new_calendar.month == 1
        assert new_calendar.day == 6

    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_preserves_configuration(self):
        """Test that advance preserves custom days_per_month and months_per_year."""
        calendar = WorldCalendar(
            year=1, month=1, day=1, era_name="Custom", days_per_month=28, months_per_year=13
        )
        # Advance exactly 28 days to reach month 2, day 1
        result = calendar.advance(28)

        assert result.is_ok
        new_calendar = result.value
        assert new_calendar.days_per_month == 28
        assert new_calendar.months_per_year == 13
        assert new_calendar.month == 2
        assert new_calendar.day == 1

    # ==================== Format Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_format_output(self):
        """Test format output matches expected pattern."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        formatted = calendar.format()

        assert formatted == "Year 1042, Month 3, Day 15 - Third Age"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_format_with_custom_era(self):
        """Test format with custom era name."""
        calendar = WorldCalendar(year=1, month=1, day=1, era_name="Dawn of Time")
        formatted = calendar.format()

        assert formatted == "Year 1, Month 1, Day 1 - Dawn of Time"

    # ==================== Validate Class Method Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_success(self):
        """Test validate class method returns Ok for valid input."""
        result = WorldCalendar.validate(1042, 3, 15, "Third Age")

        assert result.is_ok
        calendar = result.value
        assert calendar.year == 1042
        assert calendar.month == 3
        assert calendar.day == 15

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_invalid_month(self):
        """Test validate returns Err for invalid month."""
        result = WorldCalendar.validate(1042, 13, 15, "Third Age")

        assert result.is_error
        assert isinstance(result.error, ValueError)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_invalid_day(self):
        """Test validate returns Err for invalid day."""
        result = WorldCalendar.validate(1042, 3, 32, "Third Age")

        assert result.is_error
        assert isinstance(result.error, ValueError)

    # ==================== from_datetime Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_datetime(self):
        """Test creating calendar from datetime."""
        dt = datetime(2024, 6, 15)
        calendar = WorldCalendar.from_datetime(dt)

        assert calendar.year == 2024
        assert calendar.month == 6
        assert calendar.day == 15
        assert calendar.era_name == "Modern Era"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_datetime_preserves_date(self):
        """Test that from_datetime preserves the original date values."""
        dt = datetime(1042, 3, 15)
        calendar = WorldCalendar.from_datetime(dt)

        assert calendar.year == 1042
        assert calendar.month == 3
        assert calendar.day == 15

    # ==================== Equality and Hashing Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_same_values(self):
        """Test calendar equality with same values."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")

        assert calendar1 == calendar2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_different_values(self):
        """Test calendar inequality with different values."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=16, era_name="Third Age")

        assert calendar1 != calendar2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_different_era(self):
        """Test calendar inequality with different era names."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=15, era_name="Fourth Age")

        assert calendar1 != calendar2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_hash_consistency(self):
        """Test that equal calendars have the same hash."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")

        assert hash(calendar1) == hash(calendar2)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_hashable_in_set(self):
        """Test that calendars can be used in sets."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar3 = WorldCalendar(year=1042, month=3, day=16, era_name="Third Age")

        calendar_set = {calendar1, calendar2, calendar3}

        # calendar1 and calendar2 are equal, so set should have 2 elements
        assert len(calendar_set) == 2

    # ==================== Immutability Tests ====================

    @pytest.mark.unit
    def test_immutability_frozen_dataclass(self):
        """Test that calendar is immutable (frozen dataclass)."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")

        with pytest.raises(AttributeError):
            calendar.year = 1043  # Should fail due to frozen dataclass

    @pytest.mark.unit
    def test_advance_creates_new_instance(self):
        """Test that advance creates a new instance instead of modifying original."""
        original = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        result = original.advance(10)

        assert result.is_ok
        new_calendar = result.value

        # Original should remain unchanged
        assert original.year == 1042
        assert original.month == 3
        assert original.day == 15

        # New instance should be different object
        assert new_calendar is not original
        assert new_calendar.day == 25

    # ==================== Serialization Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_dict(self):
        """Test conversion to dictionary."""
        calendar = WorldCalendar(
            year=1042, month=3, day=15, era_name="Third Age", days_per_month=28
        )
        result = calendar.to_dict()

        assert result == {
            "year": 1042,
            "month": 3,
            "day": 15,
            "era_name": "Third Age",
            "days_per_month": 28,
            "months_per_year": 12,
        }

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "year": 1042,
            "month": 3,
            "day": 15,
            "era_name": "Third Age",
            "days_per_month": 28,
            "months_per_year": 13,
        }
        calendar = WorldCalendar.from_dict(data)

        assert calendar.year == 1042
        assert calendar.month == 3
        assert calendar.day == 15
        assert calendar.era_name == "Third Age"
        assert calendar.days_per_month == 28
        assert calendar.months_per_year == 13

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_with_defaults(self):
        """Test creation from dictionary with default values."""
        data = {"year": 1042, "month": 3, "day": 15, "era_name": "Third Age"}
        calendar = WorldCalendar.from_dict(data)

        assert calendar.days_per_month == 30
        assert calendar.months_per_year == 12

    @pytest.mark.unit
    @pytest.mark.fast
    def test_serialization_roundtrip(self):
        """Test that to_dict -> from_dict preserves all values."""
        original = WorldCalendar(
            year=1042, month=3, day=15, era_name="Third Age", days_per_month=28, months_per_year=13
        )
        data = original.to_dict()
        restored = WorldCalendar.from_dict(data)

        assert restored == original

    # ==================== Total Days and Days Until Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_total_days_first_day(self):
        """Test total_days for first day of calendar."""
        calendar = WorldCalendar(year=1, month=1, day=1, era_name="Start")
        assert calendar.total_days() == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_total_days_calculation(self):
        """Test total_days calculation."""
        # Year 2, Month 3, Day 5
        # = (2-1) * 12 * 30 + (3-1) * 30 + 5
        # = 360 + 60 + 5 = 425
        calendar = WorldCalendar(year=2, month=3, day=5, era_name="Test")
        assert calendar.total_days() == 425

    @pytest.mark.unit
    @pytest.mark.fast
    def test_days_until_future(self):
        """Test days_until for future date."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=25, era_name="Third Age")

        assert calendar1.days_until(calendar2) == 10

    @pytest.mark.unit
    @pytest.mark.fast
    def test_days_until_past(self):
        """Test days_until for past date."""
        calendar1 = WorldCalendar(year=1042, month=3, day=25, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")

        assert calendar1.days_until(calendar2) == -10

    @pytest.mark.unit
    @pytest.mark.fast
    def test_days_until_same_day(self):
        """Test days_until for same day."""
        calendar1 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        calendar2 = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")

        assert calendar1.days_until(calendar2) == 0

    # ==================== String Representation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation uses format()."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")

        assert str(calendar) == "Year 1042, Month 3, Day 15 - Third Age"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test detailed string representation."""
        calendar = WorldCalendar(
            year=1042, month=3, day=15, era_name="Third Age", days_per_month=28
        )
        repr_str = repr(calendar)

        assert "WorldCalendar" in repr_str
        assert "year=1042" in repr_str
        assert "month=3" in repr_str
        assert "day=15" in repr_str
        assert "era_name='Third Age'" in repr_str
        assert "days_per_month=28" in repr_str

    # ==================== Edge Cases ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_exact_year_boundary(self):
        """Test advancing exactly to year boundary."""
        calendar = WorldCalendar(
            year=1042, month=12, day=1, era_name="Third Age", days_per_month=30
        )
        # Advance exactly 30 days to reach next year
        result = calendar.advance(30)

        assert result.is_ok
        new_calendar = result.value
        assert new_calendar.year == 1043
        assert new_calendar.month == 1
        assert new_calendar.day == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_custom_calendar_system(self):
        """Test calendar with completely custom configuration."""
        # 10-day months, 20-month years
        calendar = WorldCalendar(
            year=1,
            month=1,
            day=1,
            era_name="Alien Era",
            days_per_month=10,
            months_per_year=20,
        )

        # Advance 10 days = 1 month
        result = calendar.advance(10)
        assert result.is_ok
        assert result.value.month == 2
        assert result.value.day == 1

        # Advance 200 days = 1 year (20 months * 10 days)
        result = calendar.advance(200)
        assert result.is_ok
        assert result.value.year == 2
        assert result.value.month == 1
        assert result.value.day == 1
