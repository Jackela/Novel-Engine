"""Circuit breaker configuration settings."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CircuitBreakerSettings(BaseModel):
    """Settings for circuit breaker configuration."""

    # Global settings
    enabled: bool = Field(default=True, description="Enable circuit breaker protection")

    # OpenAI API settings - more sensitive as it's external
    openai_failure_threshold: int = Field(
        default=3, description="Failures before opening OpenAI circuit"
    )
    openai_recovery_timeout: float = Field(
        default=60.0, description="Seconds before attempting recovery"
    )
    openai_half_open_max_calls: int = Field(
        default=2, description="Max calls in half-open state"
    )

    # Honcho API settings
    honcho_failure_threshold: int = Field(
        default=5, description="Failures before opening Honcho circuit"
    )
    honcho_recovery_timeout: float = Field(
        default=30.0, description="Seconds before attempting recovery"
    )
    honcho_half_open_max_calls: int = Field(
        default=3, description="Max calls in half-open state"
    )

    # Database settings - less sensitive
    database_failure_threshold: int = Field(
        default=10, description="Failures before opening database circuit"
    )
    database_recovery_timeout: float = Field(
        default=30.0, description="Seconds before attempting recovery"
    )
    database_half_open_max_calls: int = Field(
        default=3, description="Max calls in half-open state"
    )

    # External service settings
    external_failure_threshold: int = Field(
        default=5, description="Failures before opening external service circuit"
    )
    external_recovery_timeout: float = Field(
        default=45.0, description="Seconds before attempting recovery"
    )
    external_half_open_max_calls: int = Field(
        default=2, description="Max calls in half-open state"
    )

    # Embedding service fallback settings
    embedding_fallback_to_zero: bool = Field(
        default=True, description="Return zero embeddings when circuit is open"
    )
    embedding_enable_cache: bool = Field(
        default=True, description="Enable caching for embedding fallbacks"
    )

    # Retry settings
    retry_max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_base_delay: float = Field(
        default=1.0, description="Base delay between retries (seconds)"
    )
    retry_max_delay: float = Field(
        default=30.0, description="Maximum delay between retries (seconds)"
    )

    class Config:
        """Pydantic config."""

        env_prefix = "CIRCUIT_BREAKER_"
