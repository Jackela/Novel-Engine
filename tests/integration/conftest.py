"""Integration test fixtures."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Test settings."""
    from src.shared.infrastructure.config.settings import Settings

    return Settings(
        database_url="postgresql://test:test@localhost:5433/test", environment="testing"
    )


@pytest.fixture
def sample_uuid() -> UUID:
    """Provide a sample UUID for tests."""
    return uuid4()


@pytest.fixture
async def memory_event_bus():
    """Provide a started memory event bus."""
    from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

    bus = MemoryEventBus()
    await bus.start()
    yield bus
    await bus.stop()
