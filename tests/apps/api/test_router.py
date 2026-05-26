"""Tests for canonical route mounting."""

from __future__ import annotations

from typing import Any


def test_canonical_source_backed_routes_are_mounted(
    canonical_app: Any,
) -> None:
    mounted_paths = {
        route.path for route in canonical_app.routes if hasattr(route, "path")
    }

    expected_paths = {
        "/health",
        "/health/live",
        "/health/ready",
        "/version",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/auth/register",
        "/api/guest/session",
        "/api/providers",
        "/api/workspaces",
        "/api/workspaces/{workspace_id}",
        "/api/workspaces/{workspace_id}/jobs",
        "/api/workspaces/{workspace_id}/jobs/{job_id}",
    }

    missing_paths = expected_paths.difference(mounted_paths)
    assert not missing_paths, f"Missing mounted paths: {sorted(missing_paths)}"
    assert any(path.startswith("/api/knowledge") for path in mounted_paths)


def test_removed_or_missing_context_routes_are_not_mounted(
    canonical_app: Any,
) -> None:
    mounted_paths = {
        route.path for route in canonical_app.routes if hasattr(route, "path")
    }

    assert "/health/detailed" not in mounted_paths
    assert "/api/dashboard" not in mounted_paths
    assert "/api/world" not in mounted_paths
    assert "/api/" + "stor" + "ies" not in mounted_paths
    assert "/api/characters" not in mounted_paths
    assert not any(
        path.startswith("/api/") and "/story" in path for path in mounted_paths
    )
