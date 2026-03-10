#!/usr/bin/env python3
"""
Character Reaction Value Object

This module implements the CharacterReaction value object, which represents
a character's emotional or behavioral response to a world event.

Why reactions matter:
    Reactions connect characters to the world around them. When significant
    events occur, characters respond based on their personality, relationships,
    and circumstances. This creates dynamic storytelling where events have
    personal impact beyond their immediate scope.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class ReactionType(str, Enum):
    """Types of reactions a character can have to events.

    Why use an enum: Reactions have a limited set of valid types.
    Using an enum ensures type safety and makes reaction handling
    consistent across the system.
    """

    OBSERVE = "OBSERVE"
    FLEE = "FLEE"
    INVESTIGATE = "INVESTIGATE"
    IGNORE = "IGNORE"
    CELEBRATE = "CELEBRATE"
    MOURN = "MOURN"
    PROTEST = "PROTEST"

    @property
    def is_active(self) -> bool:
        """Check if this reaction type involves active engagement.

        Returns:
            True if the character actively does something (not passive observation)
        """
        return self in (
            ReactionType.FLEE,
            ReactionType.INVESTIGATE,
            ReactionType.CELEBRATE,
            ReactionType.PROTEST,
        )

    @property
    def is_emotional(self) -> bool:
        """Check if this reaction type is primarily emotional.

        Returns:
            True if the reaction expresses emotion (celebrate, mourn, protest)
        """
        return self in (
            ReactionType.CELEBRATE,
            ReactionType.MOURN,
            ReactionType.PROTEST,
        )

    @property
    def creates_memory(self) -> bool:
        """Check if this reaction type should create a memory.

        Returns:
            True if the reaction is significant enough to be remembered
        """
        return self != ReactionType.IGNORE


@dataclass(frozen=True)
class CharacterReaction:
    """
    Value object representing a character's reaction to a world event.

    Reactions capture how characters respond to events in the world.
    They determine the narrative flavor of events and can trigger
    follow-on behaviors or memories.

    Attributes:
        reaction_id: Unique identifier for this reaction
        character_id: ID of the character having the reaction
        event_id: ID of the event being reacted to
        reaction_type: Type of reaction (OBSERVE, FLEE, etc.)
        intensity: How strongly the character reacts (1-10)
        narrative: Human-readable description of the reaction
        memory_created: Whether this reaction created a memory
        created_at: When the reaction occurred

    This is immutable following DDD value object principles.
    """

    character_id: str
    event_id: str
    reaction_type: ReactionType
    intensity: int
    narrative: str
    memory_created: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    reaction_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate reaction data upon creation."""
        super().__setattr__("__validated__", True)  # Mark validation complete
        # Validate reaction_id
        if not isinstance(self.reaction_id, str):
            raise TypeError(
                f"reaction_id must be a string, got {type(self.reaction_id).__name__}"
            )
        if not self.reaction_id.strip():
            raise ValueError("reaction_id cannot be empty")

        # Validate character_id
        if not isinstance(self.character_id, str):
            raise TypeError(
                f"character_id must be a string, got {type(self.character_id).__name__}"
            )
        if not self.character_id.strip():
            raise ValueError("character_id cannot be empty")

        # Validate event_id
        if not isinstance(self.event_id, str):
            raise TypeError(
                f"event_id must be a string, got {type(self.event_id).__name__}"
            )
        if not self.event_id.strip():
            raise ValueError("event_id cannot be empty")

        # Validate reaction_type
        if isinstance(self.reaction_type, str):
            try:
                object.__setattr__(
                    self, "reaction_type", ReactionType(self.reaction_type)
                )
            except ValueError:
                raise ValueError(
                    f"Invalid reaction_type: {self.reaction_type}. "
                    f"Must be one of: {[r.value for r in ReactionType]}"
                )
        elif not isinstance(self.reaction_type, ReactionType):
            raise TypeError(
                f"reaction_type must be a ReactionType, "
                f"got {type(self.reaction_type).__name__}"
            )

        # Validate intensity (1-10)
        if not isinstance(self.intensity, int):
            raise TypeError(
                f"intensity must be an int, got {type(self.intensity).__name__}"
            )
        if self.intensity < 1 or self.intensity > 10:
            raise ValueError(
                f"intensity must be between 1 and 10, got {self.intensity}"
            )

        # Validate narrative
        if not isinstance(self.narrative, str):
            raise TypeError(
                f"narrative must be a string, got {type(self.narrative).__name__}"
            )
        if not self.narrative.strip():
            raise ValueError("narrative cannot be empty")

        # Validate memory_created
        if not isinstance(self.memory_created, bool):
            raise TypeError(
                f"memory_created must be a bool, got {type(self.memory_created).__name__}"
            )

        # Validate created_at
        if not isinstance(self.created_at, datetime):
            raise TypeError(
                f"created_at must be a datetime, got {type(self.created_at).__name__}"
            )

    def is_intense(self, threshold: int = 7) -> bool:
        """Check if this reaction exceeds an intensity threshold.

        Args:
            threshold: The intensity level to check against (default 7)

        Returns:
            True if intensity >= threshold
        """
        return self.intensity >= threshold

    def is_mild(self) -> bool:
        """Check if this is a mild reaction.

        Returns:
            True if intensity <= 3
        """
        return self.intensity <= 3

    def should_create_memory(self) -> bool:
        """Determine if this reaction should create a memory.

        A reaction should create a memory if:
        - It's not an IGNORE reaction (by type)
        - Intensity is >= 4 (mild reactions may not be memorable)

        Returns:
            True if a memory should be created
        """
        return self.reaction_type.creates_memory and self.intensity >= 4

    def with_memory_created(self) -> "CharacterReaction":
        """Create a new reaction instance with memory_created set to True.

        Why return a new instance: CharacterReaction is immutable, so state
        changes create new instances.

        Returns:
            A new CharacterReaction with memory_created=True
        """
        return CharacterReaction(
            reaction_id=self.reaction_id,
            character_id=self.character_id,
            event_id=self.event_id,
            reaction_type=self.reaction_type,
            intensity=self.intensity,
            narrative=self.narrative,
            memory_created=True,
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert reaction to dictionary format.

        Returns:
            Dict with all reaction fields
        """
        return {
            "reaction_id": self.reaction_id,
            "character_id": self.character_id,
            "event_id": self.event_id,
            "reaction_type": self.reaction_type.value,
            "intensity": self.intensity,
            "narrative": self.narrative,
            "memory_created": self.memory_created,
            "created_at": self.created_at.isoformat(),
            "is_intense": self.is_intense(),
            "is_mild": self.is_mild(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CharacterReaction":
        """Create a CharacterReaction from a dictionary.

        Args:
            data: Dictionary containing reaction data

        Returns:
            A new CharacterReaction instance
        """
        # Parse reaction_type
        reaction_type_raw = data.get("reaction_type")
        if isinstance(reaction_type_raw, str):
            reaction_type: ReactionType = ReactionType(reaction_type_raw)
        elif isinstance(reaction_type_raw, ReactionType):
            reaction_type = reaction_type_raw
        else:
            raise ValueError(
                "reaction_type is required and must be a string or ReactionType"
            )

        # Parse created_at
        created_at_raw = data.get("created_at")
        if isinstance(created_at_raw, str):
            created_at: datetime = datetime.fromisoformat(created_at_raw)
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now()

        reaction_id_raw = data.get("reaction_id")
        reaction_id = str(reaction_id_raw) if reaction_id_raw else str(uuid4())

        return cls(
            reaction_id=reaction_id,
            character_id=str(data["character_id"]),
            event_id=str(data["event_id"]),
            reaction_type=reaction_type,
            intensity=int(data.get("intensity", 5)) if data.get("intensity") is not None else 5,  # type: ignore[call-overload]
            narrative=str(data["narrative"]),
            memory_created=bool(data.get("memory_created", False)),
            created_at=created_at,
        )

    @classmethod
    def create(
        cls,
        character_id: str,
        event_id: str,
        reaction_type: ReactionType,
        intensity: int,
        narrative: str,
        memory_created: bool = False,
    ) -> "CharacterReaction":
        """Factory method to create a new reaction.

        Args:
            character_id: ID of the character reacting
            event_id: ID of the event being reacted to
            reaction_type: Type of reaction
            intensity: How strongly (1-10)
            narrative: Description of the reaction
            memory_created: Whether a memory was created (default False)

        Returns:
            A new CharacterReaction instance
        """
        return cls(
            character_id=character_id,
            event_id=event_id,
            reaction_type=reaction_type,
            intensity=intensity,
            narrative=narrative,
            memory_created=memory_created,
        )
