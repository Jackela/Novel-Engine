"""
Decision Module - User Participatory Interaction

This module provides functionality for user intervention in story generation,
allowing users to influence narrative direction at key decision points.
"""

from .models import (
    DecisionPointType,
    FeasibilityResult,
    PauseState,
    DecisionPoint,
    DecisionOption,
    UserDecision,
    NegotiationResult,
    PendingDecision,
)
from .pause_controller import InteractionPauseController
from .decision_point_detector import DecisionPointDetector
from .negotiation_engine import NegotiationEngine
from .api_router import router as decision_router, initialize_decision_system

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
