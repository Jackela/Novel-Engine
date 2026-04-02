"""Live smoke for the optional self-hosted Honcho runtime."""

# mypy: disable-error-code=misc

from __future__ import annotations

import pytest

from src.shared.infrastructure.health.checks.honcho_health_check import (
    HonchoHealthCheck,
)
from src.shared.infrastructure.honcho import HonchoSettings, create_honcho_client

pytestmark = pytest.mark.requires_honcho


@pytest.mark.asyncio
async def test_self_hosted_honcho_live_smoke() -> None:
    settings = HonchoSettings()
    assert settings.is_self_hosted

    client = create_honcho_client(settings)
    health_status = await HonchoHealthCheck(client).check()

    assert health_status.status == "healthy"
    assert health_status.message
    assert await client.health_check() is True
