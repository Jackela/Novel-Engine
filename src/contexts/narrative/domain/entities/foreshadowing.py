"""Foreshadowing Entity - Chekhov's Gun enforcement for narrative setups and payoffs.

This module defines the Foreshadowing entity, which represents a narrative setup
that will be paid off later in the story. This enforces Chekhov's Gun principle:
if you introduce a gun in act 1, it must go off by act 3.

Why Foreshadowing as a separate entity:
    Foreshadowing is a critical narrative technique that creates anticipation and
    satisfaction when properly executed. Tracking setups and payoffs ensures that
    no narrative gun is left unfired, preventing plot holes and reader frustration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Callable, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .scene import Scene


class ForeshadowingStatus(str, Enum):
    """Tracking of foreshadowing progression through the narrative.

    Why track foreshadowing status:
        PLANTED indicates the setup has been introduced but not yet addressed.
        PAID_OFF indicates the setup has been resolved, creating satisfaction.
        ABANDONED tracks intentionally dropped setups (useful for cut content).
    """

    PLANTED = "planted"  # Setup introduced, awaiting payoff
    PAID_OFF = "paid_off"  # Setup has been addressed and resolved
    ABANDONED = "abandoned"  # Setup was intentionally dropped


@dataclass
class Foreshadowing:
    """Foreshadowing Entity - A narrative setup with a future payoff.

    A Foreshadowing represents a deliberate setup introduced in one scene that
    will be addressed later in the story. This enforces Chekhov's Gun principle
    and helps writers track all narrative threads to resolution.

    Attributes:
        id: Unique identifier for the foreshadowing.
        setup_scene_id: Reference to the scene where the setup occurs.
        payoff_scene_id: Reference to the scene where payoff occurs (None until paid off).
        description: Human-readable description of the setup.
        status: Current state (PLANTED/PAID_OFF/ABANDONED).
        created_at: Timestamp when the foreshadowing was created.
        updated_at: Timestamp of the last modification.

    Why these attributes:
        The scene pair (setup/payoff) enables drawing visual connections in
        Weaver. Description explains what's being foreshadowed. Status tracks
        whether the thread is still open or has been resolved.
    """

    setup_scene_id: UUID
    description: str
    payoff_scene_id: Optional[UUID] = None
    status: ForeshadowingStatus = ForeshadowingStatus.PLANTED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate foreshadowing invariants after initialization.

        Why validation here:
            Ensures the foreshadowing is always in a valid state. Description
            validation prevents empty setups. Status consistency ensures payoff
            scene is set when status is PAID_OFF.
        """
        if not self.description or not self.description.strip():
            raise ValueError("Foreshadowing description cannot be empty")

        # If status is PAID_OFF, payoff_scene_id must be set
        if self.status == ForeshadowingStatus.PAID_OFF and self.payoff_scene_id is None:
            raise ValueError(
                "Foreshadowing with PAID_OFF status must have a payoff_scene_id"
            )

        # If payoff_scene_id is set, status must be PAID_OFF
        if (
            self.payoff_scene_id is not None
            and self.status != ForeshadowingStatus.PAID_OFF
        ):
            raise ValueError(
                "Foreshadowing with payoff_scene_id must have PAID_OFF status"
            )

    def validate_scene_order(
        self,
        get_scene_by_id: Callable[[UUID], Optional[Scene]],
    ) -> None:
        """Validate that payoff scene comes after setup scene in story order.

        Args:
            get_scene_by_id: A function that retrieves a Scene by UUID.

        Raises:
            ValueError: If payoff_scene is not after setup_scene, or if scenes
                cannot be found, or if scenes are in different chapters.

        Why this validation:
            Foreshadowing requires temporal order - the payoff must happen
            after the setup in the narrative flow. Payoffs cannot precede
            their setups in story logic.
        """
        # If no payoff scene set, no order validation needed
        if self.payoff_scene_id is None:
            return

        setup_scene = get_scene_by_id(self.setup_scene_id)
        payoff_scene = get_scene_by_id(self.payoff_scene_id)

        if setup_scene is None:
            raise ValueError(f"Setup scene not found: {self.setup_scene_id}")
        if payoff_scene is None:
            raise ValueError(f"Payoff scene not found: {self.payoff_scene_id}")

        # Scenes must be in the same chapter for ordering validation
        # Cross-chapter foreshadowing is allowed but we can't validate order
        if setup_scene.chapter_id != payoff_scene.chapter_id:
            return

        # Validate payoff comes after setup
        if payoff_scene.order_index <= setup_scene.order_index:
            raise ValueError(
                f"Payoff scene (order {payoff_scene.order_index}) must come after "
                f"setup scene (order {setup_scene.order_index})"
            )

    def update_description(self, new_description: str) -> None:
        """Update the foreshadowing description.

        Args:
            new_description: The new description for the foreshadowing.

        Raises:
            ValueError: If the description is empty.
        """
        if not new_description or not new_description.strip():
            raise ValueError("Foreshadowing description cannot be empty")
        self.description = new_description.strip()
        self._touch()

    def link_payoff(
        self, payoff_scene_id: UUID, get_scene_by_id: Callable[[UUID], Optional[Scene]]
    ) -> None:
        """Link a payoff scene to this foreshadowing.

        Args:
            payoff_scene_id: The UUID of the payoff scene.
            get_scene_by_id: A function that retrieves a Scene by UUID for validation.

        Raises:
            ValueError: If the payoff scene is the same as setup scene, or if
                the payoff scene doesn't come after the setup scene.

        Why link_payoff method:
            This is the primary way to mark a foreshadowing as paid off. It
            performs validation to ensure narrative integrity.
        """
        if payoff_scene_id == self.setup_scene_id:
            raise ValueError("Payoff scene cannot be the same as setup scene")

        self.payoff_scene_id = payoff_scene_id
        self.status = ForeshadowingStatus.PAID_OFF

        # Validate scene order using the provided getter
        self.validate_scene_order(get_scene_by_id)

        self._touch()

    def abandon(self) -> None:
        """Mark the foreshadowing as abandoned.

        Why abandon:
            Abandoning tracks intentionally dropped setups (cut content).
            This is different from leaving it planted - it's a deliberate
            choice to not pay off this setup.
        """
        self.status = ForeshadowingStatus.ABANDONED
        self.payoff_scene_id = None
        self._touch()

    def replant(self) -> None:
        """Mark an abandoned or paid-off foreshadowing as planted again.

        Why replant:
            Foreshadowing can be revived. A paid-off setup might need
            to be unresolved again, or an abandoned one might be reintroduced.
        """
        self.status = ForeshadowingStatus.PLANTED
        self.payoff_scene_id = None
        self._touch()

    @property
    def is_planted(self) -> bool:
        """Check if this foreshadowing is still planted (unresolved).

        Returns:
            True if status is PLANTED.
        """
        return self.status == ForeshadowingStatus.PLANTED

    @property
    def is_paid_off(self) -> bool:
        """Check if this foreshadowing has been paid off.

        Returns:
            True if status is PAID_OFF.
        """
        return self.status == ForeshadowingStatus.PAID_OFF

    @property
    def is_abandoned(self) -> bool:
        """Check if this foreshadowing has been abandoned.

        Returns:
            True if status is ABANDONED.
        """
        return self.status == ForeshadowingStatus.ABANDONED

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """Human-readable representation."""
        payoff_str = (
            f" -> {self.payoff_scene_id}" if self.payoff_scene_id else " (unpaid)"
        )
        return f"Foreshadowing('{self.description[:30]}...'{payoff_str}, {self.status.value})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"Foreshadowing(id={self.id}, "
            f"setup_scene_id={self.setup_scene_id}, "
            f"payoff_scene_id={self.payoff_scene_id}, "
            f"status={self.status.value})"
        )
