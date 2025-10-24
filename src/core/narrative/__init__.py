#!/usr/bin/env python3
"""
涌现式叙事系统 (Emergent Narrative System)

Backward-compatible exports maintaining original API.

Milestone 2 Implementation: CausalGraph + Multi-Agent Negotiation + Narrative Coherence
"""

# Export all types
from .types import (
    CausalEdge,
    CausalNode,
    CausalRelationType,
    EventPriority,
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
)

# Export main classes
from .causal_graph import CausalGraph
from .emergent_narrative import EmergentNarrativeEngine, create_emergent_narrative_engine
from .narrative_coherence import NarrativeCoherenceEngine
from .negotiation import AgentNegotiationEngine

__all__ = [
    # Types
    "CausalRelationType",
    "NegotiationStatus",
    "EventPriority",
    "CausalNode",
    "CausalEdge",
    "NegotiationProposal",
    "NegotiationResponse",
    "NegotiationSession",
    # Main classes
    "CausalGraph",
    "AgentNegotiationEngine",
    "NarrativeCoherenceEngine",
    "EmergentNarrativeEngine",
    # Factory
    "create_emergent_narrative_engine",
]
