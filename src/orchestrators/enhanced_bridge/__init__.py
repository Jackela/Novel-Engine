#!/usr/bin/env python3
"""
Enhanced Multi-Agent Bridge
===========================

Wave Mode Enhancement Bridge that connects the existing advanced AI intelligence
systems with the core Novel Engine simulation loop.

This package provides:
- Real-time agent-to-agent communication during simulation
- Advanced coordination through existing enterprise systems
- Intelligent conflict resolution and narrative coherence
- Performance optimization and quality monitoring
"""

from .types import (
    CommunicationType,
    DialogueState,
    RequestPriority,
)
from .models import (
    AgentDialogue,
    BridgeConfiguration,
    CostTracker,
    EnhancedWorldState,
    LLMBatchRequest,
    LLMCoordinationConfig,
    PerformanceBudget,
)
from .bridge_core import EnhancedMultiAgentBridge
from .factory import (
    create_enhanced_bridge,
    create_enhanced_multi_agent_bridge,
    create_performance_optimized_config,
)

__all__ = [
    # Types
    "RequestPriority",
    "CommunicationType",
    "DialogueState",
    # Models
    "AgentDialogue",
    "LLMCoordinationConfig",
    "LLMBatchRequest",
    "CostTracker",
    "PerformanceBudget",
    "EnhancedWorldState",
    "BridgeConfiguration",
    # Core
    "EnhancedMultiAgentBridge",
    # Factory
    "create_enhanced_bridge",
    "create_enhanced_multi_agent_bridge",
    "create_performance_optimized_config",
]
