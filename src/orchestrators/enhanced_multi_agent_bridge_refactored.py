#!/usr/bin/env python3
"""
Refactored bridge placeholders for tests to patch.

The test suite patches classes from this module. We provide minimal stubs
so that patching works regardless of internal implementation details.
"""


class DialogueManager:  # pragma: no cover - test uses patch
    pass


class LLMCoordinator:  # pragma: no cover - test uses patch
    pass


class AIIntelligenceOrchestrator:  # pragma: no cover - test uses patch
    pass


class AgentCoordinationEngine:  # pragma: no cover - test uses patch
    pass


from typing import Any, Optional

from src.orchestrators.enhanced_multi_agent_bridge import (
    BridgeConfiguration as _BridgeConfig,
)
from src.orchestrators.enhanced_multi_agent_bridge import (
    EnhancedMultiAgentBridge as _Bridge,
)

# Expose the bridge class for tests that patch here
EnhancedMultiAgentBridge = _Bridge


async def create_enhanced_bridge(
    director_agent: Any, config: Optional[_BridgeConfig] = None
) -> _Bridge:
    """Create and initialize bridge using the exposed class here (supports patching)."""
    bridge = EnhancedMultiAgentBridge(director_agent, config)
    success = await bridge.initialize()
    if not success:
        raise RuntimeError("Failed to initialize enhanced multi-agent bridge")
    return bridge
