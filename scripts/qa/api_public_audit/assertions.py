"""Reusable assertion helpers for API checks."""

from __future__ import annotations

from typing import Any

from .models import AssertionFn


def assert_json_keys(*keys: str) -> AssertionFn:
    def _assert(response: Any) -> tuple[bool, str | None]:
        try:
            payload = response.json()
        except Exception as exc:
            return False, f"Response is not valid JSON: {exc}"

        missing = [key for key in keys if key not in payload]
        if missing:
            return False, f"Missing keys: {missing}"
        return True, None

    return _assert


def assert_status_field(expected: str) -> AssertionFn:
    def _assert(response: Any) -> tuple[bool, str | None]:
        try:
            payload = response.json()
        except Exception as exc:
            return False, f"Response is not valid JSON: {exc}"

        actual = payload.get("status")
        if actual != expected:
            return False, f"Expected status '{expected}', got '{actual}'"
        return True, None

    return _assert


def assert_contains(fragment: str) -> AssertionFn:
    def _assert(response: Any) -> tuple[bool, str | None]:
        body = response.text
        if fragment not in body:
            return False, f"Response body does not contain '{fragment}'"
        return True, None

    return _assert


def assert_workspace_prefix(prefix: str) -> AssertionFn:
    def _assert(response: Any) -> tuple[bool, str | None]:
        try:
            payload = response.json()
        except Exception as exc:
            return False, f"Response is not valid JSON: {exc}"

        workspace_id = str(payload.get("workspace_id", ""))
        if not workspace_id.startswith(prefix):
            return False, f"workspace_id '{workspace_id}' does not start with '{prefix}'"
        return True, None

    return _assert
