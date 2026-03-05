#!/usr/bin/env python3
"""
WorldCalendar Value Object

This module provides the WorldCalendar value object for representing in-game
time with custom calendar systems. Following Domain-Driven Design principles,
this value object is immutable and encapsulates calendar-related logic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.core.result import Err, Ok, Result


@dataclass(frozen=True)
class WorldCalendar:
    """
    Immutable value object representing a custom calendar date.

    This value object encapsulates in-game time with support for custom
    month/year lengths and named eras. It provides methods for advancing
    time and formatting display strings.

    Attributes:
        year: Year number (must be >= 1)
        month: Month number (1 to months_per_year)
        day: Day number (1 to days_per_month)
        era_name: Name of the current era (e.g., "Third Age")
        days_per_month: Number of days per month (default: 30)
        months_per_year: Number of months per year (default: 12)
    """

    year: int
    month: int
    day: int
    era_name: str
    days_per_month: int = 30
    months_per_year: int = 12

    def __post_init__(self) -> None:
        """
        Validate calendar values after initialization.

        Raises:
            ValueError: If any calendar values are invalid
        """
        errors: list[Any] = []
        if self.year < 1:
            errors.append(f"Year must be >= 1, got {self.year}")

        if self.month < 1 or self.month > self.months_per_year:
            errors.append(
                f"Month must be between 1 and {self.months_per_year}, got {self.month}"
            )

        if self.day < 1 or self.day > self.days_per_month:
            errors.append(
                f"Day must be between 1 and {self.days_per_month}, got {self.day}"
            )

        if self.days_per_month < 1:
            errors.append(f"Days per month must be >= 1, got {self.days_per_month}")

        if self.months_per_year < 1:
            errors.append(f"Months per year must be >= 1, got {self.months_per_year}")

        if not self.era_name or not self.era_name.strip():
            errors.append("Era name cannot be empty")

        if errors:
            raise ValueError(f"Invalid calendar: {'; '.join(errors)}")

    def advance(self, days: int) -> Result["WorldCalendar", ValueError]:
        """
        Advance the calendar by a specified number of days.

        Args:
            days: Number of days to advance (must be >= 0)

        Returns:
            Result containing new WorldCalendar or ValueError if days < 0

        Example:
            >>> calendar = WorldCalendar(1042, 3, 15, "Third Age")
            >>> result = calendar.advance(20)
            >>> result.value  # Year 1042, Month 4, Day 4
        """
        if days < 0:
            return Err(ValueError("Days to advance must be >= 0"))

        if days == 0:
            return Ok(self)

        new_day = self.day + days
        new_month = self.month
        new_year = self.year

        # Handle day overflow
        while new_day > self.days_per_month:
            new_day -= self.days_per_month
            new_month += 1

            # Handle month overflow
            if new_month > self.months_per_year:
                new_month = 1
                new_year += 1

        try:
            return Ok(
                WorldCalendar(
                    year=new_year,
                    month=new_month,
                    day=new_day,
                    era_name=self.era_name,
                    days_per_month=self.days_per_month,
                    months_per_year=self.months_per_year,
                )
            )
        except ValueError as e:
            return Err(e)

    def format(self) -> str:
        """
        Format the calendar date as a human-readable string.

        Returns:
            Formatted date string (e.g., "Year 1042, Month 3, Day 15 - Third Age")
        """
        return f"Year {self.year}, Month {self.month}, Day {self.day} - {self.era_name}"

    @classmethod
    def from_datetime(cls, dt: datetime) -> "WorldCalendar":
        """
        Create a WorldCalendar from a Python datetime object.

        Args:
            dt: Datetime object to convert

        Returns:
            New WorldCalendar with default configuration

        Example:
            >>> from datetime import datetime
            >>> dt = datetime(2024, 6, 15)
            >>> calendar = WorldCalendar.from_datetime(dt)
            >>> calendar.year  # 2024
        """
        return cls(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            era_name="Modern Era",
            days_per_month=31,  # Use max to avoid validation errors
            months_per_year=12,
        )

    @classmethod
    def validate(
        cls,
        year: int,
        month: int,
        day: int,
        era_name: str,
        days_per_month: int = 30,
        months_per_year: int = 12,
    ) -> Result["WorldCalendar", ValueError]:
        """
        Validate and create a WorldCalendar, returning a Result.

        Args:
            year: Year number (must be >= 1)
            month: Month number (1 to months_per_year)
            day: Day number (1 to days_per_month)
            era_name: Name of the current era
            days_per_month: Number of days per month (default: 30)
            months_per_year: Number of months per year (default: 12)

        Returns:
            Result containing WorldCalendar or ValueError for invalid values

        Example:
            >>> result = WorldCalendar.validate(1042, 3, 15, "Third Age")
            >>> result.is_ok  # True
            >>> result = WorldCalendar.validate(1042, 13, 15, "Third Age")
            >>> result.is_error  # True (invalid month)
        """
        try:
            calendar = cls(
                year=year,
                month=month,
                day=day,
                era_name=era_name,
                days_per_month=days_per_month,
                months_per_year=months_per_year,
            )
            return Ok(calendar)
        except ValueError as e:
            return Err(e)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert calendar to dictionary representation.

        Returns:
            Dictionary with all calendar fields
        """
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "era_name": self.era_name,
            "days_per_month": self.days_per_month,
            "months_per_year": self.months_per_year,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldCalendar":
        """
        Create a WorldCalendar from dictionary representation.

        Args:
            data: Dictionary with calendar data

        Returns:
            New WorldCalendar instance

        Raises:
            KeyError: If required keys are missing
            ValueError: If values are invalid
        """
        return cls(
            year=data["year"],
            month=data["month"],
            day=data["day"],
            era_name=data["era_name"],
            days_per_month=data.get("days_per_month", 30),
            months_per_year=data.get("months_per_year", 12),
        )

    def total_days(self) -> int:
        """
        Calculate total days since year 1, month 1, day 1.

        This is useful for comparing two calendar dates or calculating
        the number of days between them.

        Returns:
            Total number of days since calendar epoch
        """
        # Days from complete years (year 1 to year-1)
        days_from_years = (self.year - 1) * self.months_per_year * self.days_per_month

        # Days from complete months in current year (month 1 to month-1)
        days_from_months = (self.month - 1) * self.days_per_month

        # Days in current month
        return days_from_years + days_from_months + self.day

    def days_until(self, other: "WorldCalendar") -> int:
        """
        Calculate the number of days until another calendar date.

        Args:
            other: Target calendar date

        Returns:
            Number of days (positive if other is in the future, negative if in the past)
        """
        return other.total_days() - self.total_days()

    def __str__(self) -> str:
        """
        String representation of the calendar.

        Returns:
            Formatted date string
        """
        return self.format()

    def __repr__(self) -> str:
        """
        Detailed string representation.

        Returns:
            Detailed string with all fields
        """
        return (
            f"WorldCalendar(year={self.year}, month={self.month}, day={self.day}, "
            f"era_name='{self.era_name}', days_per_month={self.days_per_month}, "
            f"months_per_year={self.months_per_year})"
        )
