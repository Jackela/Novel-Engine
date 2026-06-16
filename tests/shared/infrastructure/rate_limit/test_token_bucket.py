from __future__ import annotations

import asyncio

import pytest

from src.shared.infrastructure.rate_limit import (
    RateLimit,
    TokenBucketRateLimiter,
    parse_rate_limit,
)


@pytest.mark.parametrize(
    "value,expected_limit,expected_window",
    [
        ("5/minute", 5, 60.0),
        ("10/second", 10, 1.0),
        ("2/h", 2, 3600.0),
        ("1/day", 1, 86400.0),
        ("5 / min", 5, 60.0),
        ("3 / seconds", 3, 1.0),
    ],
)
def test_parse_rate_limit_accepts_valid_formats(
    value: str,
    expected_limit: int,
    expected_window: float,
) -> None:
    result = parse_rate_limit(value)
    assert result == RateLimit(limit=expected_limit, window_seconds=expected_window)


@pytest.mark.parametrize(
    "value",
    ["", "abc", "5", "5/fortnight", "-1/minute", "0/minute"],
)
def test_parse_rate_limit_rejects_invalid_formats(value: str) -> None:
    with pytest.raises(ValueError):
        parse_rate_limit(value)


async def test_token_bucket_allows_burst_then_blocks() -> None:
    now = [0.0]
    limiter = TokenBucketRateLimiter(
        rate=1.0,
        capacity=2,
        clock=lambda: now[0],
    )

    assert await limiter.is_allowed("k") is True
    assert await limiter.is_allowed("k") is True
    assert await limiter.is_allowed("k") is False

    now[0] += 1
    assert await limiter.is_allowed("k") is True
    assert await limiter.is_allowed("k") is False


async def test_token_bucket_tracks_keys_independently() -> None:
    now = [0.0]
    limiter = TokenBucketRateLimiter(
        rate=1.0,
        capacity=1,
        clock=lambda: now[0],
    )

    assert await limiter.is_allowed("a") is True
    assert await limiter.is_allowed("b") is True
    assert await limiter.is_allowed("a") is False


async def test_token_bucket_reports_retry_after() -> None:
    now = [0.0]
    limiter = TokenBucketRateLimiter(
        rate=0.5,
        capacity=1,
        clock=lambda: now[0],
    )

    assert await limiter.is_allowed("k") is True
    assert limiter.retry_after("k") == pytest.approx(2.0)

    now[0] += 1
    assert limiter.retry_after("k") == pytest.approx(1.0)

    now[0] += 1
    assert limiter.retry_after("k") == 0.0


async def test_token_bucket_cleans_up_expired_keys() -> None:
    now = [0.0]
    limiter = TokenBucketRateLimiter(
        rate=1.0,
        capacity=1,
        key_ttl_seconds=10.0,
        clock=lambda: now[0],
    )

    assert await limiter.is_allowed("a") is True
    assert await limiter.is_allowed("b") is True
    assert "a" in limiter._tokens
    assert "b" in limiter._tokens

    now[0] += 11
    await limiter.cleanup_expired()
    assert "a" not in limiter._tokens
    assert "b" not in limiter._tokens
    assert "a" not in limiter._last_update
    assert "b" not in limiter._last_update


async def test_token_bucket_keeps_active_keys_during_cleanup() -> None:
    now = [0.0]
    limiter = TokenBucketRateLimiter(
        rate=1.0,
        capacity=1,
        key_ttl_seconds=10.0,
        clock=lambda: now[0],
    )

    assert await limiter.is_allowed("a") is True
    now[0] += 11
    assert await limiter.is_allowed("b") is True
    await limiter.cleanup_expired()
    assert "a" not in limiter._tokens
    assert "b" in limiter._tokens


async def test_token_bucket_uses_per_key_locks() -> None:
    now = [0.0]
    limiter = TokenBucketRateLimiter(
        rate=1.0,
        capacity=2,
        clock=lambda: now[0],
    )

    results = await asyncio.gather(
        limiter.is_allowed("a"),
        limiter.is_allowed("a"),
        limiter.is_allowed("b"),
        limiter.is_allowed("b"),
    )
    assert results == [True, True, True, True]
