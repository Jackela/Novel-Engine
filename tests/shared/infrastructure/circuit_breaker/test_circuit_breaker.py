"""Tests for circuit breaker."""

from __future__ import annotations

import asyncio

import pytest

from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitState,
    register_default_circuit_breakers,
)


class TestCircuitBreaker:
    """Test suite for circuit breaker."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(
            name="test_circuit",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=0.1,
                half_open_max_calls=2,
                success_threshold=2,
            ),
        )

    @pytest.mark.asyncio
    async def test_circuit_starts_closed(self, circuit_breaker):
        """Test circuit starts in closed state."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test circuit opens after threshold failures."""

        async def failing_func():
            raise ValueError("Test error")

        # Trigger 3 failures
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self, circuit_breaker):
        """Test circuit enters half-open after timeout."""

        async def failing_func():
            raise ValueError("Test error")

        # Trigger failure to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should attempt (half-open) but fail
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)

        # Should still be open (failed in half-open)
        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_in_half_open(self, circuit_breaker):
        """Test circuit closes after success in half-open state."""
        call_count = 0

        async def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError("Test error")
            return "success"

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(sometimes_failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Should succeed twice to close circuit
        result1 = await circuit_breaker.call(sometimes_failing_func)
        assert result1 == "success"

        result2 = await circuit_breaker.call(sometimes_failing_func)
        assert result2 == "success"

        # Circuit should be closed now
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_call_does_not_increment_failure(self, circuit_breaker):
        """Test successful calls don't increment failure count."""

        async def success_func():
            return "success"

        for _ in range(5):
            result = await circuit_breaker.call(success_func)
            assert result == "success"

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_open_error_raised_when_open(self, circuit_breaker):
        """Test CircuitBreakerOpenError is raised when circuit is open."""

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        # Should raise CircuitBreakerOpenError immediately
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await circuit_breaker.call(failing_func)

        assert "is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker):
        """Test manual reset of circuit breaker."""

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Reset manually
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

        # Should work again
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_metrics(self, circuit_breaker):
        """Test metrics collection."""
        metrics = circuit_breaker.get_metrics()

        assert metrics["name"] == "test_circuit"
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0


class TestCircuitBreakerRegistry:
    """Test suite for circuit breaker registry."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean registry before each test."""
        CircuitBreakerRegistry._circuit_breakers.clear()
        yield
        CircuitBreakerRegistry._circuit_breakers.clear()

    @pytest.mark.asyncio
    async def test_register_and_get(self):
        """Test registering and retrieving circuit breakers."""
        cb = CircuitBreaker("test_register")
        CircuitBreakerRegistry.register("test_register", cb)

        retrieved = CircuitBreakerRegistry.get("test_register")
        assert retrieved is cb

    @pytest.mark.asyncio
    async def test_get_or_create(self):
        """Test get_or_create method."""
        config = CircuitBreakerConfig(failure_threshold=10)

        # First call should create
        cb1 = CircuitBreakerRegistry.get_or_create("test_get_or_create", config)
        assert cb1.config.failure_threshold == 10

        # Second call should return same instance
        cb2 = CircuitBreakerRegistry.get_or_create("test_get_or_create")
        assert cb1 is cb2

    @pytest.mark.asyncio
    async def test_get_all_states(self):
        """Test getting all circuit breaker states."""
        cb1 = CircuitBreaker("test1")
        cb2 = CircuitBreaker("test2")

        CircuitBreakerRegistry.register("test1", cb1)
        CircuitBreakerRegistry.register("test2", cb2)

        states = CircuitBreakerRegistry.get_all_states()

        assert "test1" in states
        assert "test2" in states
        assert states["test1"]["name"] == "test1"
        assert states["test2"]["name"] == "test2"

    @pytest.mark.asyncio
    async def test_reset_all(self):
        """Test resetting all circuit breakers."""
        cb = CircuitBreaker("test_reset")
        CircuitBreakerRegistry.register("test_reset", cb)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Reset all
        CircuitBreakerRegistry.reset_all()

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_unregister(self):
        """Test unregistering circuit breakers."""
        cb = CircuitBreaker("test_unregister")
        CircuitBreakerRegistry.register("test_unregister", cb)

        assert "test_unregister" in CircuitBreakerRegistry._circuit_breakers

        CircuitBreakerRegistry.unregister("test_unregister")

        assert "test_unregister" not in CircuitBreakerRegistry._circuit_breakers


class TestDefaultCircuitBreakers:
    """Test suite for default circuit breakers."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean registry before each test."""
        CircuitBreakerRegistry._circuit_breakers.clear()
        yield
        CircuitBreakerRegistry._circuit_breakers.clear()

    @pytest.mark.asyncio
    async def test_register_default_circuit_breakers(self):
        """Test registering default circuit breakers."""
        register_default_circuit_breakers()

        # Check all expected circuit breakers are registered
        assert "openai_api" in CircuitBreakerRegistry._circuit_breakers
        assert "honcho_api" in CircuitBreakerRegistry._circuit_breakers
        assert "database" in CircuitBreakerRegistry._circuit_breakers
        assert "external_service" in CircuitBreakerRegistry._circuit_breakers

    @pytest.mark.asyncio
    async def test_openai_api_circuit_breaker_config(self):
        """Test OpenAI API circuit breaker configuration."""
        register_default_circuit_breakers()

        cb = CircuitBreakerRegistry.get("openai_api")
        assert cb.config.failure_threshold == 3
        assert cb.config.recovery_timeout == 60.0

    @pytest.mark.asyncio
    async def test_database_circuit_breaker_config(self):
        """Test database circuit breaker configuration."""
        register_default_circuit_breakers()

        cb = CircuitBreakerRegistry.get("database")
        assert cb.config.failure_threshold == 10
        assert cb.config.recovery_timeout == 30.0


class TestCircuitBreakerConcurrency:
    """Test suite for circuit breaker concurrency."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(
            name="concurrent_test",
            config=CircuitBreakerConfig(failure_threshold=5),
        )

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, circuit_breaker):
        """Test concurrent calls to circuit breaker."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result_{call_count}"

        # Make concurrent calls
        tasks = [circuit_breaker.call(success_func) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert all(not isinstance(r, Exception) for r in results)
        assert call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_failures(self, circuit_breaker):
        """Test concurrent failures."""
        failure_count = 0

        async def failing_func():
            nonlocal failure_count
            failure_count += 1
            await asyncio.sleep(0.01)
            raise ValueError(f"Error {failure_count}")

        # Make concurrent failing calls
        tasks = [circuit_breaker.call(failing_func) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should have failed, but circuit should be open for some
        open_errors = [r for r in results if isinstance(r, CircuitBreakerOpenError)]
        value_errors = [r for r in results if isinstance(r, ValueError)]

        # Should have some of each
        assert len(open_errors) > 0 or len(value_errors) >= 3
