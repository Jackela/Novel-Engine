"""Chapter Entity - A container for scenes within a story.

This module defines the Chapter entity, which represents a logical division
within a Story. Chapters contain scenes and maintain their order within
the parent story.

Why Chapter as a separate entity:
    Chapters provide the structural hierarchy needed for novel organization.
    They serve as containers for scenes while being managed by the Story
    aggregate root.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ChapterStatus(str, Enum):
    """Publication status of a chapter.

    Why this enum:
        Individual chapters can have their own publication status,
        allowing for incremental publishing (e.g., serial novels)
        or marking chapters as work-in-progress within a published story.
    """

    DRAFT = "draft"
    PUBLISHED = "published"


@dataclass
class Chapter:
    """Chapter Entity - A container for scenes within a story.

    A Chapter represents a major division within a story. It has its own
    title, summary, and status, and maintains its position within the
    story through an order index.

    Attributes:
        id: Unique identifier for the chapter.
        story_id: Reference to the parent story.
        title: The title of the chapter.
        summary: A brief description or synopsis of the chapter.
        order_index: Position of the chapter within the story (0-based).
        status: Publication status (DRAFT or PUBLISHED).
        created_at: Timestamp when the chapter was created.
        updated_at: Timestamp of the last modification.

    Why these attributes:
        These capture the essential information for a chapter. The order_index
        enables reordering without changing IDs. The story_id reference
        maintains the relationship to the parent aggregate.
    """

    title: str
    story_id: UUID
    id: UUID = field(default_factory=uuid4)
    summary: str = ""
    order_index: int = 0
    status: ChapterStatus = ChapterStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate chapter invariants after initialization.

        Why validation here:
            Ensures the chapter is always in a valid state. Title validation
            prevents empty chapters, and order_index validation prevents
            negative indices.
        """
        if not self.title or not self.title.strip():
            raise ValueError("Chapter title cannot be empty")
        if self.order_index < 0:
            raise ValueError("Chapter order_index cannot be negative")

    def update_title(self, new_title: str) -> None:
        """Update the chapter title.

        Args:
            new_title: The new title for the chapter.

        Raises:
            ValueError: If the title is empty.
        """
        if not new_title or not new_title.strip():
            raise ValueError("Chapter title cannot be empty")
        self.title = new_title.strip()
        self._touch()

    def update_summary(self, new_summary: str) -> None:
        """Update the chapter summary."""
        self.summary = new_summary
        self._touch()

    def publish(self) -> None:
        """Publish the chapter.

        Why a method instead of direct status change:
            Encapsulating status changes allows for future validations
            or side effects (e.g., ensuring content exists before publishing).
        """
        self.status = ChapterStatus.PUBLISHED
        self._touch()

    def unpublish(self) -> None:
        """Return the chapter to draft status."""
        self.status = ChapterStatus.DRAFT
        self._touch()

    def move_to_position(self, new_index: int) -> None:
        """Update the chapter's position.

        Args:
            new_index: The new order index (0-based).

        Raises:
            ValueError: If the index is negative.

        Why this method:
            While order_index can be set directly, this method provides
            validation and timestamp updates in one operation.
        """
        if new_index < 0:
            raise ValueError("Chapter order_index cannot be negative")
        self.order_index = new_index
        self._touch()

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"Chapter('{self.title}', order={self.order_index}, {self.status.value})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Chapter(id={self.id}, story_id={self.story_id}, "
            f"title='{self.title}', order_index={self.order_index}, "
            f"status={self.status.value})"
        )
