# mypy: ignore-errors
"""State Store (Shim).

⚠️  DEPRECATION NOTICE:
    This module is kept for backward compatibility.
    Please use `src.infrastructure.state_store` instead.
"""

import warnings

warnings.warn(
    "state_store.py is deprecated. " "Use src.infrastructure.state_store instead.",
    DeprecationWarning,
    stacklevel=2,
)

from src.infrastructure.state_store.base import StateStore
from src.infrastructure.state_store.config import StateKey, StateStoreConfig
from src.infrastructure.state_store.factory import (
    create_configuration_manager,
    create_unified_state_manager,
)
from src.infrastructure.state_store.managers import (
    ConfigurationManager,
    UnifiedStateManager,
)
from src.infrastructure.state_store.postgres import PostgreSQLStateStore
from src.infrastructure.state_store.redis import RedisStateStore
from src.infrastructure.state_store.s3 import S3StateStore

__all__ = [
    "StateStore",
    "StateKey",
    "StateStoreConfig",
    "RedisStateStore",
    "PostgreSQLStateStore",
    "S3StateStore",
    "UnifiedStateManager",
    "ConfigurationManager",
    "create_unified_state_manager",
    "create_configuration_manager",
]
