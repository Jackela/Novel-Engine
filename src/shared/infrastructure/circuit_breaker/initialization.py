"""Circuit breaker initialization for Novel Engine.

This module handles the initialization and configuration of circuit breakers
when the application starts.
"""

from __future__ import annotations

import structlog

from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
)

logger = structlog.get_logger(__name__)


def initialize_circuit_breakers() -> None:
    """Initialize all circuit breakers for the application.

    This function should be called during application startup to register
    all circuit breakers with their default configurations.

    Example:
        >>> from src.shared.infrastructure.circuit_breaker.initialization import initialize_circuit_breakers
        >>> initialize_circuit_breakers()
    """
    logger.info("Initializing circuit breakers")

    # OpenAI API circuit breaker - more sensitive as it's external
    CircuitBreakerRegistry.register(
        "openai_api",
        CircuitBreaker(
            name="openai_api",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60.0,
                half_open_max_calls=2,
                success_threshold=2,
            ),
            expected_exception=(Exception,),
        ),
    )
    logger.debug("Registered OpenAI API circuit breaker")

    # Honcho API circuit breaker
    CircuitBreakerRegistry.register(
        "honcho_api",
        CircuitBreaker(
            name="honcho_api",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30.0,
                half_open_max_calls=3,
                success_threshold=2,
            ),
            expected_exception=(Exception,),
        ),
    )
    logger.debug("Registered Honcho API circuit breaker")

    # Database circuit breaker - less sensitive
    CircuitBreakerRegistry.register(
        "database",
        CircuitBreaker(
            name="database",
            config=CircuitBreakerConfig(
                failure_threshold=10,
                recovery_timeout=30.0,
                half_open_max_calls=3,
                success_threshold=2,
            ),
            expected_exception=(Exception,),
        ),
    )
    logger.debug("Registered database circuit breaker")

    # External service circuit breaker
    CircuitBreakerRegistry.register(
        "external_service",
        CircuitBreaker(
            name="external_service",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=45.0,
                half_open_max_calls=2,
                success_threshold=2,
            ),
            expected_exception=(Exception,),
        ),
    )
    logger.debug("Registered external service circuit breaker")

    logger.info("All circuit breakers initialized successfully")


def get_circuit_breaker_states() -> dict[str, dict]:
    """Get the current state of all circuit breakers.

    Returns:
        Dictionary mapping circuit breaker names to their current states.
    """
    return CircuitBreakerRegistry.get_all_states()


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers to closed state.

    This can be useful for manual recovery or testing purposes.
    """
    logger.warning("Resetting all circuit breakers")
    CircuitBreakerRegistry.reset_all()
    logger.info("All circuit breakers reset")
