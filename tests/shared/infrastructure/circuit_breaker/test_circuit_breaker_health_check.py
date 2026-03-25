"""Tests for circuit breaker health check."""

from __future__ import annotations

import pytest

from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)
from src.shared.infrastructure.health.checks.circuit_breaker_health_check import (
    CircuitBreakerHealthCheck,
)


class TestCircuitBreakerHealthCheck:
    """Test suite for circuit breaker health check."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean registry before each test."""
        CircuitBreakerRegistry._circuit_breakers.clear()
        yield
        CircuitBreakerRegistry._circuit_breakers.clear()

    @pytest.fixture
    def health_check(self):
        """Create health check instance."""
        return CircuitBreakerHealthCheck()

    @pytest.mark.asyncio
    async def test_no_circuits_registered(self, health_check):
        """Test health check with no registered circuits."""
        result = await health_check.check()

        assert result["status"] == "healthy"
        assert "No circuit breakers registered" in result["message"]
        assert result["circuits"] == {}

    @pytest.mark.asyncio
    async def test_all_circuits_closed(self, health_check):
        """Test health check when all circuits are closed."""
        cb1 = CircuitBreaker("test1")
        cb2 = CircuitBreaker("test2")
        CircuitBreakerRegistry.register("test1", cb1)
        CircuitBreakerRegistry.register("test2", cb2)

        result = await health_check.check()

        assert result["status"] == "healthy"
        assert "All circuits closed" in result["message"]
        assert "test1" in result["circuits"]
        assert "test2" in result["circuits"]

    @pytest.mark.asyncio
    async def test_open_circuits_detected(self, health_check):
        """Test health check detects open circuits."""
        cb = CircuitBreaker("test_open")
        CircuitBreakerRegistry.register("test_open", cb)

        # Open the circuit
        async def failing_func():
            raise ValueError("Test error")

        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        result = await health_check.check()

        assert result["status"] == "degraded"
        assert "test_open" in result["open_circuits"]
        assert result["open_circuits"] == ["test_open"]

    @pytest.mark.asyncio
    async def test_multiple_open_circuits(self, health_check):
        """Test health check with multiple open circuits."""
        cb1 = CircuitBreaker("open1", config=CircuitBreakerConfig(failure_threshold=3))
        cb2 = CircuitBreaker("open2", config=CircuitBreakerConfig(failure_threshold=3))
        CircuitBreakerRegistry.register("open1", cb1)
        CircuitBreakerRegistry.register("open2", cb2)

        # Open both circuits
        async def failing_func():
            raise ValueError("Test error")

        # Open first circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb1.call(failing_func)

        # Open second circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb2.call(failing_func)

        result = await health_check.check()

        assert result["status"] == "degraded"
        assert len(result["open_circuits"]) == 2
        assert "open1" in result["open_circuits"]
        assert "open2" in result["open_circuits"]

    @pytest.mark.asyncio
    async def test_half_open_circuits_reported(self, health_check):
        """Test health check reports half-open circuits."""
        cb = CircuitBreaker("half_open_test")
        cb._state = CircuitState.HALF_OPEN
        CircuitBreakerRegistry.register("half_open_test", cb)

        result = await health_check.check()

        # Should still be healthy but mention half-open
        assert result["status"] == "healthy"
        assert "half_open_circuits" in result
        assert "half_open_test" in result["half_open_circuits"]

    @pytest.mark.asyncio
    async def test_circuit_states_in_details(self, health_check):
        """Test that circuit states are included in details."""
        cb = CircuitBreaker("details_test")
        CircuitBreakerRegistry.register("details_test", cb)

        result = await health_check.check()

        assert "circuits" in result
        assert "details_test" in result["circuits"]
        circuit_details = result["circuits"]["details_test"]
        assert "name" in circuit_details
        assert "state" in circuit_details
        assert "failure_count" in circuit_details

    @pytest.mark.asyncio
    async def test_mixed_states(self, health_check):
        """Test health check with mixed circuit states."""
        closed_cb = CircuitBreaker("closed_circuit")
        open_cb = CircuitBreaker("open_circuit")

        CircuitBreakerRegistry.register("closed_circuit", closed_cb)
        CircuitBreakerRegistry.register("open_circuit", open_cb)

        # Open one circuit
        async def failing_func():
            raise ValueError("Test error")

        for _ in range(5):
            with pytest.raises(ValueError):
                await open_cb.call(failing_func)

        result = await health_check.check()

        assert result["status"] == "degraded"
        assert "open_circuit" in result["open_circuits"]
        assert "closed_circuit" not in result.get("open_circuits", [])

    @pytest.mark.asyncio
    async def test_error_handling(self, health_check, monkeypatch):
        """Test error handling in health check."""

        # Simulate an error in get_all_states
        def mock_get_all_states():
            raise RuntimeError("Test error")

        monkeypatch.setattr(
            CircuitBreakerRegistry, "get_all_states", mock_get_all_states
        )

        result = await health_check.check()

        assert result["status"] == "unhealthy"
        assert "failed" in result["message"]
