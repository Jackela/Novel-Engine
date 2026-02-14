#!/usr/bin/env python3
"""
Character Goal Value Object

This module implements the CharacterGoal value object, which represents
a goal that a character is pursuing. Goals drive character motivation
and narrative arcs, providing clear direction for storytelling.

Why goals matter:
    Goals give characters purpose and direction. A character with active
    goals generates more compelling narratives, as their actions can be
    evaluated against their desires. Completed or failed goals mark
    character growth and story progression.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class GoalStatus(str, Enum):
    """Status of a character goal.

    Why use an enum: Goals have a limited set of valid states.
    Using an enum ensures type safety and prevents invalid states.
    """

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GoalUrgency(str, Enum):
    """Urgency level of a character goal.

    Urgency affects how a character prioritizes and reacts to their goals.
    - LOW: Background ambition, no time pressure
    - MEDIUM: Important but not immediate
    - HIGH: Pressing concern that demands attention
    - CRITICAL: Must be addressed immediately
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class CharacterGoal:
    """
    Value object representing a character's goal or aspiration.

    Goals capture what a character wants to achieve. Unlike memories
    (which record the past), goals point toward the future and drive
    character behavior and narrative tension.

    Attributes:
        goal_id: Unique identifier for this goal
        description: What the character wants to achieve
        status: Current state (ACTIVE, COMPLETED, FAILED)
        urgency: How pressing this goal is
        created_at: When the goal was established
        completed_at: When the goal was completed/failed (if applicable)

    This is immutable following DDD value object principles.
    """

    description: str
    status: GoalStatus = GoalStatus.ACTIVE
    urgency: GoalUrgency = GoalUrgency.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    goal_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate goal data upon creation."""
        # Validate description
        if not isinstance(self.description, str):
            raise TypeError(
                f"description must be a string, got {type(self.description).__name__}"
            )
        if not self.description.strip():
            raise ValueError("description cannot be empty")

        # Validate status
        if not isinstance(self.status, GoalStatus):
            if isinstance(self.status, str):
                try:
                    object.__setattr__(self, "status", GoalStatus(self.status))
                except ValueError:
                    raise ValueError(
                        f"Invalid status: {self.status}. "
                        f"Must be one of: {[s.value for s in GoalStatus]}"
                    )
            else:
                raise TypeError(
                    f"status must be a GoalStatus, got {type(self.status).__name__}"
                )

        # Validate urgency
        if not isinstance(self.urgency, GoalUrgency):
            if isinstance(self.urgency, str):
                try:
                    object.__setattr__(self, "urgency", GoalUrgency(self.urgency))
                except ValueError:
                    raise ValueError(
                        f"Invalid urgency: {self.urgency}. "
                        f"Must be one of: {[u.value for u in GoalUrgency]}"
                    )
            else:
                raise TypeError(
                    f"urgency must be a GoalUrgency, got {type(self.urgency).__name__}"
                )

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise TypeError(
                f"created_at must be a datetime, got {type(self.created_at).__name__}"
            )

        if self.completed_at is not None and not isinstance(
            self.completed_at, datetime
        ):
            raise TypeError(
                f"completed_at must be a datetime or None, "
                f"got {type(self.completed_at).__name__}"
            )

        # Business rule: completed_at should only be set for non-active goals
        if self.status == GoalStatus.ACTIVE and self.completed_at is not None:
            raise ValueError("Active goals should not have a completed_at timestamp")

        # Validate goal_id
        if not isinstance(self.goal_id, str):
            raise TypeError(
                f"goal_id must be a string, got {type(self.goal_id).__name__}"
            )
        if not self.goal_id.strip():
            raise ValueError("goal_id cannot be empty")

    def is_active(self) -> bool:
        """Check if this goal is still being pursued.

        Returns:
            True if status is ACTIVE
        """
        return self.status == GoalStatus.ACTIVE

    def is_completed(self) -> bool:
        """Check if this goal was successfully achieved.

        Returns:
            True if status is COMPLETED
        """
        return self.status == GoalStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if this goal was abandoned or became impossible.

        Returns:
            True if status is FAILED
        """
        return self.status == GoalStatus.FAILED

    def is_resolved(self) -> bool:
        """Check if this goal has been resolved (completed or failed).

        Returns:
            True if status is COMPLETED or FAILED
        """
        return self.status in (GoalStatus.COMPLETED, GoalStatus.FAILED)

    def is_urgent(self) -> bool:
        """Check if this goal requires immediate attention.

        Returns:
            True if urgency is HIGH or CRITICAL
        """
        return self.urgency in (GoalUrgency.HIGH, GoalUrgency.CRITICAL)

    def get_urgency_level(self) -> str:
        """Get the urgency level as a lowercase string.

        Returns:
            'low', 'medium', 'high', or 'critical'
        """
        return self.urgency.value.lower()

    def complete(self) -> "CharacterGoal":
        """Create a new goal instance marked as completed.

        Why return a new instance: CharacterGoal is immutable, so state
        changes create new instances. This preserves the history of the
        goal's state transitions.

        Returns:
            A new CharacterGoal with status=COMPLETED and completed_at set
        """
        if self.status != GoalStatus.ACTIVE:
            raise ValueError(f"Cannot complete a goal with status {self.status.value}")

        return CharacterGoal(
            goal_id=self.goal_id,
            description=self.description,
            status=GoalStatus.COMPLETED,
            urgency=self.urgency,
            created_at=self.created_at,
            completed_at=datetime.now(),
        )

    def fail(self) -> "CharacterGoal":
        """Create a new goal instance marked as failed.

        Returns:
            A new CharacterGoal with status=FAILED and completed_at set
        """
        if self.status != GoalStatus.ACTIVE:
            raise ValueError(f"Cannot fail a goal with status {self.status.value}")

        return CharacterGoal(
            goal_id=self.goal_id,
            description=self.description,
            status=GoalStatus.FAILED,
            urgency=self.urgency,
            created_at=self.created_at,
            completed_at=datetime.now(),
        )

    def update_urgency(self, new_urgency: GoalUrgency) -> "CharacterGoal":
        """Create a new goal instance with updated urgency.

        Args:
            new_urgency: The new urgency level

        Returns:
            A new CharacterGoal with the updated urgency
        """
        if self.status != GoalStatus.ACTIVE:
            raise ValueError(
                f"Cannot update urgency of a goal with status {self.status.value}"
            )

        return CharacterGoal(
            goal_id=self.goal_id,
            description=self.description,
            status=self.status,
            urgency=new_urgency,
            created_at=self.created_at,
            completed_at=self.completed_at,
        )

    def to_dict(self) -> dict:
        """Convert goal to dictionary format.

        Returns:
            Dict with all goal fields
        """
        result = {
            "goal_id": self.goal_id,
            "description": self.description,
            "status": self.status.value,
            "urgency": self.urgency.value,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active(),
            "is_urgent": self.is_urgent(),
        }

        if self.completed_at is not None:
            result["completed_at"] = self.completed_at.isoformat()

        return result

    def get_summary(self) -> str:
        """Get a brief summary of the goal for display.

        Returns:
            A one-line summary with status and urgency indicators
        """
        status_emoji = {
            GoalStatus.ACTIVE: "⏳",
            GoalStatus.COMPLETED: "✓",
            GoalStatus.FAILED: "✗",
        }
        urgency_indicator = "!" * (
            [
                GoalUrgency.LOW,
                GoalUrgency.MEDIUM,
                GoalUrgency.HIGH,
                GoalUrgency.CRITICAL,
            ].index(self.urgency)
            + 1
        )

        desc_preview = (
            self.description[:50] + "..."
            if len(self.description) > 50
            else self.description
        )

        return f"{status_emoji[self.status]} [{urgency_indicator}] {desc_preview}"

    @classmethod
    def create(
        cls,
        description: str,
        urgency: GoalUrgency = GoalUrgency.MEDIUM,
        status: GoalStatus = GoalStatus.ACTIVE,
    ) -> "CharacterGoal":
        """Factory method to create a new goal.

        Args:
            description: What the character wants to achieve
            urgency: How pressing this goal is (default MEDIUM)
            status: Initial status (default ACTIVE)

        Returns:
            A new CharacterGoal instance
        """
        return cls(
            description=description,
            urgency=urgency,
            status=status,
        )
