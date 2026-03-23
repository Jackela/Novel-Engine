"""Character memory adapter initialization.

Provides factory functions for creating memory adapter instances
with proper dependency injection.
"""

from __future__ import annotations

from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
)
from src.contexts.character.infrastructure.adapters.honcho_memory_adapter import (
    HonchoMemoryAdapter,
)
from src.shared.infrastructure.honcho import HonchoClient, HonchoSettings


async def create_honcho_memory_adapter(
    settings: HonchoSettings | None = None,
) -> CharacterMemoryPort:
    """Create a Honcho-based memory adapter.

    This factory function initializes the adapter with proper
    dependency injection.

    Args:
        settings: Optional Honcho settings. If None, uses defaults.

    Returns:
        Configured CharacterMemoryPort instance.

    Example:
        >>> adapter = await create_honcho_memory_adapter()
        >>> await adapter.initialize()
    """
    # Get or create Honcho client
    client = await HonchoClient.get_instance(settings)

    # Create adapter with injected client
    adapter = HonchoMemoryAdapter(honcho_client=client)
    await adapter.initialize()

    return adapter


async def create_memory_adapter() -> CharacterMemoryPort:
    """Create the default memory adapter for the application.

    This is the main entry point for getting a memory adapter.
    It uses the default configuration.

    Returns:
        CharacterMemoryPort instance.
    """
    return await create_honcho_memory_adapter()
