#!/usr/bin/env python3
"""FactionIntent Domain Entity.

This module defines the FactionIntent entity which represents a faction's
intended action within the world simulation. Intents are generated based
on world state and faction characteristics, then resolved during simulation.

The entity follows the status lifecycle:
    PROPOSED -> SELECTED -> EXECUTED
    PROPOSED/SELECTED -> REJECTED

Typical usage example:
    >>> from src.contexts.world.domain.entities import FactionIntent, ActionType, IntentStatus
    >>> intent = FactionIntent(
    ...     faction_id="faction-uuid",
    ...     action_type=ActionType.EXPAND,
    ...     target_id="location-uuid",
    ...     priority=1,
    ...     rationale="Expand territory into the eastern plains"
    ... )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class ActionType(Enum):
    """Classification of faction action types.

    Categorizes the different strategic actions a faction can intend
    to take during simulation ticks.

    Attributes:
        EXPAND: Increase territory or influence.
        ATTACK: Military action against another faction.
        TRADE: Economic exchange proposal.
        SABOTAGE: Covert operation against rival.
        STABILIZE: Internal consolidation, defensive posture.

    Legacy aliases (mapped to new types):
        DEFEND: Maps to STABILIZE.
        ALLY: Maps to TRADE (diplomatic exchange).
        RECOVER: Maps to STABILIZE (internal recovery).
        CONSOLIDATE: Maps to STABILIZE.
    """

    EXPAND = "expand"
    ATTACK = "attack"
    TRADE = "trade"
    SABOTAGE = "sabotage"
    STABILIZE = "stabilize"
    # Legacy aliases - these map to equivalent new types
    DEFEND = "stabilize"  # Alias for STABILIZE
    ALLY = "trade"  # Alias for TRADE
    RECOVER = "stabilize"  # Alias for STABILIZE
    CONSOLIDATE = "stabilize"  # Alias for STABILIZE


class IntentStatus(Enum):
    """Lifecycle status of a faction intent.

    Tracks the progression of an intent from creation to resolution.

    Attributes:
        PROPOSED: Initial state, intent has been generated but not selected.
        SELECTED: Intent has been chosen for execution (by user or AI).
        EXECUTED: Intent has been acted upon and resolved.
        REJECTED: Intent was discarded without execution.
    """

    PROPOSED = "proposed"
    SELECTED = "selected"
    EXECUTED = "executed"
    REJECTED = "rejected"


# Define valid status transitions according to REQ-INTENT-003
VALID_STATUS_TRANSITIONS: Dict[IntentStatus, set[IntentStatus]] = {
    IntentStatus.PROPOSED: {IntentStatus.SELECTED, IntentStatus.REJECTED},
    IntentStatus.SELECTED: {IntentStatus.EXECUTED, IntentStatus.REJECTED},
    IntentStatus.EXECUTED: set(),  # Terminal state
    IntentStatus.REJECTED: set(),  # Terminal state
}

# Legacy aliases for backward compatibility
OFFENSIVE_INTENTS = {ActionType.ATTACK, ActionType.EXPAND}
DEFENSIVE_INTENTS = {ActionType.STABILIZE, ActionType.CONSOLIDATE}

# New action set names
OFFENSIVE_ACTIONS = {ActionType.ATTACK, ActionType.SABOTAGE}
DEFENSIVE_ACTIONS = {ActionType.STABILIZE}


def _normalize_action_type(action_type: Any) -> ActionType:
    """Normalize action type to one of the canonical types.

    Maps legacy types to their canonical equivalents.

    Args:
        action_type: ActionType enum or string

    Returns:
        Canonical ActionType enum value
    """
    if isinstance(action_type, str):
        action_type = ActionType(action_type.lower())

    if not isinstance(action_type, ActionType):
        return ActionType.STABILIZE

    # Map legacy types to canonical types
    legacy_mapping = {
        ActionType.DEFEND: ActionType.STABILIZE,
        ActionType.ALLY: ActionType.TRADE,
        ActionType.RECOVER: ActionType.STABILIZE,
        ActionType.CONSOLIDATE: ActionType.STABILIZE,
    }

    return legacy_mapping.get(action_type, action_type)


@dataclass
class FactionIntent:
    """FactionIntent Entity.

    Represents a faction's intended action within the simulation.
    Uses frozen=False to allow status transitions while maintaining
    immutability of other fields.

    Attributes:
        id: Unique identifier for this intent (UUID).
        faction_id: ID of the faction that has this intent.
        action_type: Classification of the action (EXPAND, ATTACK, etc.).
        target_id: ID of target (faction_id or location_id), optional.
        rationale: AI-generated explanation for the intent.
        priority: Importance level (1-3, 1 = highest priority).
        status: Current lifecycle status of the intent.
        created_at: Timestamp when the intent was created.

    Legacy Attributes (for backward compatibility):
        intent_id: Alias for id.
        intent_type: Alias for action_type.
        narrative: Alias for rationale.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    faction_id: str = ""
    action_type: ActionType = ActionType.STABILIZE
    target_id: Optional[str] = None
    rationale: str = ""
    priority: int = 2  # Default to medium priority
    status: IntentStatus = IntentStatus.PROPOSED
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate intent after initialization."""
        # Normalize action type to canonical form
        object.__setattr__(
            self, "action_type", _normalize_action_type(self.action_type)
        )
        self._validate()

    def _validate(self) -> None:
        """Validate the intent's invariants.

        Raises:
            ValueError: If any validation rule is violated.
        """
        errors: list[Any] = []
        if not self.id:
            errors.append("Intent ID cannot be empty")

        if not self.faction_id:
            errors.append("Faction ID cannot be empty")

        # Note: action_type and status are typed as enums and validated by dataclass

        if not 1 <= self.priority <= 3:
            errors.append(f"Priority must be between 1 and 3, got {self.priority}")

        if not self.rationale or not self.rationale.strip():
            errors.append("Rationale cannot be empty")

        if errors:
            raise ValueError(f"FactionIntent validation failed: {'; '.join(errors)}")

    # Legacy property aliases for backward compatibility
    @property
    def intent_id(self) -> str:
        """Legacy alias for id."""
        return self.id

    @property
    def intent_type(self) -> ActionType:
        """Legacy alias for action_type."""
        return self.action_type

    @property
    def narrative(self) -> str:
        """Legacy alias for rationale."""
        return self.rationale

    def transition_to(self, new_status: IntentStatus) -> None:
        """Transition the intent to a new status.

        Validates that the transition follows the allowed lifecycle:
        - PROPOSED -> SELECTED or REJECTED
        - SELECTED -> EXECUTED or REJECTED
        - EXECUTED and REJECTED are terminal states

        Args:
            new_status: The target status to transition to.

        Raises:
            ValueError: If the transition is not allowed.
        """
        if new_status == self.status:
            return  # No-op for same status

        allowed_transitions = VALID_STATUS_TRANSITIONS.get(self.status, set())
        if new_status not in allowed_transitions:
            logger.warning(
                "invalid_status_transition",
                intent_id=self.id,
                current_status=self.status.value,
                attempted_status=new_status.value,
                allowed=[s.value for s in allowed_transitions],
            )
            raise ValueError(
                f"Cannot transition from {self.status.value} to {new_status.value}. "
                f"Allowed transitions: {[s.value for s in allowed_transitions]}"
            )

        old_status = self.status
        self.status = new_status

        logger.info(
            "intent_status_transitioned",
            intent_id=self.id,
            faction_id=self.faction_id,
            old_status=old_status.value,
            new_status=new_status.value,
        )

    def select(self) -> None:
        """Mark this intent as selected for execution.

        Raises:
            ValueError: If intent is not in PROPOSED status.
        """
        self.transition_to(IntentStatus.SELECTED)

    def execute(self) -> None:
        """Mark this intent as executed.

        Raises:
            ValueError: If intent is not in SELECTED status.
        """
        self.transition_to(IntentStatus.EXECUTED)

    def reject(self) -> None:
        """Mark this intent as rejected.

        Raises:
            ValueError: If intent is not in PROPOSED or SELECTED status.
        """
        self.transition_to(IntentStatus.REJECTED)

    @property
    def is_offensive(self) -> bool:
        """Check if this intent is offensive in nature.

        Offensive actions include ATTACK and SABOTAGE.
        Also considers legacy OFFENSIVE_INTENTS (ATTACK, EXPAND).

        Returns:
            True if the intent is offensive, False otherwise.
        """
        return (
            self.action_type in OFFENSIVE_ACTIONS
            or self.action_type in OFFENSIVE_INTENTS
        )

    @property
    def is_defensive(self) -> bool:
        """Check if this intent is defensive in nature.

        Defensive actions include STABILIZE.

        Returns:
            True if the intent is defensive, False otherwise.
        """
        return self.action_type in DEFENSIVE_ACTIONS

    @property
    def is_terminal(self) -> bool:
        """Check if this intent is in a terminal state.

        Terminal states are EXECUTED and REJECTED.

        Returns:
            True if the intent is in a terminal state.
        """
        return self.status in {IntentStatus.EXECUTED, IntentStatus.REJECTED}

    @property
    def is_active(self) -> bool:
        """Check if this intent is active (non-terminal).

        Active states are PROPOSED and SELECTED.

        Returns:
            True if the intent is active.
        """
        return self.status in {IntentStatus.PROPOSED, IntentStatus.SELECTED}

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent to dictionary representation.

        Returns:
            Dictionary representation of the intent.
        """
        return {
            "id": self.id,
            "intent_id": self.id,  # Legacy alias
            "faction_id": self.faction_id,
            "action_type": self.action_type.value,
            "intent_type": self.action_type.value,  # Legacy alias
            "target_id": self.target_id,
            "rationale": self.rationale,
            "narrative": self.rationale,  # Legacy alias
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "is_offensive": self.is_offensive,
            "is_defensive": self.is_defensive,
            "is_terminal": self.is_terminal,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactionIntent":
        """Create a FactionIntent from a dictionary.

        Supports both new field names and legacy aliases:
        - id or intent_id
        - action_type or intent_type
        - rationale or narrative

        Args:
            data: Dictionary containing intent data.

        Returns:
            A new FactionIntent instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        # Handle created_at parsing
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        # Handle action_type parsing (support both new and legacy names)
        action_type = data.get("action_type") or data.get("intent_type")
        if isinstance(action_type, str):
            action_type = _normalize_action_type(action_type.lower())
        elif not isinstance(action_type, ActionType):
            action_type = ActionType.STABILIZE
        else:
            action_type = _normalize_action_type(action_type)

        # Handle status parsing
        status = data.get("status")
        if isinstance(status, str):
            status = IntentStatus(status.lower())
        elif not isinstance(status, IntentStatus):
            status = IntentStatus.PROPOSED

        # Handle id (support both new and legacy names)
        intent_id = data.get("id") or data.get("intent_id")

        # Handle rationale (support both new and legacy names)
        rationale = data.get("rationale") or data.get("narrative", "")

        return cls(
            id=intent_id or str(uuid4()),
            faction_id=data.get("faction_id", ""),
            action_type=action_type,
            target_id=data.get("target_id"),
            rationale=rationale,
            priority=data.get("priority", 2),
            status=status,
            created_at=created_at,
        )

    def __str__(self) -> str:
        """Return string representation of the intent.

        Returns:
            String representation showing intent type and faction.
        """
        return f"FactionIntent({self.faction_id[:8]}... -> {self.action_type.value}, priority={self.priority}, status={self.status.value})"

    def __repr__(self) -> str:
        """Return detailed string representation.

        Returns:
            Detailed string representation of the intent.
        """
        return (
            f"FactionIntent(id={self.id[:8]}..., "
            f"faction_id={self.faction_id[:8]}..., "
            f"type={self.action_type.value}, priority={self.priority}, status={self.status.value})"
        )


# Backward compatibility aliases for existing code
IntentType = ActionType  # Alias for backward compatibility
