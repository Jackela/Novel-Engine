#!/usr/bin/env python3
"""
Enhanced Bridge Factory
=======================

Factory functions for creating and configuring the Enhanced Multi-Agent Bridge.
"""

import structlog
from typing import Any, Optional

from src.core.event_bus import EventBus

from .models import LLMCoordinationConfig, BridgeConfiguration
from .bridge_core import EnhancedMultiAgentBridge

__all__ = [
    "create_enhanced_bridge",
    "create_enhanced_multi_agent_bridge",
    "create_performance_optimized_config",
]

logger = structlog.get_logger(__name__)


async def create_enhanced_bridge(
    director_agent: Any, config: Optional[BridgeConfiguration] = None
) -> EnhancedMultiAgentBridge:
    """Factory to create and initialize the enhanced bridge for tests."""
    bridge = EnhancedMultiAgentBridge(director_agent, config)
    success = await bridge.initialize()
    if not success:
        raise RuntimeError("Failed to initialize enhanced multi-agent bridge")
    return bridge


def create_enhanced_multi_agent_bridge(
    event_bus: EventBus,
    director_agent: Optional[Any] = None,
    llm_coordination_config: Optional[LLMCoordinationConfig] = None,
) -> EnhancedMultiAgentBridge:
    """
    Factory function to create and configure an Enhanced Multi-Agent Bridge with LLM coordination.

    Args:
        event_bus: Event bus for agent communication
        director_agent: Optional existing director agent
        llm_coordination_config: Optional LLM coordination configuration

    Returns:
        Configured EnhancedMultiAgentBridge instance with LLM coordination
    """
    # Use default high-performance configuration if not provided
    if llm_coordination_config is None:
        llm_coordination_config = LLMCoordinationConfig(
            enable_smart_batching=True,
            max_batch_size=5,
            batch_timeout_ms=2000,
            priority_queue_enabled=True,
            cost_tracking_enabled=True,
            max_parallel_llm_calls=3,
            dialogue_generation_budget=2.0,
            coordination_temperature=0.8,
            max_turn_time_seconds=5.0,
            batch_priority_threshold=0.7,
            cost_alert_threshold=0.8,
        )

    bridge = EnhancedMultiAgentBridge(
        event_bus, director_agent, llm_coordination_config
    )
    logger.info("Enhanced Multi-Agent Bridge created with advanced LLM coordination")
    return bridge


def create_performance_optimized_config(
    max_turn_time_seconds: float = 5.0, budget_per_hour: float = 2.0
) -> LLMCoordinationConfig:
    """
    Create a performance-optimized LLM coordination configuration.

    Args:
        max_turn_time_seconds: Maximum time allowed per turn
        budget_per_hour: Budget in USD per hour for LLM usage

    Returns:
        Optimized LLMCoordinationConfig
    """
    return LLMCoordinationConfig(
        enable_smart_batching=True,
        max_batch_size=7,  # Larger batches for efficiency
        batch_timeout_ms=1500,  # Shorter timeout for responsiveness
        priority_queue_enabled=True,
        cost_tracking_enabled=True,
        max_parallel_llm_calls=4,  # More parallel calls
        dialogue_generation_budget=budget_per_hour,
        coordination_temperature=0.7,  # Slightly more focused
        max_turn_time_seconds=max_turn_time_seconds,
        batch_priority_threshold=0.6,  # Lower threshold for more priority processing
        cost_alert_threshold=0.85,  # Higher threshold for cost alerts
    )
