from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitState,
    register_default_circuit_breakers,
)
from src.shared.infrastructure.circuit_breaker.config import CircuitBreakerSettings
from src.shared.infrastructure.circuit_breaker.initialization import (
    get_circuit_breaker_states,
    initialize_circuit_breakers,
    reset_all_circuit_breakers,
)


class ExpectedServiceError(Exception):
    pass


class UnexpectedServiceError(Exception):
    pass


async def succeed(value: str = "ok") -> str:
    return value


async def fail_expected() -> str:
    raise ExpectedServiceError("expected failure")


async def fail_unexpected() -> str:
    raise UnexpectedServiceError("unexpected failure")


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    CircuitBreakerRegistry._circuit_breakers.clear()


@pytest.mark.asyncio
async def test_circuit_opens_after_failure_threshold() -> None:
    breaker = CircuitBreaker(
        "service",
        CircuitBreakerConfig(failure_threshold=2),
        expected_exception=ExpectedServiceError,
    )

    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)
    assert breaker.state.name == CircuitState.CLOSED.name
    assert breaker.failure_count == 1

    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)
    assert breaker.state.name == CircuitState.OPEN.name

    with pytest.raises(CircuitBreakerOpenError, match="service"):
        await breaker.call(succeed)


@pytest.mark.asyncio
async def test_open_circuit_enters_half_open_after_recovery_timeout() -> None:
    breaker = CircuitBreaker(
        "service",
        CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=30,
            success_threshold=2,
        ),
        expected_exception=ExpectedServiceError,
    )
    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)
    breaker._last_failure_time = datetime.utcnow() - timedelta(seconds=31)

    assert await breaker.call(succeed, "first") == "first"
    assert breaker.state.name == CircuitState.HALF_OPEN.name
    assert breaker.get_metrics()["half_open_call_count"] == 1

    assert await breaker.call(succeed, "second") == "second"
    assert breaker.state.name == CircuitState.CLOSED.name
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_half_open_call_limit_rejects_extra_probe_calls() -> None:
    breaker = CircuitBreaker(
        "service",
        CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0,
            half_open_max_calls=1,
            success_threshold=3,
        ),
        expected_exception=ExpectedServiceError,
    )
    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)

    assert await breaker.call(succeed) == "ok"
    assert breaker.state.name == CircuitState.HALF_OPEN.name

    with pytest.raises(CircuitBreakerOpenError, match="half-open limit"):
        await breaker.call(succeed)


@pytest.mark.asyncio
async def test_half_open_failure_reopens_circuit() -> None:
    breaker = CircuitBreaker(
        "service",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0),
        expected_exception=ExpectedServiceError,
    )
    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)

    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)

    assert breaker.state.name == CircuitState.OPEN.name
    assert breaker.get_metrics()["half_open_call_count"] == 0


@pytest.mark.asyncio
async def test_unexpected_exception_does_not_trip_circuit() -> None:
    breaker = CircuitBreaker(
        "service",
        CircuitBreakerConfig(failure_threshold=1),
        expected_exception=ExpectedServiceError,
    )

    with pytest.raises(UnexpectedServiceError):
        await breaker.call(fail_unexpected)

    assert breaker.state.name == CircuitState.CLOSED.name
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_closed_success_reduces_failure_count() -> None:
    breaker = CircuitBreaker(
        "service",
        CircuitBreakerConfig(failure_threshold=3),
        expected_exception=ExpectedServiceError,
    )
    with pytest.raises(ExpectedServiceError):
        await breaker.call(fail_expected)

    assert await breaker.call(succeed) == "ok"

    assert breaker.failure_count == 0
    assert breaker.state.name == CircuitState.CLOSED.name


def test_reset_clears_state_and_metrics() -> None:
    breaker = CircuitBreaker("service")
    breaker._state = CircuitState.OPEN
    breaker._failure_count = 3
    breaker._success_count = 2
    breaker._half_open_call_count = 1
    breaker._last_failure_time = datetime.utcnow()

    breaker.reset()

    assert breaker.state.name == CircuitState.CLOSED.name
    assert breaker.get_metrics() == {
        "name": "service",
        "state": "closed",
        "failure_count": 0,
        "success_count": 0,
        "half_open_call_count": 0,
        "last_failure_time": None,
    }


def test_registry_registers_gets_resets_and_unregisters() -> None:
    breaker = CircuitBreaker("service")

    CircuitBreakerRegistry.register("service", breaker)
    assert CircuitBreakerRegistry.get("service") is breaker
    assert CircuitBreakerRegistry.get_or_create("service") is breaker
    assert "service" in CircuitBreakerRegistry.get_all_states()

    CircuitBreakerRegistry.reset_all()
    CircuitBreakerRegistry.unregister("service")

    with pytest.raises(KeyError, match="not found"):
        CircuitBreakerRegistry.get("service")


def test_default_initialization_registers_expected_services() -> None:
    initialize_circuit_breakers()

    states = get_circuit_breaker_states()

    assert set(states) == {"openai_api", "database", "external_service"}
    assert states["openai_api"]["state"] == "closed"

    reset_all_circuit_breakers()
    assert all(state["state"] == "closed" for state in get_circuit_breaker_states().values())


def test_register_default_circuit_breakers_is_directly_usable() -> None:
    register_default_circuit_breakers()

    assert CircuitBreakerRegistry.get("database").config.failure_threshold == 10


def test_circuit_breaker_settings_defaults() -> None:
    settings = CircuitBreakerSettings()

    assert settings.enabled is True
    assert settings.openai_failure_threshold == 3
    assert settings.embedding_fallback_to_zero is True
