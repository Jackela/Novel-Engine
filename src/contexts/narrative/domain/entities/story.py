"""Story Entity - Root Aggregate for a Novel.

This module defines the Story entity, which serves as the root aggregate
for managing a complete novel or story within the Narrative bounded context.

Why Story as an aggregate root:
    A Story owns its chapters and controls the consistency boundaries for
    structural operations. All modifications to chapters should flow through
    the Story aggregate to maintain invariants like unique order indices
    and chapter limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .chapter import Chapter


class StoryStatus(str, Enum):
    """Publication status of a story.

    Why this enum:
        Stories move through a lifecycle from initial drafting to final
        publication. The status controls what operations are permitted
        (e.g., published stories may have restrictions on structural changes).
    """

    DRAFT = "draft"
    PUBLISHED = "published"


@dataclass
class Story:
    """Story Entity - The root aggregate for a novel.

    A Story represents a complete narrative work containing one or more
    chapters. It tracks metadata like title and summary, maintains the
    publication status, and owns the collection of chapters.

    Attributes:
        id: Unique identifier for the story.
        title: The title of the story.
        summary: A brief description or synopsis.
        status: Publication status (DRAFT or PUBLISHED).
        created_at: Timestamp when the story was created.
        updated_at: Timestamp of the last modification.

    Why these attributes:
        These are the minimum attributes needed to identify and describe
        a story. The status field enables workflow management while keeping
        the entity simple. Timestamps support audit trails.
    """

    title: str
    id: UUID = field(default_factory=uuid4)
    summary: str = ""
    status: StoryStatus = StoryStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Internal chapter collection - chapters are owned by the story
    _chapters: list[Chapter] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Validate story invariants after initialization.

        Why validation here:
            Ensures the story is always in a valid state, even when
            instantiated directly without going through a factory.
        """
        if not self.title or not self.title.strip():
            raise ValueError("Story title cannot be empty")

    @property
    def chapters(self) -> list[Chapter]:
        """Get a copy of chapters sorted by order_index.

        Why return a copy:
            Prevents external code from directly modifying the internal
            list, ensuring all modifications go through aggregate methods.
        """
        return sorted(self._chapters, key=lambda c: c.order_index)

    def add_chapter(self, chapter: Chapter) -> None:
        """Add a chapter to this story.

        Args:
            chapter: The chapter to add.

        Raises:
            ValueError: If a chapter with the same ID already exists.

        Why this method:
            Centralizes chapter addition to enforce invariants like
            preventing duplicate chapters.
        """
        if any(c.id == chapter.id for c in self._chapters):
            raise ValueError(f"Chapter with ID {chapter.id} already exists in story")

        self._chapters.append(chapter)
        self._touch()

    def remove_chapter(self, chapter_id: UUID) -> Optional[Chapter]:
        """Remove a chapter from this story.

        Args:
            chapter_id: The ID of the chapter to remove.

        Returns:
            The removed chapter, or None if not found.

        Why return the chapter:
            Allows callers to verify what was removed or use it for
            undo operations.
        """
        for i, chapter in enumerate(self._chapters):
            if chapter.id == chapter_id:
                removed = self._chapters.pop(i)
                self._touch()
                return removed
        return None

    def get_chapter(self, chapter_id: UUID) -> Optional[Chapter]:
        """Get a chapter by its ID.

        Args:
            chapter_id: The ID of the chapter to retrieve.

        Returns:
            The chapter if found, None otherwise.
        """
        for chapter in self._chapters:
            if chapter.id == chapter_id:
                return chapter
        return None

    def reorder_chapters(self, chapter_ids: list[UUID]) -> None:
        """Reorder chapters by providing the new order of IDs.

        Args:
            chapter_ids: List of chapter IDs in the desired order.

        Raises:
            ValueError: If the provided IDs don't match existing chapters.

        Why this approach:
            Accepting a complete ordering prevents partial updates that
            could leave the story in an inconsistent state.
        """
        existing_ids = {c.id for c in self._chapters}
        provided_ids = set(chapter_ids)

        if existing_ids != provided_ids:
            raise ValueError(
                "Provided chapter IDs must match existing chapters exactly"
            )

        # Create a mapping from ID to chapter
        id_to_chapter = {c.id: c for c in self._chapters}

        # Update order indices
        for index, chapter_id in enumerate(chapter_ids):
            id_to_chapter[chapter_id].order_index = index

        self._touch()

    def publish(self) -> None:
        """Publish the story.

        Why a method instead of direct status change:
            Publishing might have side effects or validations in the future
            (e.g., ensuring at least one chapter exists). Encapsulating
            this as a method allows for those extensions.
        """
        self.status = StoryStatus.PUBLISHED
        self._touch()

    def unpublish(self) -> None:
        """Return the story to draft status."""
        self.status = StoryStatus.DRAFT
        self._touch()

    def update_title(self, new_title: str) -> None:
        """Update the story title.

        Args:
            new_title: The new title for the story.

        Raises:
            ValueError: If the title is empty.
        """
        if not new_title or not new_title.strip():
            raise ValueError("Story title cannot be empty")
        self.title = new_title.strip()
        self._touch()

    def update_summary(self, new_summary: str) -> None:
        """Update the story summary."""
        self.summary = new_summary
        self._touch()

    def _touch(self) -> None:
        """Update the modification timestamp.

        Why a private method:
            Centralizes timestamp updates so we don't forget to update
            it when modifying the entity.
        """
        self.updated_at = datetime.now(timezone.utc)

    @property
    def chapter_count(self) -> int:
        """Get the number of chapters in this story."""
        return len(self._chapters)

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Story('{self.title}', {self.status.value}, {self.chapter_count} chapters)"
        )

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Story(id={self.id}, title='{self.title}', "
            f"status={self.status.value}, chapters={self.chapter_count})"
        )
