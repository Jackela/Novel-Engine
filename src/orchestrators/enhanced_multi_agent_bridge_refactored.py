#!/usr/bin/env python3
"""Refactored bridge wrapper that forwards to the real bridge implementation."""

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
