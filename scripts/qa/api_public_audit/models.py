"""Data models used by the public API audit workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

AssertionFn = Callable[[Any], tuple[bool, str | None]]


@dataclass(frozen=True, order=True)
class RouteKey:
    method: str
    path: str


@dataclass
class CheckResult:
    id: str
    category: str
    name: str
    method: str
    route_template: str
    request_path: str
    expected_statuses: list[int]
    status_code: int | None
    passed: bool
    duration_ms: float
    assertion_message: str | None
    response_excerpt: str | None
    error: str | None


@dataclass
class AuditContext:
    suffix: int
    workspace_id: str = ""
    guest_workspace_id: str = ""
    story_id: str = ""
    run_id: str = ""
    knowledge_base_id: str = ""
    document_id: str = ""
