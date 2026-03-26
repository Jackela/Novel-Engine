"""Circuit breaker and resilience patterns for Novel Engine."""

from src.shared.infrastructure.circuit_breaker.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitState,
    register_default_circuit_breakers,
)
from src.shared.infrastructure.circuit_breaker.config import CircuitBreakerSettings

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
    "CircuitState",
    "register_default_circuit_breakers",
    # Configuration
    "CircuitBreakerSettings",
]
