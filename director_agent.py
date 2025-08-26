#!/usr/bin/env python3
"""
DirectorAgent - Backward Compatibility Interface

This module maintains backward compatibility by importing and exposing the
integrated DirectorAgent implementation. This ensures existing imports continue
to work while providing the benefits of modular architecture.

Original functionality is preserved through the integrated architecture:
- DirectorAgentBase: Core initialization and basic interfaces
- TurnOrchestrator: Turn execution and coordination
- WorldStateCoordinator: World state management and persistence  
- AgentLifecycleManager: Iron Laws validation and action adjudication
"""

# Import the integrated implementation
from director_agent_integrated import DirectorAgent

# Re-export for backward compatibility
__all__ = ['DirectorAgent']