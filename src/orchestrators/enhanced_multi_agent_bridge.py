#!/usr/bin/env python3
"""
Enhanced Multi-Agent Bridge (Shim)
===================================

⚠️  DEPRECATION NOTICE:
    This module is kept for backward compatibility.
    Please use `src.orchestrators.enhanced_bridge` instead.

    Old: from src.orchestrators.enhanced_multi_agent_bridge import EnhancedMultiAgentBridge
    New: from src.orchestrators.enhanced_bridge import EnhancedMultiAgentBridge
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "enhanced_multi_agent_bridge.py is deprecated. "
    "Use src.orchestrators.enhanced_bridge instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all symbols from the new package
from src.orchestrators.enhanced_bridge.types import (
    CommunicationType,
    DialogueState,
    RequestPriority,
)
from src.orchestrators.enhanced_bridge.models import (
    AgentDialogue,
    BridgeConfiguration,
    CostTracker,
    EnhancedWorldState,
    LLMBatchRequest,
    LLMCoordinationConfig,
    PerformanceBudget,
)
from src.orchestrators.enhanced_bridge.bridge_core import EnhancedMultiAgentBridge
from src.orchestrators.enhanced_bridge.factory import (
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
