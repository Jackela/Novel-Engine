"""State Store Factory.

Factory functions for creating state store instances.
"""

from typing import Any, Optional

from src.infrastructure.state_store.base import StateStore
from src.infrastructure.state_store.config import StateStoreConfig, StateStoreType
from src.infrastructure.state_store.managers import (
    ConfigurationManager,
    UnifiedStateManager,
)


class StateStoreFactory:
    """Factory for creating state store instances."""

    @staticmethod
    def create_redis_store(
        config: Optional[StateStoreConfig] = None,
    ) -> Any:
        """Create Redis state store.

        Args:
            config: Optional configuration

        Returns:
            RedisStateStore instance
        """
        from src.infrastructure.state_store.redis import RedisStateStore

        if config is None:
            config = StateStoreConfig()
        return RedisStateStore(config)

    @staticmethod
    def create_postgres_store(
        config: Optional[StateStoreConfig] = None,
    ) -> Any:
        """Create PostgreSQL state store.

        Args:
            config: Optional configuration

        Returns:
            PostgreSQLStateStore instance
        """
        from src.infrastructure.state_store.postgres import PostgreSQLStateStore

        if config is None:
            config = StateStoreConfig()
        return PostgreSQLStateStore(config)

    @staticmethod
    def create_s3_store(
        config: Optional[StateStoreConfig] = None,
    ) -> Any:
        """Create S3 state store.

        Args:
            config: Optional configuration

        Returns:
            S3StateStore instance
        """
        from src.infrastructure.state_store.s3 import S3StateStore

        if config is None:
            config = StateStoreConfig()
        return S3StateStore(config)

    @staticmethod
    def create_memory_store(
        config: Optional[StateStoreConfig] = None,
    ) -> Any:
        """Create memory state store.

        Args:
            config: Optional configuration

        Returns:
            MemoryStateStore instance (uses Redis as fallback for now)
        """
        from src.infrastructure.state_store.redis import RedisStateStore

        if config is None:
            config = StateStoreConfig()
        return RedisStateStore(config)

    @staticmethod
    def create_store(
        config: Optional[StateStoreConfig] = None,
    ) -> Any:
        """Create state store based on config.

        Args:
            config: Optional configuration

        Returns:
            StateStore instance based on store_type
        """
        if config is None:
            config = StateStoreConfig()

        if config.store_type == StateStoreType.REDIS:
            return StateStoreFactory.create_redis_store(config)
        elif config.store_type in (StateStoreType.POSTGRES, StateStoreType.POSTGRESQL):
            return StateStoreFactory.create_postgres_store(config)
        elif config.store_type == StateStoreType.S3:
            return StateStoreFactory.create_s3_store(config)
        else:
            return StateStoreFactory.create_redis_store(config)


def create_unified_state_manager(
    config: Optional[StateStoreConfig] = None,
) -> UnifiedStateManager:
    """Create unified state manager.

    Args:
        config: Optional state store configuration.
            If not provided, creates default configuration.

    Returns:
        Initialized UnifiedStateManager instance
    """
    if config is None:
        config = StateStoreConfig()

    return UnifiedStateManager(config)


def create_configuration_manager(
    config: Optional[StateStoreConfig] = None,
) -> ConfigurationManager:
    """Create configuration manager.

    Args:
        config: Optional state store configuration.
            If not provided, creates default configuration.

    Returns:
        Initialized ConfigurationManager instance
    """
    if config is None:
        config = StateStoreConfig()

    return ConfigurationManager(config)
