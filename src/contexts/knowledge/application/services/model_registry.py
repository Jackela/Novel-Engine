"""Model Registry Service (Shim).

⚠️  DEPRECATION NOTICE:
    This module is kept for backward compatibility.
    Please use `src.contexts.knowledge.application.services.model_registry_pkg` instead.
"""

import warnings

warnings.warn(
    "model_registry.py is deprecated. "
    "Use src.contexts.knowledge.application.services.model_registry_pkg instead.",
    DeprecationWarning,
    stacklevel=2,
)

from src.contexts.knowledge.application.services.model_registry_pkg.config import (
    DEFAULT_ALIASES,
    DEFAULT_MODELS,
    DEFAULT_TASK_CONFIGS,
    ModelLookupResult,
    ModelRegistryConfig,
    ModelRegistryConfigFile,
)
from src.contexts.knowledge.application.services.model_registry_pkg.registry import (
    ModelRegistry,
)
from src.contexts.knowledge.application.services.model_registry_pkg.factory import (
    create_model_registry,
)

__all__ = [
    "DEFAULT_ALIASES",
    "DEFAULT_MODELS",
    "DEFAULT_TASK_CONFIGS",
    "ModelLookupResult",
    "ModelRegistryConfig",
    "ModelRegistryConfigFile",
    "ModelRegistry",
    "create_model_registry",
]
