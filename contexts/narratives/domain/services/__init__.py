#!/usr/bin/env python3
"""
Narrative Domain Services Package

This package contains domain services that implement complex business logic
for the Narrative bounded context.

Key Domain Services:
- CausalGraphService: Manages cause-and-effect relationships in narratives
- NarrativeFlowService: Manages story flow and sequence optimization
- ThemeAnalysisService: Analyzes thematic consistency and development
"""

from .causal_graph_service import CausalGraphService
from .narrative_flow_service import NarrativeFlowService

__all__ = ["CausalGraphService", "NarrativeFlowService"]

__version__ = "1.0.0"
