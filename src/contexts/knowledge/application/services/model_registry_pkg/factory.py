"""Model Registry Factory."""

from typing import Optional

from src.contexts.knowledge.application.services.model_registry_pkg.config import (
    ModelRegistryConfig,
)
from src.contexts.knowledge.application.services.model_registry_pkg.registry import (
    ModelRegistry,
)


def create_model_registry(
    config: Optional[ModelRegistryConfig] = None,
) -> ModelRegistry:
    """
    Factory function to create a ModelRegistry.

    Why factory:
        - Provides convenient instantiation
        - Allows for future dependency injection
        - Consistent with other service factories

    Args:
        config: Optional registry configuration

    Returns:
        Configured ModelRegistry instance
    """
    return ModelRegistry(config)


__all__ = [
    "ModelRegistry",
    "ModelRegistryConfig",
    "create_model_registry",
]
