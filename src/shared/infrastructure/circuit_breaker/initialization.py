"""Circuit breaker initialization for Novel Engine.

This module handles the initialization and configuration of circuit breakers
when the application starts.
"""

from __future__ import annotations

import structlog

from src.shared.infrastructure.circuit_breaker import (
    CircuitBreakerRegistry,
    register_default_circuit_breakers,
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
    register_default_circuit_breakers()
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
