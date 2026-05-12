"""Execution layer for public API checks."""

from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from .models import AssertionFn, CheckResult, RouteKey
from .runtime import truncate_text


class AuditRunner:
    def __init__(self, client: TestClient, discovered_routes: list[RouteKey]) -> None:
        self.client = client
        self.discovered_routes = discovered_routes
        self.covered_routes: set[RouteKey] = set()
        self.results: list[CheckResult] = []
        self._counter = 0

    def check(
        self,
        *,
        category: str,
        name: str,
        method: str,
        route_template: str,
        request_path: str,
        expected_statuses: list[int],
        assertion: AssertionFn | None = None,
        request_kwargs: dict[str, Any] | None = None,
    ) -> Any | None:
        self._counter += 1
        check_id = f"C{self._counter:03d}"
        started = time.perf_counter()
        status_code: int | None = None
        response_excerpt: str | None = None
        assertion_message: str | None = None
        error_message: str | None = None
        passed = False

        route_key = RouteKey(method=method, path=route_template)
        self.covered_routes.add(route_key)

        response: Any | None = None
        try:
            response = self.client.request(
                method,
                request_path,
                **(request_kwargs or {}),
            )
            status_code = response.status_code

            try:
                response_excerpt = truncate_text(response.text)
            except Exception:
                response_excerpt = None

            status_ok = status_code in expected_statuses
            assertion_ok = True
            if assertion is not None:
                assertion_ok, assertion_message = assertion(response)
            passed = status_ok and assertion_ok

            if not status_ok and assertion_message is None:
                assertion_message = (
                    f"Unexpected status {status_code}, expected one of {expected_statuses}"
                )
        except Exception as exc:  # pragma: no cover - hard failure path
            passed = False
            error_message = f"{type(exc).__name__}: {exc}"
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)

        self.results.append(
            CheckResult(
                id=check_id,
                category=category,
                name=name,
                method=method,
                route_template=route_template,
                request_path=request_path,
                expected_statuses=expected_statuses,
                status_code=status_code,
                passed=passed,
                duration_ms=duration_ms,
                assertion_message=assertion_message,
                response_excerpt=response_excerpt,
                error=error_message,
            )
        )
        return response
