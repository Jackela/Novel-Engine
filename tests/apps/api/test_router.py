"""Tests for canonical route mounting."""

from __future__ import annotations


def test_canonical_source_backed_routes_are_mounted(canonical_app) -> None:
    mounted_paths = {
        route.path for route in canonical_app.routes if hasattr(route, "path")
    }

    expected_paths = {
        "/health",
        "/health/live",
        "/health/ready",
        "/version",
        "/api/versions",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/auth/register",
        "/api/v1/guest/session",
        "/api/v1/dashboard/status",
        "/api/v1/dashboard/orchestration",
        "/api/v1/dashboard/orchestration/start",
        "/api/v1/dashboard/orchestration/pause",
        "/api/v1/dashboard/orchestration/stop",
        "/api/v1/dashboard/events/stream",
        "/api/v1/world/rumors/propagate",
        "/api/v1/world/rumors/{world_id}",
    }

    missing_paths = expected_paths.difference(mounted_paths)
    assert not missing_paths, f"Missing mounted paths: {sorted(missing_paths)}"
    assert any(path.startswith("/api/v1/knowledge") for path in mounted_paths)


def test_legacy_or_missing_context_routes_are_not_mounted(canonical_app) -> None:
    mounted_paths = {
        route.path for route in canonical_app.routes if hasattr(route, "path")
    }

    assert "/health/detailed" not in mounted_paths
    assert "/api/v1/stories" not in mounted_paths
    assert "/api/v1/characters" not in mounted_paths
