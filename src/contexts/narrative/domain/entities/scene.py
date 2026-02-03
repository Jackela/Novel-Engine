"""Scene Entity - A dramatic unit within a chapter.

This module defines the Scene entity, which represents a continuous action
sequence in a specific time and place. Scenes are the primary unit of
storytelling and contain beats (atomic narrative moments).

Why Scene as a separate entity:
    Scenes provide the natural unit for writing and editing. A scene has
    unity of time, place, and action, making it the ideal container for
    LLM-generated content and user editing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .beat import Beat


class SceneStatus(str, Enum):
    """Workflow status of a scene.

    Why this enum:
        Scenes have a more granular workflow than chapters because they
        are the primary editing unit. The status helps track progress
        through the writing and revision process.
    """

    DRAFT = "draft"
    GENERATING = "generating"  # LLM is actively producing content
    REVIEW = "review"  # Content ready for human review
    PUBLISHED = "published"


@dataclass
class Scene:
    """Scene Entity - A dramatic unit within a chapter.

    A Scene represents a continuous sequence of action happening in one
    location at one time. It is the primary container for beats and the
    main unit for LLM generation.

    Attributes:
        id: Unique identifier for the scene.
        chapter_id: Reference to the parent chapter.
        title: The title or name of the scene.
        summary: A brief synopsis or logline of the scene.
        order_index: Position of the scene within the chapter (0-based).
        status: Workflow status (DRAFT, GENERATING, REVIEW, PUBLISHED).
        location: Optional location/setting description.
        created_at: Timestamp when the scene was created.
        updated_at: Timestamp of the last modification.
        _beats: Internal list of beats (access via beats property).

    Why these attributes:
        These capture both the metadata needed for organization (title,
        order_index) and the workflow state (status) needed for the
        generation pipeline. Location is optional but useful for context.
    """

    title: str
    chapter_id: UUID
    id: UUID = field(default_factory=uuid4)
    summary: str = ""
    order_index: int = 0
    status: SceneStatus = SceneStatus.DRAFT
    location: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _beats: list[Beat] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate scene invariants after initialization.

        Why validation here:
            Ensures the scene is always in a valid state. Title validation
            prevents anonymous scenes, and order_index validation prevents
            negative indices.
        """
        if not self.title or not self.title.strip():
            raise ValueError("Scene title cannot be empty")
        if self.order_index < 0:
            raise ValueError("Scene order_index cannot be negative")

    @property
    def beats(self) -> list[Beat]:
        """Get a sorted copy of the beats in this scene.

        Returns:
            A new list of beats sorted by order_index.

        Why a copy:
            Prevents external modification of the internal beat list.
            Callers who need to modify beats should use the provided methods.
        """
        return sorted(self._beats, key=lambda b: b.order_index)

    def add_beat(self, beat: Beat) -> None:
        """Add a beat to this scene.

        Args:
            beat: The beat to add.

        Raises:
            ValueError: If the beat's scene_id doesn't match this scene.

        Why this validation:
            Ensures referential integrity between beats and scenes.
            A beat cannot exist in multiple scenes.
        """
        if beat.scene_id != self.id:
            raise ValueError(
                f"Beat scene_id ({beat.scene_id}) does not match scene id ({self.id})"
            )
        self._beats.append(beat)
        self._touch()

    def remove_beat(self, beat_id: UUID) -> bool:
        """Remove a beat from this scene.

        Args:
            beat_id: The ID of the beat to remove.

        Returns:
            True if the beat was found and removed, False otherwise.
        """
        initial_length = len(self._beats)
        self._beats = [b for b in self._beats if b.id != beat_id]
        if len(self._beats) < initial_length:
            self._touch()
            return True
        return False

    def get_beat(self, beat_id: UUID) -> Optional[Beat]:
        """Get a beat by its ID.

        Args:
            beat_id: The ID of the beat to find.

        Returns:
            The beat if found, None otherwise.
        """
        for beat in self._beats:
            if beat.id == beat_id:
                return beat
        return None

    def reorder_beats(self, beat_ids: list[UUID]) -> None:
        """Reorder beats according to the provided ID sequence.

        Args:
            beat_ids: List of beat IDs in the desired order.

        Raises:
            ValueError: If beat_ids doesn't match existing beats exactly.

        Why this method:
            Provides atomic reordering of all beats. The caller provides
            the complete new order, ensuring no beats are lost or duplicated.
            This is the primary method for drag-and-drop reordering in the UI.
        """
        existing_ids = {b.id for b in self._beats}
        provided_ids = set(beat_ids)

        if existing_ids != provided_ids:
            missing = existing_ids - provided_ids
            extra = provided_ids - existing_ids
            error_parts = []
            if missing:
                error_parts.append(f"missing: {missing}")
            if extra:
                error_parts.append(f"extra: {extra}")
            raise ValueError(f"Beat IDs mismatch: {', '.join(error_parts)}")

        # Create a mapping from beat_id to beat
        beat_map = {b.id: b for b in self._beats}

        # Update order_index based on position in beat_ids
        for new_index, beat_id in enumerate(beat_ids):
            beat_map[beat_id].order_index = new_index

        self._touch()

    def update_title(self, new_title: str) -> None:
        """Update the scene title.

        Args:
            new_title: The new title for the scene.

        Raises:
            ValueError: If the title is empty.
        """
        if not new_title or not new_title.strip():
            raise ValueError("Scene title cannot be empty")
        self.title = new_title.strip()
        self._touch()

    def update_summary(self, new_summary: str) -> None:
        """Update the scene summary."""
        self.summary = new_summary
        self._touch()

    def update_location(self, new_location: str) -> None:
        """Update the scene location."""
        self.location = new_location
        self._touch()

    def start_generation(self) -> None:
        """Mark the scene as being generated by LLM.

        Why this state:
            Provides UI feedback and prevents concurrent edits during
            LLM generation.
        """
        self.status = SceneStatus.GENERATING
        self._touch()

    def complete_generation(self) -> None:
        """Mark LLM generation as complete, move to review."""
        self.status = SceneStatus.REVIEW
        self._touch()

    def publish(self) -> None:
        """Publish the scene."""
        self.status = SceneStatus.PUBLISHED
        self._touch()

    def unpublish(self) -> None:
        """Return the scene to draft status."""
        self.status = SceneStatus.DRAFT
        self._touch()

    def move_to_position(self, new_index: int) -> None:
        """Update the scene's position within its chapter.

        Args:
            new_index: The new order index (0-based).

        Raises:
            ValueError: If the index is negative.
        """
        if new_index < 0:
            raise ValueError("Scene order_index cannot be negative")
        self.order_index = new_index
        self._touch()

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"Scene('{self.title}', order={self.order_index}, {self.status.value})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Scene(id={self.id}, chapter_id={self.chapter_id}, "
            f"title='{self.title}', order_index={self.order_index}, "
            f"status={self.status.value}, beats={len(self._beats)})"
        )
