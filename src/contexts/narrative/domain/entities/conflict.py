"""Conflict Entity - Dramatic tension drivers within scenes.

This module defines the Conflict entity, which represents a source of
dramatic tension in a scene. Conflicts are the engine of story - without
conflict, there is no narrative momentum.

Why Conflict as a separate entity:
    Conflicts track the stakes, type, and resolution status of dramatic
    tensions. This enables the Director Mode to ensure every scene has
    purpose and to track unresolved plot threads across the narrative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ConflictType(str, Enum):
    """Classification of conflict sources.

    Why these types:
        These represent the fundamental categories of dramatic conflict
        in narrative theory. Internal conflicts are within a character,
        external are against environment/fate, and interpersonal are
        between characters.
    """

    INTERNAL = "internal"  # Character vs self (moral dilemma, fear, desire)
    EXTERNAL = "external"  # Character vs environment/nature/fate
    INTERPERSONAL = "interpersonal"  # Character vs character


class ConflictStakes(str, Enum):
    """Stakes level indicating how much is at risk.

    Why stakes matter:
        Stakes determine the emotional weight of the scene. LOW stakes
        create breathing room, CRITICAL stakes create peak tension.
        A well-paced story varies stakes throughout.
    """

    LOW = "low"  # Minor inconvenience, embarrassment
    MEDIUM = "medium"  # Significant loss, relationship damage
    HIGH = "high"  # Major life impact, severe consequences
    CRITICAL = "critical"  # Life or death, irreversible change


class ResolutionStatus(str, Enum):
    """Tracking of conflict progression through the narrative.

    Why track resolution:
        Unresolved conflicts create tension and reader anticipation.
        Escalating conflicts drive rising action. Resolved conflicts
        provide catharsis. Tracking these states helps ensure satisfying
        narrative arcs.
    """

    UNRESOLVED = "unresolved"  # Conflict is active, no resolution yet
    ESCALATING = "escalating"  # Conflict is intensifying
    RESOLVED = "resolved"  # Conflict has been addressed


@dataclass
class Conflict:
    """Conflict Entity - A source of dramatic tension in a scene.

    A Conflict represents something that creates tension, opposition, or
    stakes within a scene. Every compelling scene should have at least
    one conflict driving the action.

    Attributes:
        id: Unique identifier for the conflict.
        scene_id: Reference to the scene containing this conflict.
        conflict_type: Classification (INTERNAL/EXTERNAL/INTERPERSONAL).
        stakes: Level of what's at risk (LOW/MEDIUM/HIGH/CRITICAL).
        description: Human-readable description of the conflict.
        resolution_status: Current state (UNRESOLVED/ESCALATING/RESOLVED).
        created_at: Timestamp when the conflict was created.
        updated_at: Timestamp of the last modification.

    Why these attributes:
        These capture the essential elements needed to track and analyze
        dramatic conflicts. The type helps categorize conflicts for analysis,
        stakes inform pacing decisions, and resolution_status enables
        tracking of plot threads.
    """

    scene_id: UUID
    conflict_type: ConflictType
    description: str
    stakes: ConflictStakes = ConflictStakes.MEDIUM
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate conflict invariants after initialization.

        Why validation here:
            Ensures the conflict is always in a valid state. Description
            validation prevents empty conflicts which would have no narrative
            purpose.
        """
        if not self.description or not self.description.strip():
            raise ValueError("Conflict description cannot be empty")

    def update_description(self, new_description: str) -> None:
        """Update the conflict description.

        Args:
            new_description: The new description for the conflict.

        Raises:
            ValueError: If the description is empty.
        """
        if not new_description or not new_description.strip():
            raise ValueError("Conflict description cannot be empty")
        self.description = new_description.strip()
        self._touch()

    def update_conflict_type(self, new_type: ConflictType) -> None:
        """Update the conflict classification.

        Args:
            new_type: The new conflict type.
        """
        self.conflict_type = new_type
        self._touch()

    def update_stakes(self, new_stakes: ConflictStakes) -> None:
        """Update the stakes level.

        Args:
            new_stakes: The new stakes level.

        Why update stakes:
            Stakes may change as the story progresses. A conflict that
            starts as LOW stakes might escalate to CRITICAL.
        """
        self.stakes = new_stakes
        self._touch()

    def escalate(self) -> None:
        """Mark the conflict as escalating.

        Why escalate:
            Escalation indicates the conflict is intensifying, which
            is a key story beat in rising action sequences.
        """
        self.resolution_status = ResolutionStatus.ESCALATING
        self._touch()

    def resolve(self) -> None:
        """Mark the conflict as resolved.

        Why resolve:
            Resolution provides closure and catharsis. Tracking
            resolved conflicts helps ensure all plot threads are
            addressed.
        """
        self.resolution_status = ResolutionStatus.RESOLVED
        self._touch()

    def reopen(self) -> None:
        """Reopen a resolved conflict.

        Why reopen:
            Sometimes a conflict that seemed resolved returns. This
            is a common dramatic technique for plot twists.
        """
        self.resolution_status = ResolutionStatus.UNRESOLVED
        self._touch()

    @property
    def is_critical(self) -> bool:
        """Check if this conflict has critical stakes.

        Returns:
            True if stakes are CRITICAL.

        Why this property:
            Critical conflicts need special UI treatment (fire/red indicators)
            and affect pacing analysis.
        """
        return self.stakes == ConflictStakes.CRITICAL

    @property
    def is_resolved(self) -> bool:
        """Check if this conflict is resolved.

        Returns:
            True if resolution_status is RESOLVED.
        """
        return self.resolution_status == ResolutionStatus.RESOLVED

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Conflict('{self.description[:30]}...', "
            f"{self.conflict_type.value}, {self.stakes.value}, "
            f"{self.resolution_status.value})"
        )

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Conflict(id={self.id}, scene_id={self.scene_id}, "
            f"type={self.conflict_type.value}, stakes={self.stakes.value}, "
            f"status={self.resolution_status.value})"
        )
