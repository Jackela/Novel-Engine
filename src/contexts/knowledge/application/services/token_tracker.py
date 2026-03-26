"""
Token Tracker Service

Warzone 4: AI Brain - BRAIN-034A
Middleware/decorator for tracking LLM token usage and costs.

Constitution Compliance:
- Article II (Hexagonal): Application service with no infrastructure dependencies
- Article V (SOLID): SRP - token tracking and cost calculation only

Usage:
    >>> tracker = TokenTracker(repository, model_registry)
    >>> # As decorator
    >>> @tracker.track_llm_call()
    >>> async def generate_text(prompt: str) -> str:
    >>>     # LLM call here
    >>>     return response
    >>>
    >>> # As context manager
    >>> async with tracker.track_call("gpt-4o", user_id="user-123") as ctx:
    >>>     result = await llm_client.generate(request)
    >>>     ctx.record_result(result)
"""

from ..ports.i_token_usage_repository import (
    ITokenUsageRepository,
)
from .model_registry import ModelRegistry
from .token_tracker_config import TokenTrackerConfig
from .token_tracker_core import TokenTrackerCore
from .tracking_context import TrackingContext


class TokenTracker(TokenTrackerCore):
    """
    Facade combining all token tracking operations.

    This is the main entry point for token tracking functionality.
    It inherits from TokenTrackerCore which contains the actual implementation.

    Example (decorator):
        >>> tracker = TokenTracker(repository, model_registry)
        >>>
        >>> @tracker.track_llm_call(provider="openai", model_name="gpt-4o")
        >>> async def generate_story(scene: str) -> str:
        >>>     return await llm_client.generate(scene)

    Example (context manager):
        >>> async with tracker.track_call("gpt-4o") as ctx:
        >>>     response = await llm_client.generate(request)
        >>>     ctx.record_success(
        >>>         input_tokens=response.usage.prompt_tokens,
        >>>         output_tokens=response.usage.completion_tokens,
        >>>     )
    """

    def __init__(
        self,
        repository: ITokenUsageRepository,
        model_registry: ModelRegistry,
        config: TokenTrackerConfig | None = None,
    ) -> None:
        """
        Initialize the token tracker.

        Args:
            repository: Repository for persisting usage records
            model_registry: Model registry for pricing information
            config: Optional tracker configuration
        """
        super().__init__(
            repository=repository,
            model_registry=model_registry,
            config=config,
        )


def create_token_tracker(
    repository: ITokenUsageRepository,
    model_registry: ModelRegistry,
    config: TokenTrackerConfig | None = None,
) -> TokenTracker:
    """
    Factory function to create a configured TokenTracker.

    Args:
        repository: Repository for persisting usage records
        model_registry: Model registry for pricing information
        config: Optional tracker configuration

    Returns:
        Configured TokenTracker instance
    """
    return TokenTracker(
        repository=repository,
        model_registry=model_registry,
        config=config or TokenTrackerConfig(),
    )


__all__ = [
    "TokenTracker",
    "TrackingContext",
    "TokenTrackerConfig",
    "TokenAwareConfig",
    "create_token_tracker",
]

# Re-export for backward compatibility
from .token_tracker_config import TokenAwareConfig
