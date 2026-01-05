"""
Decision Module - User Participatory Interaction

This module provides functionality for user intervention in story generation,
allowing users to influence narrative direction at key decision points.
"""

from .api_router import initialize_decision_system
from .api_router import router as decision_router
from .decision_point_detector import DecisionPointDetector
from .models import (
    DecisionOption,
    DecisionPoint,
    DecisionPointType,
    FeasibilityResult,
    NegotiationResult,
    PauseState,
    PendingDecision,
    UserDecision,
)
from .negotiation_engine import NegotiationEngine
from .pause_controller import InteractionPauseController

__all__ = [
    # Models
    "DecisionPointType",
    "FeasibilityResult",
    "PauseState",
    "DecisionPoint",
    "DecisionOption",
    "UserDecision",
    "NegotiationResult",
    "PendingDecision",
    # Controllers
    "InteractionPauseController",
    "DecisionPointDetector",
    "NegotiationEngine",
    # API
    "decision_router",
    "initialize_decision_system",
]
