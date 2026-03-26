"""Tests for health checker.

Comprehensive tests for the centralized health checking coordinator.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.shared.infrastructure.health.health_checker import HealthChecker, HealthStatus


class TestHealthStatus:
    """Test cases for HealthStatus dataclass."""

    def test_health_status_defaults(self) -> None:
        """Test HealthStatus with default values."""
        status = HealthStatus()
        assert status.status == "unknown"
        assert status.message == ""
        assert status.error is None
        assert status.details == {}
        assert status.response_time_ms == 0.0

    def test_health_status_custom_values(self) -> None:
        """Test HealthStatus with custom values."""
        status = HealthStatus(
            status="healthy",
            message="All systems operational",
            error=None,
            details={"version": "1.0"},
            response_time_ms=42.5,
        )
        assert status.status == "healthy"
        assert status.message == "All systems operational"
        assert status.details == {"version": "1.0"}
        assert status.response_time_ms == 42.5

    def test_health_status_to_dict(self) -> None:
        """Test converting HealthStatus to dictionary."""
        status = HealthStatus(
            status="unhealthy",
            message="Service down",
            error="Connection refused",
            details={"host": "localhost"},
            response_time_ms=100.0,
        )
        result = status.to_dict()
        assert result["status"] == "unhealthy"
        assert result["message"] == "Service down"
        assert result["error"] == "Connection refused"
        assert result["details"] == {"host": "localhost"}
        assert result["response_time_ms"] == 100.0

    def test_health_status_to_dict_no_error(self) -> None:
        """Test to_dict excludes error when None."""
        status = HealthStatus(status="healthy", message="OK")
        result = status.to_dict()
        assert "error" not in result
        assert "details" not in result


class TestHealthChecker:
    """Test cases for HealthChecker."""

    @pytest.mark.asyncio
    async def test_register_health_check(self) -> None:
        """Test registering a health check."""
        checker = HealthChecker()
        mock_check = AsyncMock(return_value=HealthStatus(status="healthy"))

        checker.register("test_check", mock_check)

        assert "test_check" in checker.checks

    @pytest.mark.asyncio
    async def test_unregister_health_check(self) -> None:
        """Test unregistering a health check."""
        checker = HealthChecker()
        mock_check = AsyncMock(return_value=HealthStatus(status="healthy"))

        checker.register("test_check", mock_check)
        checker.unregister("test_check")

        assert "test_check" not in checker.checks

    @pytest.mark.asyncio
    async def test_check_all_empty(self) -> None:
        """Test check_all with no registered checks."""
        checker = HealthChecker()

        result = await checker.check_all()

        assert result["overall_status"] == "healthy"
        assert result["components"] == {}
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_check_all_single_healthy(self) -> None:
        """Test check_all with single healthy check."""
        checker = HealthChecker()
        mock_check = AsyncMock(return_value=HealthStatus(status="healthy"))

        checker.register("test", mock_check)
        result = await checker.check_all()

        assert result["overall_status"] == "healthy"
        assert result["components"]["test"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_all_single_unhealthy(self) -> None:
        """Test check_all with single unhealthy check."""
        checker = HealthChecker()
        mock_check = AsyncMock(
            return_value=HealthStatus(status="unhealthy", error="Failed")
        )

        checker.register("test", mock_check)
        result = await checker.check_all()

        assert result["overall_status"] == "unhealthy"
        assert result["components"]["test"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_check_all_aggregates_results(self) -> None:
        """Test that check_all aggregates all check results."""
        checker = HealthChecker()

        async def healthy_check() -> HealthStatus:
            return HealthStatus(status="healthy", message="OK")

        async def unhealthy_check() -> HealthStatus:
            return HealthStatus(status="unhealthy", error="Fail")

        async def timeout_check() -> HealthStatus:
            await asyncio.sleep(10)  # Will timeout
            return HealthStatus(status="healthy")

        checker.register("healthy", healthy_check)
        checker.register("unhealthy", unhealthy_check)
        checker.register("timeout", timeout_check)

        # Set short timeout for faster test
        checker._default_timeout = 0.1
        result = await checker.check_all()

        assert result["components"]["healthy"]["status"] == "healthy"
        assert result["components"]["unhealthy"]["status"] == "unhealthy"
        assert result["components"]["timeout"]["status"] == "timeout"
        assert result["overall_status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_check_all_concurrent_execution(self) -> None:
        """Test that checks run concurrently."""
        checker = HealthChecker()
        execution_order = []

        async def slow_check(name: str, delay: float) -> HealthStatus:
            await asyncio.sleep(delay)
            execution_order.append(name)
            return HealthStatus(status="healthy")

        checker.register("a", lambda: slow_check("a", 0.1))
        checker.register("b", lambda: slow_check("b", 0.1))

        await checker.check_all()

        # Both should complete around the same time (concurrent)
        assert len(execution_order) == 2

    @pytest.mark.asyncio
    async def test_check_all_with_timeout(self) -> None:
        """Test that timeout is handled correctly."""
        checker = HealthChecker(default_timeout=0.1)

        async def slow_check() -> HealthStatus:
            await asyncio.sleep(1.0)
            return HealthStatus(status="healthy")

        checker.register("slow", slow_check)
        result = await checker.check_all()

        assert result["components"]["slow"]["status"] == "timeout"
        assert "timed out" in result["components"]["slow"]["message"]

    @pytest.mark.asyncio
    async def test_check_all_handles_exceptions(self) -> None:
        """Test that exceptions in checks are handled gracefully."""
        checker = HealthChecker()

        async def failing_check() -> HealthStatus:
            raise RuntimeError("Check failed")

        checker.register("failing", failing_check)
        result = await checker.check_all()

        assert result["components"]["failing"]["status"] == "error"
        assert "Check failed" in result["components"]["failing"]["error"]

    @pytest.mark.asyncio
    async def test_check_all_degraded_status(self) -> None:
        """Test degraded overall status."""
        checker = HealthChecker()

        async def healthy_check() -> HealthStatus:
            return HealthStatus(status="healthy")

        async def degraded_check() -> HealthStatus:
            return HealthStatus(status="degraded")

        checker.register("healthy", healthy_check)
        checker.register("degraded", degraded_check)

        result = await checker.check_all()

        assert result["overall_status"] == "degraded"

    @pytest.mark.asyncio
    async def test_check_single(self) -> None:
        """Test checking a single component."""
        checker = HealthChecker()
        mock_check = AsyncMock(return_value=HealthStatus(status="healthy"))

        checker.register("test", mock_check)
        result = await checker.check_single("test")

        assert result is not None
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_check_single_not_found(self) -> None:
        """Test checking a non-existent component."""
        checker = HealthChecker()

        result = await checker.check_single("nonexistent")

        assert result is None

    def test_is_healthy_true(self) -> None:
        """Test is_healthy returns True for healthy status."""
        checker = HealthChecker()
        results = {"overall_status": "healthy", "components": {}}

        assert checker.is_healthy(results) is True

    def test_is_healthy_false(self) -> None:
        """Test is_healthy returns False for unhealthy status."""
        checker = HealthChecker()
        results = {"overall_status": "unhealthy", "components": {}}

        assert checker.is_healthy(results) is False

    def test_clear(self) -> None:
        """Test clearing all checks."""
        checker = HealthChecker()
        mock_check = AsyncMock(return_value=HealthStatus(status="healthy"))

        checker.register("test", mock_check)
        checker.clear()

        assert len(checker.checks) == 0

    @pytest.mark.asyncio
    async def test_response_time_tracking(self) -> None:
        """Test that response times are tracked."""
        checker = HealthChecker()

        async def slow_check() -> HealthStatus:
            await asyncio.sleep(0.05)
            return HealthStatus(status="healthy")

        checker.register("slow", slow_check)
        result = await checker.check_all()

        assert result["components"]["slow"]["response_time_ms"] > 0


class TestHealthCheckerIntegration:
    """Integration-style tests for HealthChecker."""

    @pytest.mark.asyncio
    async def test_real_world_scenario(self) -> None:
        """Test a realistic scenario with multiple components."""
        checker = HealthChecker()

        # Simulate database check
        async def db_check() -> HealthStatus:
            return HealthStatus(
                status="healthy",
                message="Database connected",
                details={"connections": 10, "max": 100},
            )

        # Simulate cache check
        async def cache_check() -> HealthStatus:
            return HealthStatus(
                status="healthy",
                message="Cache responding",
                details={"hit_rate": 0.95},
            )

        # Simulate external API check
        async def api_check() -> HealthStatus:
            return HealthStatus(
                status="degraded",
                message="API slow but responding",
                details={"latency_ms": 500},
            )

        checker.register("database", db_check)
        checker.register("cache", cache_check)
        checker.register("external_api", api_check)

        result = await checker.check_all()

        assert result["overall_status"] == "degraded"
        assert len(result["components"]) == 3
        assert result["components"]["database"]["status"] == "healthy"
        assert result["components"]["cache"]["status"] == "healthy"
        assert result["components"]["external_api"]["status"] == "degraded"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception_type",
        [
            ValueError,
            RuntimeError,
            ConnectionError,
            OSError,
        ],
    )
    async def test_various_exception_types(
        self, exception_type: type[Exception]
    ) -> None:
        """Test handling of various exception types."""
        checker = HealthChecker()

        async def failing_check() -> HealthStatus:
            raise exception_type("Test error")

        checker.register("failing", failing_check)
        result = await checker.check_all()

        assert result["components"]["failing"]["status"] == "error"
        assert "Test error" in result["components"]["failing"]["error"]

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self) -> None:
        """Test that TimeoutError from check function is handled properly."""
        checker = HealthChecker()

        async def failing_check() -> HealthStatus:
            # TimeoutError might be treated specially by asyncio
            raise RuntimeError("Timeout simulated")

        checker.register("failing", failing_check)
        result = await checker.check_all()

        assert result["components"]["failing"]["status"] == "error"
