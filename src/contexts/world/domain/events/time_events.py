#!/usr/bin/env python3
"""
Time Domain Events

This module contains domain events specifically for time/calendar operations.
These events provide detailed information about time advancement in the world.

The TimeAdvancedEvent is a focused event for time changes, distinct from the
more general WorldStateChanged event, allowing for specific time-based handlers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog

from src.events.event_bus import Event, EventPriority

logger = structlog.get_logger()


@dataclass
class TimeAdvancedEvent(Event):
    """
    Domain event emitted when world time is advanced.

    This event provides detailed information about time changes including
    the previous date, new date, and the number of days advanced. It follows
    the enterprise event bus patterns for integration with other systems.

    Attributes:
        previous_date: Dictionary containing the date before advancement
            (year, month, day, era_name)
        new_date: Dictionary containing the date after advancement
            (year, month, day, era_name)
        days_advanced: Number of days the calendar was advanced

    Example:
        >>> event = TimeAdvancedEvent(
        ...     previous_date={"year": 1042, "month": 5, "day": 10, "era_name": "Third Age"},
        ...     new_date={"year": 1042, "month": 5, "day": 15, "era_name": "Third Age"},
        ...     days_advanced=5
        ... )
    """

    # Override base event fields
    event_type: str = field(default="world.time_advanced", init=False)
    source: str = field(default="calendar_service")
    priority: EventPriority = field(default=EventPriority.HIGH, init=False)

    # Time-specific event data
    previous_date: Dict[str, Any] = field(default_factory=dict)
    new_date: Dict[str, Any] = field(default_factory=dict)
    days_advanced: int = 0

    def __post_init__(self) -> None:
        """Initialize event with time-specific metadata and validation."""
        # Set timestamp if not provided
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

        # Generate event ID if not provided
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid4()))

        # Add time-specific tags
        self.tags.update({
            "context:world",
            "event:time_advanced",
            f"days_advanced:{self.days_advanced}",
        })

        # Set event payload with time data
        self.payload.update({
            "previous_date": self.previous_date,
            "new_date": self.new_date,
            "days_advanced": self.days_advanced,
        })

        # Call parent post_init
        super().__post_init__()

        # Validate event data
        self._validate_time_event()

    def _validate_time_event(self) -> None:
        """
        Validate time event data.

        Raises:
            ValueError: If event data is invalid
        """
        errors = []

        # Validate days_advanced
        if self.days_advanced < 0:
            errors.append(f"days_advanced must be >= 0, got {self.days_advanced}")

        # Validate previous_date has required fields
        required_date_fields = {"year", "month", "day"}
        if self.previous_date:
            missing = required_date_fields - set(self.previous_date.keys())
            if missing:
                errors.append(f"previous_date missing fields: {missing}")

        # Validate new_date has required fields
        if self.new_date:
            missing = required_date_fields - set(self.new_date.keys())
            if missing:
                errors.append(f"new_date missing fields: {missing}")

        if errors:
            # Log validation failure before raising
            logger.warning(
                "time_event_validation_failed",
                event_id=self.event_id,
                errors=errors,
                days_advanced=self.days_advanced,
                previous_date=self.previous_date,
                new_date=self.new_date,
            )
            raise ValueError(f"TimeAdvancedEvent validation failed: {'; '.join(errors)}")

    @classmethod
    def create(
        cls,
        previous_date: Dict[str, Any],
        new_date: Dict[str, Any],
        days_advanced: int,
        world_id: Optional[str] = None,
        source: str = "calendar_service",
    ) -> "TimeAdvancedEvent":
        """
        Factory method to create a TimeAdvancedEvent with validation.

        Args:
            previous_date: Date before advancement (must include year, month, day)
            new_date: Date after advancement (must include year, month, day)
            days_advanced: Number of days advanced (must be >= 0)
            world_id: Optional world identifier for multi-world scenarios
            source: Event source identifier

        Returns:
            TimeAdvancedEvent instance

        Example:
            >>> event = TimeAdvancedEvent.create(
            ...     previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            ...     new_date={"year": 1, "month": 1, "day": 6, "era_name": "First Age"},
            ...     days_advanced=5
            ... )
        """
        event = cls(
            previous_date=previous_date,
            new_date=new_date,
            days_advanced=days_advanced,
            source=source,
        )

        if world_id:
            event.tags.add(f"world:{world_id}")
            event.payload["world_id"] = world_id

        return event

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the time advancement.

        Returns:
            String summary of the time change
        """
        prev = self.previous_date
        new = self.new_date
        era = new.get("era_name", "Unknown Era")

        return (
            f"Advanced {self.days_advanced} day(s): "
            f"{prev.get('year', '?')}/{prev.get('month', '?')}/{prev.get('day', '?')} -> "
            f"{new.get('year', '?')}/{new.get('month', '?')}/{new.get('day', '?')} ({era})"
        )
