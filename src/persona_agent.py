#!/usr/bin/env python3
"""
PersonaAgent - Backward Compatibility Interface

This module maintains backward compatibility by importing and exposing the
integrated PersonaAgent implementation. This ensures existing imports continue
to work while providing the benefits of modular architecture.

Original functionality is preserved through the integrated architecture:
- PersonaAgentCore: Core initialization and basic interfaces
- DecisionEngine: Decision-making and action selection
- CharacterInterpreter: Character data loading and interpretation
- MemoryInterface: Memory management and experience processing

Architecture Reference: Architecture_Blueprint.md Section 2.2 PersonaAgent
Development Phase: Modular Refactoring - Wave 4 Implementation
"""

# Import the integrated implementation
from src.persona_agent_integrated import PersonaAgent

# Re-export for backward compatibility
__all__ = ["PersonaAgent"]
