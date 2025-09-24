#!/usr/bin/env python3
"""
Shared Types - Backward Compatibility Interface

This module maintains backward compatibility by importing and exposing the
shared types from both core types modules. This ensures existing imports continue
to work while providing the benefits of modular architecture.

Development Phase: Phase 1 Validation - Import Compatibility
"""

# Import from both types modules for full compatibility
try:
    # Import from the main shared types module
    # Also import from the core types module to get CharacterAction
    from src.core.types.shared_types import ActionPriority, CharacterAction
    from src.shared_types import *  # noqa: F403

    # Handle potential naming conflicts by keeping both available
    TYPES_AVAILABLE = True

except ImportError as e:
    # Fallback if modules aren't available
    TYPES_AVAILABLE = False
    print(f"Warning: Could not import all shared types: {e}")

# Re-export everything for backward compatibility
try:
    # Core types that should always be available
    _core_exports = ["CharacterAction", "ActionType", "ActionPriority"]

    # Extended types from main module
    _extended_exports = [
        "CampaignEvent",
        "NarrativeSegment",
        "WorldEvent",
        "SubjectiveInterpretation",
        "ThreatLevel",
        "EventType",
        "CharacterData",
        "DecisionContext",
        "MemoryEntry",
        "AgentConfig",
        "ProposedAction",
        "ValidatedAction",
        "ActionTarget",
        "ActionParameters",
    ]

    # Dynamically build __all__ based on what's available
    __all__ = []
    for name in _core_exports + _extended_exports:
        if name in globals():
            __all__.append(name)

    if not __all__:
        __all__ = ["TYPES_AVAILABLE"]

except Exception:
    __all__ = ["TYPES_AVAILABLE"]
