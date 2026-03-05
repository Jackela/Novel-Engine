"""Enhanced Multi-Agent Bridge Module.

This module provides the enhanced multi-agent bridge functionality,
now split into focused submodules for better maintainability.
"""

from .bridge_core import (
    EnhancedMultiAgentBridge,
    create_enhanced_bridge,
    create_enhanced_multi_agent_bridge,
)
from .dialogue_manager import DialogueManager
from .state_manager import StateManager
from .task_scheduler import TaskScheduler
from .types import (
    AgentDialogue,
    BridgeConfiguration,
    CommunicationType,
    CostTracker,
    DialogueState,
    EnhancedWorldState,
    LLMBatchRequest,
    LLMCoordinationConfig,
    PerformanceBudget,
    RequestPriority,
)

__all__ = [
    # Core classes
    "EnhancedMultiAgentBridge",
    "DialogueManager",
    "StateManager",
    "TaskScheduler",
    # Types
    "AgentDialogue",
    "BridgeConfiguration",
    "CommunicationType",
    "CostTracker",
    "DialogueState",
    "EnhancedWorldState",
    "LLMBatchRequest",
    "LLMCoordinationConfig",
    "PerformanceBudget",
    "RequestPriority",
    # Factory functions
    "create_enhanced_bridge",
    "create_enhanced_multi_agent_bridge",
]
