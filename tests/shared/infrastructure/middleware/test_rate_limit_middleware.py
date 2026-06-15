from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.infrastructure.config.settings import SecuritySettings
from src.shared.infrastructure.middleware.rate_limit_middleware import (
    RateLimitMiddleware,
)


def _make_app(
    *,
    rate_limit: str,
    burst: int,
    now: list[float],
    trusted_proxies: list[str] | None = None,
) -> FastAPI:
    app = FastAPI()
    settings = SecuritySettings(
        rate_limit=rate_limit,
        rate_limit_burst=burst,
        trusted_proxies=trusted_proxies or [],
    )
    app.add_middleware(
        RateLimitMiddleware,
        settings=settings,
        clock=lambda: now[0],
    )

    @app.post("/api/session/guest")
    async def guest() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/setup")
    async def setup() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/projects")
    async def projects() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_rate_limit_allows_requests_within_burst() -> None:
    now = [0.0]
    client = TestClient(_make_app(rate_limit="5/minute", burst=3, now=now))

    for _ in range(3):
        response = client.post("/api/session/guest")
        assert response.status_code == 200


def test_rate_limit_blocks_excess_requests() -> None:
    now = [0.0]
    client = TestClient(_make_app(rate_limit="5/minute", burst=3, now=now))

    for _ in range(3):
        client.post("/api/session/guest")

    response = client.post("/api/session/guest")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded."
    # 5 tokens per 60s -> 12s to refill one token
    assert response.headers["Retry-After"] == "12"


def test_rate_limit_refills_over_time() -> None:
    now = [0.0]
    client = TestClient(_make_app(rate_limit="5/minute", burst=3, now=now))

    for _ in range(3):
        client.post("/api/session/guest")
    assert client.post("/api/session/guest").status_code == 429

    now[0] += 60
    assert client.post("/api/session/guest").status_code == 200


def test_rate_limit_tracks_endpoints_independently() -> None:
    now = [0.0]
    client = TestClient(_make_app(rate_limit="5/minute", burst=1, now=now))

    assert client.post("/api/setup").status_code == 200
    assert client.post("/api/session/guest").status_code == 200


def test_rate_limit_uses_x_forwarded_for_from_trusted_proxy() -> None:
    now = [0.0]
    client = TestClient(
        _make_app(
            rate_limit="5/minute",
            burst=1,
            now=now,
            trusted_proxies=["testclient"],
        )
    )

    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "1.2.3.4"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "1.2.3.4"},
        ).status_code
        == 429
    )
    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "5.6.7.8"},
        ).status_code
        == 200
    )


def test_rate_limit_ignores_x_forwarded_for_without_trusted_proxies() -> None:
    now = [0.0]
    client = TestClient(_make_app(rate_limit="5/minute", burst=1, now=now))

    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "1.2.3.4, 9.9.9.9"},
        ).status_code
        == 200
    )
    # Same direct client should still be blocked even with a forged header.
    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "5.6.7.8"},
        ).status_code
        == 429
    )


def test_rate_limit_trusted_proxy_checks_client_host() -> None:
    now = [0.0]
    client = TestClient(
        _make_app(
            rate_limit="5/minute",
            burst=1,
            now=now,
            trusted_proxies=["127.0.0.1"],
        )
    )

    # testclient is not 127.0.0.1, so X-Forwarded-For must be ignored.
    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "1.2.3.4"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/session/guest",
            headers={"X-Forwarded-For": "5.6.7.8"},
        ).status_code
        == 429
    )


def test_rate_limit_skips_unprotected_paths() -> None:
    now = [0.0]
    client = TestClient(_make_app(rate_limit="5/minute", burst=1, now=now))

    for _ in range(5):
        assert client.get("/api/projects").status_code == 200
