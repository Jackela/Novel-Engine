"""
Multi-Agent Bridge Package
===========================

Modular multi-agent coordination system for Novel Engine.
"""

from .core.types import (
    AgentDialogue,
    CommunicationType,
    DialogueState,
    EnhancedWorldState,
    LLMCoordinationConfig,
    RequestPriority,
)
from .enhanced_multi_agent_bridge_modular import EnhancedMultiAgentBridge

__all__ = [
    "EnhancedMultiAgentBridge",
    "RequestPriority",
    "CommunicationType",
    "DialogueState",
    "AgentDialogue",
    "LLMCoordinationConfig",
    "EnhancedWorldState",
]
