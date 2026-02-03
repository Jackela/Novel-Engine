#!/usr/bin/env python3
"""
Character Memory Value Object

This module implements the CharacterMemory value object, which represents
a single memory that a character holds. Memories are immutable records of
past experiences, thoughts, or knowledge that shape character behavior.

Why memories matter:
    Memories drive character decisions and dialogue. A character who remembers
    being betrayed will act differently from one who remembers kindness. By
    making memories explicit and queryable, AI systems can generate more
    consistent and contextual character behavior.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import uuid4


@dataclass(frozen=True)
class CharacterMemory:
    """
    Value object representing a single character memory.

    Memories are immutable records that characters accumulate over time.
    Each memory has:
    - content: What the character remembers (a narrative description)
    - importance: How significant this memory is (1-10 scale)
    - tags: Categorization for retrieval (e.g., ["betrayal", "family"])
    - timestamp: When the memory was formed
    - memory_id: Unique identifier for the memory

    Importance scale:
    - 1-3: Minor memories (daily routines, passing encounters)
    - 4-6: Moderate memories (friendships, minor conflicts)
    - 7-8: Significant memories (major life events, turning points)
    - 9-10: Core memories (defining moments, traumas, transformations)

    This is immutable following DDD value object principles.
    """

    content: str
    importance: int
    tags: tuple  # Using tuple for immutability (frozen dataclass)
    timestamp: datetime = field(default_factory=datetime.now)
    memory_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate memory data upon creation."""
        # Validate content
        if not isinstance(self.content, str):
            raise TypeError(
                f"content must be a string, got {type(self.content).__name__}"
            )
        if not self.content.strip():
            raise ValueError("content cannot be empty")

        # Validate importance (1-10 scale)
        if not isinstance(self.importance, int):
            raise TypeError(
                f"importance must be an integer, got {type(self.importance).__name__}"
            )
        if self.importance < 1 or self.importance > 10:
            raise ValueError(
                f"importance must be between 1 and 10, got {self.importance}"
            )

        # Validate tags
        if not isinstance(self.tags, (tuple, list)):
            raise TypeError(
                f"tags must be a tuple or list, got {type(self.tags).__name__}"
            )
        for tag in self.tags:
            if not isinstance(tag, str):
                raise TypeError(f"each tag must be a string, got {type(tag).__name__}")
            if not tag.strip():
                raise ValueError("tags cannot contain empty strings")

        # Convert list to tuple if needed (for frozen dataclass)
        if isinstance(self.tags, list):
            object.__setattr__(self, "tags", tuple(self.tags))

        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"timestamp must be a datetime, got {type(self.timestamp).__name__}"
            )

        # Validate memory_id
        if not isinstance(self.memory_id, str):
            raise TypeError(
                f"memory_id must be a string, got {type(self.memory_id).__name__}"
            )
        if not self.memory_id.strip():
            raise ValueError("memory_id cannot be empty")

    def is_core_memory(self) -> bool:
        """
        Check if this is a core memory (importance > 8).

        Why this matters: Core memories are the defining experiences that
        shape a character's identity. They should be highlighted in UI
        and given priority in AI context building.

        Returns:
            True if importance > 8
        """
        return self.importance > 8

    def has_tag(self, tag: str) -> bool:
        """
        Check if this memory has a specific tag.

        Args:
            tag: The tag to search for (case-insensitive)

        Returns:
            True if the tag is present
        """
        return tag.lower() in [t.lower() for t in self.tags]

    def get_importance_level(self) -> str:
        """
        Get a qualitative description of memory importance.

        Returns:
            'minor', 'moderate', 'significant', or 'core'
        """
        if self.importance <= 3:
            return "minor"
        elif self.importance <= 6:
            return "moderate"
        elif self.importance <= 8:
            return "significant"
        else:
            return "core"

    def to_dict(self) -> dict:
        """
        Convert memory to dictionary format.

        Returns:
            Dict with all memory fields
        """
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "importance": self.importance,
            "tags": list(self.tags),
            "timestamp": self.timestamp.isoformat(),
            "is_core_memory": self.is_core_memory(),
            "importance_level": self.get_importance_level(),
        }

    def get_summary(self) -> str:
        """
        Get a brief summary of the memory for display.

        Returns:
            A one-line summary with importance and first 50 chars of content
        """
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        level = self.get_importance_level().upper()
        return f"[{level}] {content_preview}"

    @classmethod
    def create(
        cls,
        content: str,
        importance: int,
        tags: List[str],
        timestamp: datetime = None,
    ) -> "CharacterMemory":
        """
        Factory method to create a new memory.

        Args:
            content: The memory content
            importance: Importance score (1-10)
            tags: List of tags for categorization
            timestamp: When the memory was formed (defaults to now)

        Returns:
            A new CharacterMemory instance
        """
        return cls(
            content=content,
            importance=importance,
            tags=tuple(tags),
            timestamp=timestamp or datetime.now(),
        )
