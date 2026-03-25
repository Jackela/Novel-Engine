"""Circuit breaker implementation for external service protection."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Optional, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = auto()  # Normal operation
    OPEN = auto()  # Failing, reject requests
    HALF_OPEN = auto()  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures."""

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        expected_exception: type[BaseException]
        | tuple[type[BaseException], ...] = Exception,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def get_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self._state.name.lower(),
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time.isoformat()
            if self._last_failure_time
            else None,
        }

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call function with circuit breaker protection."""
        await self._check_state()

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception:
            await self._on_failure()
            raise

    async def _check_state(self) -> None:
        """Check and update circuit state before making a call."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"Circuit {self.name} entering half-open state")
                else:
                    raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")

            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name} is OPEN (half-open limit reached)"
                    )

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit {self.name} closed after recovery")
            else:
                self._failure_count = max(0, self._failure_count - 1)

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} opened after half-open failure")
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.name} opened after {self.config.failure_threshold} failures"
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        elapsed = datetime.utcnow() - self._last_failure_time
        return elapsed >= timedelta(seconds=self.config.recovery_timeout)

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(f"Circuit {self.name} manually reset to closed state")


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers."""

    _circuit_breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def register(cls, name: str, circuit_breaker: CircuitBreaker) -> None:
        """Register a circuit breaker."""
        cls._circuit_breakers[name] = circuit_breaker
        logger.info(f"Registered circuit breaker: {name}")

    @classmethod
    def get(cls, name: str) -> CircuitBreaker:
        """Get circuit breaker by name."""
        if name not in cls._circuit_breakers:
            raise KeyError(f"Circuit breaker '{name}' not found in registry")
        return cls._circuit_breakers[name]

    @classmethod
    def get_or_create(
        cls,
        name: str,
        config: CircuitBreakerConfig | None = None,
        expected_exception: type[BaseException]
        | tuple[type[BaseException], ...] = Exception,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create a new one."""
        if name not in cls._circuit_breakers:
            cb = CircuitBreaker(name, config, expected_exception)
            cls.register(name, cb)
        return cls._circuit_breakers[name]

    @classmethod
    def get_all_states(cls) -> dict[str, dict[str, Any]]:
        """Get all circuit breaker states for monitoring."""
        return {name: cb.get_metrics() for name, cb in cls._circuit_breakers.items()}

    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        for cb in cls._circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a circuit breaker."""
        if name in cls._circuit_breakers:
            del cls._circuit_breakers[name]
            logger.info(f"Unregistered circuit breaker: {name}")


# Pre-configured circuit breakers for common services
def register_default_circuit_breakers() -> None:
    """Register default circuit breakers for common services."""

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

    logger.info("Default circuit breakers registered")
