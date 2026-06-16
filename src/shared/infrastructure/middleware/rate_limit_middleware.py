"""Rate limiting middleware for authentication endpoints.

Limits request frequency for the unauthenticated setup and session endpoints.
The client is identified by ``request.client.host`` by default. When the
immediate remote peer is a configured trusted proxy, the first entry of
``X-Forwarded-For`` is used instead.
"""

from __future__ import annotations

import ipaddress
import math
import time
from typing import Awaitable, Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from src.shared.infrastructure.config.settings import SecuritySettings, get_settings
from src.shared.infrastructure.rate_limit import (
    TokenBucketRateLimiter,
    parse_rate_limit,
)

_PROTECTED_PATHS = frozenset({"/api/setup", "/api/session/login", "/api/session/guest"})


def _is_trusted_proxy(host: str, trusted_proxies: list[str]) -> bool:
    """Check whether ``host`` matches any configured trusted proxy.

    Supports IPv4/IPv6 addresses, CIDR networks, and exact host strings
    (useful for local sockets or test clients).
    """
    try:
        client_addr = ipaddress.ip_address(host)
    except ValueError:
        return host in trusted_proxies
    for proxy in trusted_proxies:
        try:
            if "/" in proxy:
                network = ipaddress.ip_network(proxy, strict=False)
                if client_addr in network:
                    return True
            elif client_addr == ipaddress.ip_address(proxy):
                return True
        except ValueError:
            if host == proxy:
                return True
            continue
    return False


def _client_id(request: Request, trusted_proxies: list[str]) -> str:
    """Determine a rate-limit key for the request origin."""
    client_host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and _is_trusted_proxy(client_host, trusted_proxies):
        return forwarded.split(",")[0].strip()
    return client_host


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that rate-limits sensitive unauthenticated endpoints."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: SecuritySettings | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Configure the middleware.

        Args:
            app: The ASGI application to wrap.
            settings: Optional security settings. Defaults to the global settings.
            clock: Optional time source for testing.
        """
        super().__init__(app)
        security = settings or get_settings().security
        rate_limit = parse_rate_limit(security.rate_limit)
        self._window_seconds = rate_limit.window_seconds
        self._trusted_proxies = security.trusted_proxies
        self._limiter = TokenBucketRateLimiter(
            rate=rate_limit.limit / rate_limit.window_seconds,
            capacity=security.rate_limit_burst,
            key_ttl_seconds=rate_limit.window_seconds,
            clock=clock or time.monotonic,
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Apply rate limiting to protected paths."""
        if request.method == "OPTIONS" or request.url.path not in _PROTECTED_PATHS:
            return await call_next(request)

        key = f"{_client_id(request, self._trusted_proxies)}:{request.method}:{request.url.path}"
        if await self._limiter.is_allowed(key):
            return await call_next(request)

        retry_after = math.ceil(self._limiter.retry_after(key))
        return JSONResponse(
            {"detail": "Rate limit exceeded."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(int(retry_after))},
        )
