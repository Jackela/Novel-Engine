"""Beat Entity - The atomic unit of narrative.

This module defines the Beat entity, which represents a single moment or
action within a scene. Beats are the smallest unit of storytelling and
correspond to individual LLM generation chunks.

Why Beat as a separate entity:
    Beats provide granular control over narrative flow. Each beat can
    represent a distinct narrative function (action, reaction, revelation)
    making them ideal for fine-grained editing and generation control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class BeatType(str, Enum):
    """Classification of narrative beats.

    Why this enum:
        Different beat types serve different narrative functions. This
        classification helps the LLM generate appropriate content and
        assists writers in pacing their scenes.

    Beat types based on common screenplay/novel writing theory:
        - ACTION: Physical activity or movement
        - DIALOGUE: Character speech
        - REACTION: Emotional or physical response
        - REVELATION: New information or discovery
        - TRANSITION: Movement between states or locations
        - DESCRIPTION: Setting or character description
    """

    ACTION = "action"
    DIALOGUE = "dialogue"
    REACTION = "reaction"
    REVELATION = "revelation"
    TRANSITION = "transition"
    DESCRIPTION = "description"


@dataclass
class Beat:
    """Beat Entity - The atomic unit of narrative.

    A Beat represents a single moment or action within a scene. It is the
    smallest unit of storytelling that can be independently generated,
    edited, or reordered.

    Attributes:
        id: Unique identifier for the beat.
        scene_id: Reference to the parent scene.
        content: The actual narrative text of the beat.
        order_index: Position of the beat within the scene (0-based).
        beat_type: Classification of the beat's narrative function.
        notes: Optional authorial notes or comments.
        created_at: Timestamp when the beat was created.
        updated_at: Timestamp of the last modification.

    Why these attributes:
        Content is the core text. Beat_type provides semantic classification
        for better generation and analysis. Notes allow for meta-commentary
        without polluting the narrative content.
    """

    scene_id: UUID
    id: UUID = field(default_factory=uuid4)
    content: str = ""
    order_index: int = 0
    beat_type: BeatType = BeatType.ACTION
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate beat invariants after initialization.

        Why validation here:
            Ensures the beat is always in a valid state. Order_index
            validation prevents negative indices. Unlike Scene and Chapter,
            empty content is allowed (for placeholder beats).
        """
        if self.order_index < 0:
            raise ValueError("Beat order_index cannot be negative")

    def update_content(self, new_content: str) -> None:
        """Update the beat's narrative content.

        Args:
            new_content: The new text for this beat.

        Why no validation:
            Empty content is valid for beats (placeholder or deleted content).
            Validation of narrative quality is the LLM's responsibility.
        """
        self.content = new_content
        self._touch()

    def append_content(self, additional_content: str) -> None:
        """Append content to the beat (useful for streaming).

        Args:
            additional_content: Text to append to existing content.

        Why this method:
            Supports streaming LLM generation where content arrives in
            chunks. Rather than replacing content each time, we append.
        """
        self.content += additional_content
        self._touch()

    def change_type(self, new_type: BeatType) -> None:
        """Change the beat's narrative classification.

        Args:
            new_type: The new beat type.
        """
        self.beat_type = new_type
        self._touch()

    def update_notes(self, new_notes: str) -> None:
        """Update authorial notes."""
        self.notes = new_notes
        self._touch()

    def move_to_position(self, new_index: int) -> None:
        """Update the beat's position within its scene.

        Args:
            new_index: The new order index (0-based).

        Raises:
            ValueError: If the index is negative.
        """
        if new_index < 0:
            raise ValueError("Beat order_index cannot be negative")
        self.order_index = new_index
        self._touch()

    def is_empty(self) -> bool:
        """Check if the beat has no content.

        Returns:
            True if content is empty or whitespace-only.

        Why this method:
            Useful for cleanup operations or validation before publishing.
        """
        return not self.content or not self.content.strip()

    def word_count(self) -> int:
        """Get the word count of the beat's content.

        Returns:
            Number of words in the content.

        Why this method:
            Word count is a common metric for writing progress tracking.
        """
        if not self.content:
            return 0
        return len(self.content.split())

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """Human-readable representation."""
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Beat({self.beat_type.value}, order={self.order_index}, '{preview}')"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Beat(id={self.id}, scene_id={self.scene_id}, "
            f"beat_type={self.beat_type.value}, order_index={self.order_index}, "
            f"content_len={len(self.content)})"
        )
