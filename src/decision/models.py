"""
Decision Module Data Models

Defines data structures for decision points, user responses, and negotiation results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class DecisionPointType(Enum):
    """Types of decision points that can trigger user interaction."""

    TURNING_POINT = "turning_point"
    CRISIS = "crisis"
    CLIMAX = "climax"
    REVELATION = "revelation"
    TRANSFORMATION = "transformation"
    CHARACTER_CHOICE = "character_choice"
    RELATIONSHIP_CHANGE = "relationship_change"
    CONFLICT_ESCALATION = "conflict_escalation"


class FeasibilityResult(Enum):
    """Results of feasibility evaluation for user input."""

    ACCEPTED = "accepted"  # User input can be executed as-is
    MINOR_ADJUSTMENT = "minor_adjustment"  # Small tweaks needed
    ALTERNATIVE_REQUIRED = "alternative_required"  # Needs significant changes
    REJECTED = "rejected"  # Cannot be executed (violates story rules)


class PauseState(Enum):
    """States of the pause controller."""

    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    NEGOTIATING = "negotiating"
    RESUMING = "resuming"


@dataclass
class DecisionOption:
    """A single option presented to the user at a decision point."""

    option_id: int
    label: str
    description: str
    icon: str = ""  # Emoji or icon identifier
    impact_preview: str = ""  # Brief description of potential impact

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "option_id": self.option_id,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "impact_preview": self.impact_preview,
        }


@dataclass
class DecisionPoint:
    """
    Represents a key narrative moment where user intervention is requested.

    A decision point is detected when story conditions meet certain criteria
    (high dramatic tension, relationship changes, etc.) and the system
    pauses to allow user input.
    """

    decision_id: str = field(default_factory=lambda: f"dp-{uuid4().hex[:8]}")
    decision_type: DecisionPointType = DecisionPointType.TURNING_POINT
    turn_number: int = 0

    # Context
    title: str = ""
    description: str = ""
    narrative_context: str = ""  # Recent story summary

    # Options
    options: List[DecisionOption] = field(default_factory=list)
    default_option_id: Optional[int] = None

    # Metrics that triggered this decision point
    dramatic_tension: Decimal = Decimal("5.0")
    emotional_intensity: Decimal = Decimal("5.0")

    # Timing
    timeout_seconds: int = 120  # Default 2 minutes
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Status
    is_resolved: bool = False
    resolution: Optional[str] = None  # "user_input", "timeout", "skipped"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "turn_number": self.turn_number,
            "title": self.title,
            "description": self.description,
            "narrative_context": self.narrative_context,
            "options": [opt.to_dict() for opt in self.options],
            "default_option_id": self.default_option_id,
            "dramatic_tension": float(self.dramatic_tension),
            "emotional_intensity": float(self.emotional_intensity),
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "is_resolved": self.is_resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionPoint":
        """Create from dictionary."""
        options = [DecisionOption(**opt) for opt in data.get("options", [])]
        return cls(
            decision_id=data.get("decision_id", f"dp-{uuid4().hex[:8]}"),
            decision_type=DecisionPointType(data.get("decision_type", "turning_point")),
            turn_number=data.get("turn_number", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            narrative_context=data.get("narrative_context", ""),
            options=options,
            default_option_id=data.get("default_option_id"),
            dramatic_tension=Decimal(str(data.get("dramatic_tension", "5.0"))),
            emotional_intensity=Decimal(str(data.get("emotional_intensity", "5.0"))),
            timeout_seconds=data.get("timeout_seconds", 120),
            is_resolved=data.get("is_resolved", False),
            resolution=data.get("resolution"),
        )


@dataclass
class UserDecision:
    """User's response to a decision point."""

    decision_id: str
    input_type: str  # "option" or "freetext"

    # For option selection
    selected_option_id: Optional[int] = None

    # For free text input
    free_text: Optional[str] = None

    # Meta
    use_default: bool = False  # True if timeout or skip
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision_id": self.decision_id,
            "input_type": self.input_type,
            "selected_option_id": self.selected_option_id,
            "free_text": self.free_text,
            "use_default": self.use_default,
            "submitted_at": self.submitted_at.isoformat(),
        }


@dataclass
class NegotiationResult:
    """Result of LLM evaluation for free text user input."""

    decision_id: str
    feasibility: FeasibilityResult = FeasibilityResult.ACCEPTED

    # Explanation of why input was accepted/adjusted/rejected
    explanation: str = ""

    # If adjustment needed, the adjusted action
    adjusted_action: Optional[str] = None

    # Alternative options if original cannot be executed
    alternatives: List[DecisionOption] = field(default_factory=list)

    # Whether user has confirmed the negotiation result
    user_confirmed: bool = False
    user_insisted: bool = False  # User chose to insist on original input

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision_id": self.decision_id,
            "feasibility": self.feasibility.value,
            "explanation": self.explanation,
            "adjusted_action": self.adjusted_action,
            "alternatives": [alt.to_dict() for alt in self.alternatives],
            "user_confirmed": self.user_confirmed,
            "user_insisted": self.user_insisted,
        }


@dataclass
class PendingDecision:
    """Internal state for a pending decision awaiting user response."""

    decision_point: DecisionPoint
    user_response: Optional[UserDecision] = None
    negotiation_result: Optional[NegotiationResult] = None
    final_action: Optional[str] = None

    # State tracking
    state: PauseState = PauseState.AWAITING_INPUT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
