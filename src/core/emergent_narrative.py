#!/usr/bin/env python3
"""
涌现式叙事系统 (Emergent Narrative System)
=======================================

⚠️  DEPRECATED: This module has been refactored into separate modules.
    Please import from src.core.narrative instead.

Backward-compatible wrapper - imports still work but please migrate to:
    from src.core.narrative import EmergentNarrativeEngine, CausalGraph, etc.

New module structure:
- src.core.narrative.types - Shared enums and dataclasses
- src.core.narrative.causal_graph - CausalGraph implementation
- src.core.narrative.negotiation - AgentNegotiationEngine
- src.core.narrative.narrative_coherence - NarrativeCoherenceEngine
- src.core.narrative.emergent_narrative - Main orchestrator
"""

import warnings

# Re-export everything from new location for backward compatibility
from src.core.narrative import (
    AgentNegotiationEngine,
    CausalEdge,
    CausalGraph,
    CausalNode,
    CausalRelationType,
    EmergentNarrativeEngine,
    EventPriority,
    NarrativeCoherenceEngine,
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
    create_emergent_narrative_engine,
)

# Issue deprecation warning
warnings.warn(
    "Importing from src.core.emergent_narrative is deprecated. "
    "Please use: from src.core.narrative import EmergentNarrativeEngine, ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CausalRelationType",
    "NegotiationStatus",
    "EventPriority",
    "CausalNode",
    "CausalEdge",
    "NegotiationProposal",
    "NegotiationResponse",
    "NegotiationSession",
    "CausalGraph",
    "AgentNegotiationEngine",
    "NarrativeCoherenceEngine",
    "EmergentNarrativeEngine",
    "create_emergent_narrative_engine",
]
