"""Honcho health-check status contracts."""

from __future__ import annotations

from typing import Any, cast

import pytest

from src.shared.infrastructure.health.checks.honcho_health_check import (
    HonchoHealthCheck,
)
from src.shared.infrastructure.health.health_checker import HealthStatus


@pytest.mark.asyncio
async def test_honcho_health_check_reports_not_configured() -> None:
    status = await HonchoHealthCheck().check()

    assert status.status == "unknown"
    assert status.message == "Honcho client not configured"


@pytest.mark.asyncio
async def test_honcho_health_check_reports_healthy() -> None:
    class _Client:
        async def health_check(self) -> bool:
            return True

    status = await HonchoHealthCheck(cast(Any, _Client())).check()

    assert status.status == "healthy"
    assert status.message == "Honcho service connection successful"


@pytest.mark.asyncio
async def test_honcho_health_check_reports_unhealthy() -> None:
    class _Client:
        async def health_check(self) -> bool:
            return False

    status = await HonchoHealthCheck(cast(Any, _Client())).check()

    assert status.status == "unhealthy"
    assert status.message == "Honcho service health check failed"


@pytest.mark.asyncio
async def test_honcho_health_check_preserves_degraded_result() -> None:
    class _Client:
        async def health_check(self) -> HealthStatus:
            return HealthStatus(status="degraded", message="Honcho latency is high")

    status = await HonchoHealthCheck(cast(Any, _Client())).check()

    assert status.status == "degraded"
    assert status.message == "Honcho latency is high"


@pytest.mark.asyncio
async def test_honcho_health_check_supports_string_status() -> None:
    class _Client:
        def health_check(self) -> str:
            return "degraded"

    status = await HonchoHealthCheck(cast(Any, _Client())).check()

    assert status.status == "degraded"
    assert status.message == "Honcho service reported degraded"


@pytest.mark.asyncio
async def test_honcho_health_check_falls_back_to_get_client() -> None:
    class _Client:
        async def _get_client(self) -> object:
            return object()

    status = await HonchoHealthCheck(cast(Any, _Client())).check()

    assert status.status == "healthy"
    assert status.message == "Honcho client initialized successfully"


@pytest.mark.asyncio
async def test_honcho_health_check_reports_missing_probe() -> None:
    status = await HonchoHealthCheck(cast(Any, object())).check()

    assert status.status == "unknown"
    assert status.message == "Honcho client does not expose a health probe"


@pytest.mark.asyncio
async def test_honcho_health_check_reports_exception_details() -> None:
    class _Client:
        async def health_check(self) -> bool:
            raise TimeoutError("probe timed out")

    status = await HonchoHealthCheck(cast(Any, _Client())).check()

    assert status.status == "unhealthy"
    assert status.error == "probe timed out"
    assert status.details == {"error_type": "TimeoutError"}
