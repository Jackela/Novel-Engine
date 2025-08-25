"""
Multi-Agent Bridge Package
===========================

Modular multi-agent coordination system for Novel Engine.
"""

from .enhanced_multi_agent_bridge_modular import EnhancedMultiAgentBridge
from .core.types import (
    RequestPriority, CommunicationType, DialogueState, 
    AgentDialogue, LLMCoordinationConfig, EnhancedWorldState
)

__all__ = [
    'EnhancedMultiAgentBridge',
    'RequestPriority',
    'CommunicationType', 
    'DialogueState',
    'AgentDialogue',
    'LLMCoordinationConfig',
    'EnhancedWorldState'
]