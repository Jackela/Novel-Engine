import pytest

from src.core.event_bus import EventBus
from src.orchestrators.enhanced_multi_agent_bridge import (
    BridgeConfiguration,
    EnhancedMultiAgentBridge,
    create_enhanced_bridge,
)

pytestmark = pytest.mark.integration


class _StubDirector:
    def __init__(self) -> None:
        self.event_bus = EventBus()


@pytest.mark.asyncio
async def test_create_enhanced_bridge_initializes() -> None:
    director = _StubDirector()
    config = BridgeConfiguration()

    bridge = await create_enhanced_bridge(director, config)

    assert isinstance(bridge, EnhancedMultiAgentBridge)
    assert bridge._initialized is True
    assert bridge.event_bus is director.event_bus


@pytest.mark.asyncio
async def test_create_enhanced_bridge_uses_llm_config() -> None:
    director = _StubDirector()
    config = BridgeConfiguration()
    config.llm_coordination.max_batch_size = 8

    bridge = await create_enhanced_bridge(director, config)

    assert bridge.llm_config.max_batch_size == 8
