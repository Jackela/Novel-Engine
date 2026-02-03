"""Plotline Entity - Narrative threads weaving through the story.

This module defines the Plotline entity, which represents a storyline
or thematic thread that runs through multiple scenes. Plotlines enable
writers to track and manage complex narrative structures.

Why Plotline as a separate entity:
    Plotlines provide a way to organize and visualize the narrative threads
    that weave through a story. They help ensure all storylines are properly
    developed and resolved, and enable filtering the narrative to focus on
    specific threads during editing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class PlotlineStatus(str, Enum):
    """Tracking of plotline progression through the narrative.

    Why track plotline status:
        Active plotlines are currently being developed. Resolved plotlines
        have reached their conclusion. Abandoned plotlines were intentionally
        dropped (useful for tracking cut content).
    """

    ACTIVE = "active"  # Plotline is currently being developed
    RESOLVED = "resolved"  # Plotline has reached its conclusion
    ABANDONED = "abandoned"  # Plotline was intentionally dropped


@dataclass
class Plotline:
    """Plotline Entity - A narrative thread running through multiple scenes.

    A Plotline represents a storyline or thematic thread that weaves through
    the narrative. Multiple plotlines can run in parallel, and scenes can
    belong to multiple plotlines simultaneously.

    Attributes:
        id: Unique identifier for the plotline.
        name: The name or title of the plotline.
        color: Hex color code for visual identification (e.g., "#ff5733").
        description: Human-readable description of the plotline.
        status: Current state (ACTIVE/RESOLVED/ABANDONED).
        created_at: Timestamp when the plotline was created.
        updated_at: Timestamp of the last modification.

    Why these attributes:
        Name and description provide identification. Color enables visual
        distinction in the UI (Weaver graph, scene tags). Status tracks
        whether the plotline is ongoing, concluded, or dropped.
    """

    name: str
    color: str
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    status: PlotlineStatus = PlotlineStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate plotline invariants after initialization.

        Why validation here:
            Ensures the plotline is always in a valid state. Name validation
            prevents anonymous plotlines. Color validation ensures it's a valid
            hex color code for UI rendering.
        """
        if not self.name or not self.name.strip():
            raise ValueError("Plotline name cannot be empty")

        # Validate hex color format (supports #RGB, #RRGGBB, #RRGGBBAA)
        color = self.color.strip()
        if not color.startswith("#"):
            raise ValueError(f"Plotline color must be a hex color code starting with '#', got: {color}")

        # Remove # and validate length
        hex_part = color[1:]
        if len(hex_part) not in (3, 6, 8):
            raise ValueError(f"Plotline color must be 3, 6, or 8 hex characters, got: {color}")

        # Validate all characters are hex digits
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError(f"Plotline color contains invalid hex characters: {color}")

    def update_name(self, new_name: str) -> None:
        """Update the plotline name.

        Args:
            new_name: The new name for the plotline.

        Raises:
            ValueError: If the name is empty.
        """
        if not new_name or not new_name.strip():
            raise ValueError("Plotline name cannot be empty")
        self.name = new_name.strip()
        self._touch()

    def update_description(self, new_description: str) -> None:
        """Update the plotline description.

        Args:
            new_description: The new description for the plotline.
        """
        self.description = new_description
        self._touch()

    def update_color(self, new_color: str) -> None:
        """Update the plotline color.

        Args:
            new_color: The new hex color code.

        Raises:
            ValueError: If the color is not a valid hex color code.

        Why update color:
            Colors may need adjustment for contrast or aesthetic reasons.
            The UI relies on valid hex codes for rendering.
        """
        # Validate hex color format
        color = new_color.strip()
        if not color.startswith("#"):
            raise ValueError(f"Plotline color must be a hex color code starting with '#', got: {color}")

        hex_part = color[1:]
        if len(hex_part) not in (3, 6, 8):
            raise ValueError(f"Plotline color must be 3, 6, or 8 hex characters, got: {color}")

        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError(f"Plotline color contains invalid hex characters: {color}")

        self.color = color
        self._touch()

    def resolve(self) -> None:
        """Mark the plotline as resolved.

        Why resolve:
            Resolution indicates the plotline has reached its conclusion.
            This helps track which story threads are complete.
        """
        self.status = PlotlineStatus.RESOLVED
        self._touch()

    def abandon(self) -> None:
        """Mark the plotline as abandoned.

        Why abandon:
            Abandoning tracks intentionally dropped plotlines (cut content).
            This is different from unresolved - it's a deliberate choice.
        """
        self.status = PlotlineStatus.ABANDONED
        self._touch()

    def reactivate(self) -> None:
        """Mark an abandoned or resolved plotline as active again.

        Why reactivate:
            Plotlines can be revived. A resolved plotline might need
            continuation, or an abandoned one might be reintroduced.
        """
        self.status = PlotlineStatus.ACTIVE
        self._touch()

    @property
    def is_active(self) -> bool:
        """Check if this plotline is active.

        Returns:
            True if status is ACTIVE.

        Why this property:
            Active plotlines need different UI treatment and filtering
            behavior than resolved or abandoned ones.
        """
        return self.status == PlotlineStatus.ACTIVE

    @property
    def is_resolved(self) -> bool:
        """Check if this plotline is resolved.

        Returns:
            True if status is RESOLVED.
        """
        return self.status == PlotlineStatus.RESOLVED

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Plotline('{self.name}', color={self.color}, "
            f"{self.status.value})"
        )

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Plotline(id={self.id}, name='{self.name}', "
            f"color={self.color}, status={self.status.value})"
        )
