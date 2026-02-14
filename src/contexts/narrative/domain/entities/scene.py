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


class StoryPhase(str, Enum):
    """Story structure phase of a scene within a chapter.

    Why this enum:
        Enables Chapter Board View (Kanban-style) organization by story beats.
        Scenes can be categorized by their narrative function: Setup,
        Inciting Incident, Rising Action, Climax, or Resolution. This helps
        authors visualize story structure and balance pacing across phases.
    """

    SETUP = "setup"
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


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
        story_phase: Story structure phase (SETUP, INCITING_INCIDENT, RISING_ACTION, CLIMAX, RESOLUTION).
        location: Optional location/setting description.
        tension_level: Dramatic tension level 1-10 (default 5).
        energy_level: Narrative energy level 1-10 (default 5).
        plotline_ids: List of plotline IDs this scene belongs to.
        metadata: Flexible dict for additional data like smart tags.
        created_at: Timestamp when the scene was created.
        updated_at: Timestamp of the last modification.
        _beats: Internal list of beats (access via beats property).

    Why these attributes:
        These capture both the metadata needed for organization (title,
        order_index) and the workflow state (status) needed for the
        generation pipeline. Location is optional but useful for context.
        Tension and energy levels enable pacing analysis across scenes.
        Plotline IDs enable tracking which narrative threads this scene
        advances. Metadata stores flexible data like smart tags from
        the AI tagging system.
    """

    title: str
    chapter_id: UUID
    id: UUID = field(default_factory=uuid4)
    summary: str = ""
    order_index: int = 0
    status: SceneStatus = SceneStatus.DRAFT
    story_phase: StoryPhase = StoryPhase.SETUP
    location: str = ""
    tension_level: int = 5
    energy_level: int = 5
    plotline_ids: list[UUID] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _beats: list[Beat] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate scene invariants after initialization.

        Why validation here:
            Ensures the scene is always in a valid state. Title validation
            prevents anonymous scenes, order_index validation prevents
            negative indices, and pacing levels must be within bounds.
        """
        if not self.title or not self.title.strip():
            raise ValueError("Scene title cannot be empty")
        if self.order_index < 0:
            raise ValueError("Scene order_index cannot be negative")
        if not 1 <= self.tension_level <= 10:
            raise ValueError("Scene tension_level must be between 1 and 10")
        if not 1 <= self.energy_level <= 10:
            raise ValueError("Scene energy_level must be between 1 and 10")

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

    def update_tension_level(self, level: int) -> None:
        """Update the scene's tension level.

        Args:
            level: Tension level from 1-10.

        Raises:
            ValueError: If level is not between 1 and 10.

        Why tension level:
            Tension measures dramatic conflict and stakes. High tension
            scenes involve danger, conflict, or uncertainty. Low tension
            provides breathing room between intense moments.
        """
        if not 1 <= level <= 10:
            raise ValueError("Scene tension_level must be between 1 and 10")
        self.tension_level = level
        self._touch()

    def update_energy_level(self, level: int) -> None:
        """Update the scene's energy level.

        Args:
            level: Energy level from 1-10.

        Raises:
            ValueError: If level is not between 1 and 10.

        Why energy level:
            Energy measures narrative momentum and action intensity.
            High energy scenes have rapid action, dialogue, or events.
            Low energy scenes are reflective, descriptive, or quiet.
        """
        if not 1 <= level <= 10:
            raise ValueError("Scene energy_level must be between 1 and 10")
        self.energy_level = level
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

    def add_plotline(self, plotline_id: UUID) -> None:
        """Add a plotline to this scene.

        Args:
            plotline_id: The ID of the plotline to add.

        Why this method:
            Enables tracking which narrative threads this scene advances.
            A scene can belong to multiple plotlines simultaneously.
        """
        if plotline_id not in self.plotline_ids:
            self.plotline_ids.append(plotline_id)
            self._touch()

    def remove_plotline(self, plotline_id: UUID) -> bool:
        """Remove a plotline from this scene.

        Args:
            plotline_id: The ID of the plotline to remove.

        Returns:
            True if the plotline was found and removed, False otherwise.
        """
        if plotline_id in self.plotline_ids:
            self.plotline_ids.remove(plotline_id)
            self._touch()
            return True
        return False

    def set_plotlines(self, plotline_ids: list[UUID]) -> None:
        """Replace all plotlines with a new list.

        Args:
            plotline_ids: The new list of plotline IDs.

        Why this method:
            Provides atomic replacement of all plotline associations.
            Useful for bulk updates from the UI.
        """
        self.plotline_ids = list(plotline_ids)
        self._touch()

    def update_story_phase(self, phase: StoryPhase) -> None:
        """Update the scene's story structure phase.

        Args:
            phase: The new story phase.

        Why this method:
            Enables Chapter Board View (Kanban) organization by narrative function.
            Scenes can be moved between phases to visualize story structure.
        """
        self.story_phase = phase
        self._touch()

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def update_metadata(self, key: str, value: Any) -> None:
        """Update a metadata key-value pair.

        Args:
            key: The metadata key to update.
            value: The value to set.

        Why this method:
            Provides controlled access to metadata for storing flexible
            data like smart tags from the AI tagging system.
        """
        self.metadata[key] = value
        self._touch()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value by key.

        Args:
            key: The metadata key to retrieve.
            default: Default value if key not found.

        Returns:
            The metadata value or default if not found.
        """
        return self.metadata.get(key, default)

    def set_smart_tags(self, tags: dict[str, list[str]]) -> None:
        """Store smart tags in metadata.

        Args:
            tags: Dictionary mapping category names to tag lists.

        Why this method:
            Provides a consistent interface for storing smart tags
            generated by the AI tagging system.
        """
        self.metadata["smart_tags"] = tags
        self._touch()

    def get_smart_tags(self) -> dict[str, list[str]]:
        """Get smart tags from metadata.

        Returns:
            Dictionary mapping category names to tag lists, or empty dict if none.
        """
        return self.metadata.get("smart_tags", {})

    # ==================== Manual Smart Tags Override ====================

    def set_manual_smart_tags(self, category: str, tags: list[str]) -> None:
        """Set manual tags for a specific category.

        These tags are marked as manual-only and will never be overridden
        by auto-tagging. They are stored under a separate key in metadata.

        Args:
            category: The tag category (e.g., "genre", "mood", "themes")
            tags: List of manual tags for this category
        """
        if "manual_smart_tags" not in self.metadata:
            self.metadata["manual_smart_tags"] = {}

        self.metadata["manual_smart_tags"][category] = [
            t.strip().lower() for t in tags if t.strip()
        ]
        self._touch()

    def get_manual_smart_tags(self) -> dict[str, list[str]]:
        """Get manual-only smart tags.

        Returns:
            Dictionary mapping category names to manual tag lists.
        """
        return self.metadata.get("manual_smart_tags", {})

    def get_manual_smart_tags_for_category(self, category: str) -> list[str]:
        """Get manual tags for a specific category.

        Args:
            category: The tag category

        Returns:
            List of manual tags for this category
        """
        manual_tags = self.get_manual_smart_tags()
        return manual_tags.get(category, [])

    def remove_manual_smart_tag(self, category: str, tag: str) -> bool:
        """Remove a manual smart tag.

        Args:
            category: The tag category
            tag: The tag to remove

        Returns:
            True if tag was found and removed
        """
        manual_tags = self.get_manual_smart_tags()
        if category in manual_tags:
            tag_normalized = tag.strip().lower()
            if tag_normalized in [t.lower() for t in manual_tags[category]]:
                manual_tags[category] = [
                    t for t in manual_tags[category] if t.lower() != tag_normalized
                ]
                self.metadata["manual_smart_tags"] = manual_tags
                self._touch()
                return True
        return False

    def clear_manual_smart_tags(self, category: str | None = None) -> None:
        """Clear manual smart tags.

        Args:
            category: If provided, only clear this category.
                     If None, clear all manual tags.
        """
        if "manual_smart_tags" not in self.metadata:
            return

        if category:
            self.metadata["manual_smart_tags"].pop(category, None)
        else:
            self.metadata["manual_smart_tags"] = {}

        self._touch()

    def get_effective_smart_tags(self) -> dict[str, list[str]]:
        """Get all smart tags (auto + manual) combined.

        Returns:
            Dictionary with all tags by category, merging auto-generated
            and manual tags.
        """
        auto_tags = self.get_smart_tags()
        manual_tags = self.get_manual_smart_tags()

        effective: dict[str, list[str]] = {}

        # All categories
        all_categories = set(auto_tags.keys()) | set(manual_tags.keys())

        for category in all_categories:
            auto = set(auto_tags.get(category, []))
            manual = set(manual_tags.get(category, []))
            effective[category] = list(auto | manual)

        return effective

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"Scene('{self.title}', order={self.order_index}, {self.status.value})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Scene(id={self.id}, chapter_id={self.chapter_id}, "
            f"title='{self.title}', order_index={self.order_index}, "
            f"status={self.status.value}, tension={self.tension_level}, "
            f"energy={self.energy_level}, beats={len(self._beats)})"
        )
