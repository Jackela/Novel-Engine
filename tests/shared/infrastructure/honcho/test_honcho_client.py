"""Mock-based contracts for the optional Honcho client wrapper."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.shared.infrastructure.honcho import HonchoClient, HonchoSettings
from src.shared.infrastructure.honcho import client as client_module
from src.shared.infrastructure.honcho.errors import HonchoClientError


class _FakeHoncho:
    calls: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


@pytest.fixture(autouse=True)
def reset_fake_honcho() -> None:
    _FakeHoncho.calls.clear()


@pytest.mark.asyncio
async def test_client_lazy_initializes_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "_Honcho", _FakeHoncho)
    settings = HonchoSettings(
        api_key="honcho-key",
        base_url="http://honcho.local/",
        timeout=5,
    )

    client = HonchoClient(settings)
    assert _FakeHoncho.calls == []

    first = await client._get_client()
    second = await client._get_client()

    assert first is second
    assert _FakeHoncho.calls == [
        {
            "base_url": "http://honcho.local",
            "timeout": 5,
            "api_key": "honcho-key",
        }
    ]


@pytest.mark.asyncio
async def test_missing_honcho_package_maps_to_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "_Honcho", None)
    client = HonchoClient(HonchoSettings())

    with pytest.raises(HonchoClientError) as exc_info:
        await client._get_client()

    assert exc_info.value.error_code == "HONCHO_PACKAGE_MISSING"
    assert exc_info.value.details is not None
    assert exc_info.value.details.operation == "initialize"


@pytest.mark.asyncio
async def test_cloud_deployment_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "_Honcho", _FakeHoncho)
    client = HonchoClient(HonchoSettings(deployment="cloud", api_key=None))

    with pytest.raises(HonchoClientError, match="HONCHO_API_KEY") as exc_info:
        await client._get_client()

    assert exc_info.value.error_code == "CONFIGURATION_ERROR"
    assert _FakeHoncho.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("factory_error", "error_code"),
    [
        (ConnectionError("network down"), "CONNECTION_ERROR"),
        (TimeoutError("slow honcho"), "TIMEOUT_ERROR"),
        (RuntimeError("boom"), "UNKNOWN_ERROR"),
    ],
)
async def test_initialization_failures_map_to_client_error(
    monkeypatch: pytest.MonkeyPatch,
    factory_error: Exception,
    error_code: str,
) -> None:
    class _FailingHoncho:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs
            raise factory_error

    monkeypatch.setattr(client_module, "_Honcho", _FailingHoncho)
    client = HonchoClient(HonchoSettings())

    with pytest.raises(HonchoClientError) as exc_info:
        await client._get_client()

    assert exc_info.value.error_code == error_code
    assert exc_info.value.details is not None
    assert exc_info.value.details.original_exception is factory_error


def test_settings_normalize_deployment_and_workspace_ids() -> None:
    settings = HonchoSettings(
        deployment="managed",
        base_url="http://localhost:8000/",
        default_workspace_name="novel",
    )

    assert settings.is_cloud
    assert settings.base_url == "http://localhost:8000"
    assert settings.get_workspace_id() == "novel"
    assert settings.get_workspace_for_story("story-1") == "novel-story-1"
    assert settings.get_workspace_for_character("char-1", "story-1") == "novel-story-1"


def test_settings_character_strategy_uses_character_workspace() -> None:
    settings = HonchoSettings(
        default_workspace_name="novel",
        workspace_strategy="character",
    )

    assert settings.is_self_hosted
    assert settings.get_workspace_for_character("char-1", "story-1") == "novel-char-1"


def test_settings_reject_invalid_deployment() -> None:
    with pytest.raises(ValidationError):
        HonchoSettings(deployment="invalid")


@pytest.mark.asyncio
async def test_health_check_false_when_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "_Honcho", None)
    client = HonchoClient(HonchoSettings())

    assert await client.health_check() is False


@pytest.mark.asyncio
async def test_health_check_uses_boolean_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ProbeHoncho:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        async def health(self) -> bool:
            return True

    monkeypatch.setattr(client_module, "_Honcho", _ProbeHoncho)
    client = HonchoClient(HonchoSettings())

    assert await client.health_check() is True


@pytest.mark.asyncio
async def test_health_check_uses_response_ok_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        ok = False

    class _ProbeHoncho:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        def ping(self) -> _Response:
            return _Response()

    monkeypatch.setattr(client_module, "_Honcho", _ProbeHoncho)
    client = HonchoClient(HonchoSettings())

    assert await client.health_check() is False


@pytest.mark.asyncio
async def test_health_check_fails_when_all_available_probes_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingProbeHoncho:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        def health(self) -> bool:
            raise RuntimeError("health endpoint down")

        def status(self) -> bool:
            raise RuntimeError("status endpoint down")

    monkeypatch.setattr(client_module, "_Honcho", _FailingProbeHoncho)
    client = HonchoClient(HonchoSettings())

    assert await client.health_check() is False


@pytest.mark.asyncio
async def test_health_check_succeeds_without_probe_after_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "_Honcho", _FakeHoncho)
    client = HonchoClient(HonchoSettings())

    assert await client.health_check() is True
