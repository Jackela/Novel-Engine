#!/usr/bin/env python3
"""
Turn Identity Value Object

Immutable identifier for turn instances with sequence tracking,
validation, and factory methods for different turn types.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TurnId:
    """
    Immutable value object representing a unique turn identifier.

    Encapsulates turn identification with sequence tracking, validation,
    and support for both auto-generated and custom turn IDs.

    Attributes:
        turn_uuid: Unique UUID for the turn instance
        sequence_number: Optional sequential turn number
        campaign_id: Optional campaign identifier for grouping
        custom_name: Optional human-readable turn name
        created_at: Timestamp when turn ID was created

    Business Rules:
        - Turn UUID must be valid UUID format
        - Sequence number must be positive if provided
        - Custom name must follow naming conventions if provided
        - Campaign ID must be valid UUID if provided
    """

    turn_uuid: UUID
    sequence_number: Optional[int] = None
    campaign_id: Optional[UUID] = None
    custom_name: Optional[str] = None
    created_at: datetime = None

    # Class-level validation patterns
    _CUSTOM_NAME_PATTERN: ClassVar[str] = r"^[a-zA-Z0-9_-]{1,50}$"
    _RESERVED_NAMES: ClassVar[set] = {"test", "debug", "system", "admin", "root", "api"}

    def __post_init__(self):
        """Validate turn ID structure and business rules."""
        # Set created_at if not provided
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now())

        # Validate UUID format
        if not isinstance(self.turn_uuid, UUID):
            raise ValueError("turn_uuid must be a valid UUID")

        # Validate sequence number
        if self.sequence_number is not None:
            if not isinstance(self.sequence_number, int) or self.sequence_number < 1:
                raise ValueError("sequence_number must be a positive integer")

        # Validate campaign ID
        if self.campaign_id is not None:
            if not isinstance(self.campaign_id, UUID):
                raise ValueError("campaign_id must be a valid UUID")

        # Validate custom name
        if self.custom_name is not None:
            self._validate_custom_name(self.custom_name)

    def _validate_custom_name(self, name: str) -> None:
        """Validate custom name follows conventions."""
        if not isinstance(name, str):
            raise ValueError("custom_name must be a string")

        if not re.match(self._CUSTOM_NAME_PATTERN, name):
            raise ValueError(
                "custom_name must contain only alphanumeric characters, "
                "hyphens, and underscores (1-50 characters)"
            )

        if name.lower() in self._RESERVED_NAMES:
            raise ValueError(f"custom_name '{name}' is reserved")

    @classmethod
    def generate(
        cls,
        sequence_number: Optional[int] = None,
        campaign_id: Optional[UUID] = None,
        custom_name: Optional[str] = None,
    ) -> "TurnId":
        """
        Generate a new turn ID with optional parameters.

        Args:
            sequence_number: Optional sequential turn number
            campaign_id: Optional campaign grouping identifier
            custom_name: Optional human-readable name

        Returns:
            New TurnId instance with generated UUID
        """
        return cls(
            turn_uuid=uuid4(),
            sequence_number=sequence_number,
            campaign_id=campaign_id,
            custom_name=custom_name,
            created_at=datetime.now(),
        )

    @classmethod
    def from_string(cls, turn_string: str) -> "TurnId":
        """
        Create TurnId from string representation.

        Args:
            turn_string: String representation of turn ID

        Returns:
            TurnId instance parsed from string

        Raises:
            ValueError: If string format is invalid
        """
        try:
            # Handle UUID-only strings
            if len(turn_string.replace("-", "")) == 32:
                return cls(turn_uuid=UUID(turn_string))

            # Handle formatted strings with sequence/campaign info
            # Format: "uuid[|seq_num][|campaign_id][|custom_name]"
            parts = turn_string.split("|")

            turn_uuid = UUID(parts[0])
            sequence_number = int(parts[1]) if len(parts) > 1 and parts[1] else None
            campaign_id = UUID(parts[2]) if len(parts) > 2 and parts[2] else None
            custom_name = parts[3] if len(parts) > 3 and parts[3] else None

            return cls(
                turn_uuid=turn_uuid,
                sequence_number=sequence_number,
                campaign_id=campaign_id,
                custom_name=custom_name,
            )

        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid turn string format: {turn_string}") from e

    @classmethod
    def create_sequenced(cls, sequence_number: int, campaign_id: Optional[UUID] = None) -> "TurnId":
        """
        Create a sequenced turn ID for campaign progression.

        Args:
            sequence_number: Sequential turn number in campaign
            campaign_id: Campaign identifier for grouping

        Returns:
            TurnId with sequence tracking
        """
        return cls.generate(sequence_number=sequence_number, campaign_id=campaign_id)

    @classmethod
    def create_named(cls, custom_name: str, campaign_id: Optional[UUID] = None) -> "TurnId":
        """
        Create a named turn ID for special turns.

        Args:
            custom_name: Human-readable turn name
            campaign_id: Optional campaign grouping

        Returns:
            TurnId with custom name
        """
        return cls.generate(custom_name=custom_name, campaign_id=campaign_id)

    def to_short_string(self) -> str:
        """
        Get short string representation for logging.

        Returns:
            Abbreviated string representation
        """
        uuid_short = str(self.turn_uuid)[:8]

        if self.custom_name:
            return f"{self.custom_name}({uuid_short})"
        elif self.sequence_number:
            return f"turn_{self.sequence_number}({uuid_short})"
        else:
            return uuid_short

    def to_full_string(self) -> str:
        """
        Get full string representation for persistence.

        Returns:
            Complete string representation with all fields
        """
        parts = [str(self.turn_uuid)]

        if self.sequence_number is not None:
            parts.append(str(self.sequence_number))
        else:
            parts.append("")

        if self.campaign_id is not None:
            parts.append(str(self.campaign_id))
        else:
            parts.append("")

        if self.custom_name is not None:
            parts.append(self.custom_name)
        else:
            parts.append("")

        return "|".join(parts)

    def is_sequenced(self) -> bool:
        """Check if this is a sequenced turn."""
        return self.sequence_number is not None

    def is_named(self) -> bool:
        """Check if this is a named turn."""
        return self.custom_name is not None

    def belongs_to_campaign(self, campaign_id: UUID) -> bool:
        """Check if turn belongs to specific campaign."""
        return self.campaign_id == campaign_id

    def get_display_name(self) -> str:
        """
        Get human-readable display name for UI.

        Returns:
            Formatted display name based on available information
        """
        if self.custom_name:
            if self.sequence_number:
                return f"{self.custom_name} (Turn #{self.sequence_number})"
            else:
                return self.custom_name
        elif self.sequence_number:
            return f"Turn #{self.sequence_number}"
        else:
            return f"Turn {str(self.turn_uuid)[:8]}..."

    def __str__(self) -> str:
        """String representation for general use."""
        return self.to_short_string()

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"TurnId(uuid={self.turn_uuid}, seq={self.sequence_number}, "
            f"campaign={self.campaign_id}, name={self.custom_name})"
        )
