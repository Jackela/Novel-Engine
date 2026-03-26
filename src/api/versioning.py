"""Lightweight API versioning for the canonical backend."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


class APIVersion(str, Enum):
    """Supported API versions."""

    V1_0 = "1.0"


class VersionStatus(str, Enum):
    """Lifecycle status for the canonical API version."""

    CURRENT = "current"


@dataclass(slots=True)
class VersionInfo:
    """Static metadata about a supported API version."""

    version: APIVersion
    status: VersionStatus
    release_date: datetime
    description: str
    breaking_changes: list[str] = field(default_factory=list)
    migration_guide_url: str | None = None


class APIVersionRegistry:
    """Registry of supported API versions."""

    def __init__(self) -> None:
        self.versions = {
            APIVersion.V1_0: VersionInfo(
                version=APIVersion.V1_0,
                status=VersionStatus.CURRENT,
                release_date=datetime(2024, 1, 1, tzinfo=UTC),
                description="Canonical SSOT backend",
            ),
        }

    def get_current_version(self) -> APIVersion:
        """Return the canonical API version."""
        return APIVersion.V1_0

    def get_supported_versions(self) -> list[APIVersion]:
        """Return versions that can still be served."""
        return list(self.versions.keys())

    def is_supported(self, version: APIVersion) -> bool:
        """Return whether a version can still be served."""
        return version in self.versions


class VersionExtractor:
    """Extract an API version from request headers or URL."""

    def __init__(self, default_version: APIVersion = APIVersion.V1_0) -> None:
        self.default_version = default_version

    def extract_from_request(self, request: Request) -> APIVersion | None:
        """Resolve the requested version from the request.

        Returns ``None`` when the client explicitly asks for an unsupported
        version.
        """
        version_header = request.headers.get("X-API-Version")
        if version_header:
            try:
                return APIVersion(version_header)
            except ValueError:
                return None

        accept_header = request.headers.get("accept", "")
        if "application/vnd.novel-engine.v" in accept_header:
            candidate = accept_header.split("application/vnd.novel-engine.v", 1)[1]
            candidate = candidate.split("+", 1)[0]
            try:
                return APIVersion(candidate)
            except ValueError:
                return None

        path = request.url.path
        version_match = re.match(r"^/api/v(\d+(?:\.\d+)?)(?:/|$)", path)
        if version_match:
            raw_version = version_match.group(1)
            normalized_version = raw_version if "." in raw_version else f"{raw_version}.0"
            try:
                return APIVersion(normalized_version)
            except ValueError:
                return None

        return self.default_version


class VersionMiddleware:
    """Minimal middleware that annotates responses with API version metadata."""

    def __init__(self) -> None:
        self.registry = APIVersionRegistry()
        self.extractor = VersionExtractor(self.registry.get_current_version())

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and add version headers."""
        api_version = self.extractor.extract_from_request(request)
        if api_version is None or not self.registry.is_supported(api_version):
            return JSONResponse(
                status_code=400,
                content={"detail": "API version is not supported"},
            )

        request.state.api_version = api_version
        response = await call_next(request)
        response.headers["X-API-Version"] = api_version.value
        response.headers["X-Supported-Versions"] = ",".join(
            version.value for version in self.registry.get_supported_versions()
        )
        return response


def create_version_info_endpoint() -> Callable[[], dict[str, Any]]:
    """Create the `/api/versions` endpoint handler."""

    def get_api_versions() -> dict[str, Any]:
        registry = APIVersionRegistry()
        return {
            "current_version": registry.get_current_version().value,
            "supported_versions": [
                version.value for version in registry.get_supported_versions()
            ],
            "versions": {
                version.value: {
                    "status": info.status.value,
                    "release_date": info.release_date.isoformat(),
                    "description": info.description,
                    "breaking_changes": info.breaking_changes,
                    "migration_guide_url": info.migration_guide_url,
                }
                for version, info in registry.versions.items()
            },
        }

    return get_api_versions


def setup_versioning(app: FastAPI) -> VersionMiddleware:
    """Attach versioning middleware and the canonical version metadata endpoint."""
    middleware = VersionMiddleware()
    app.middleware("http")(middleware)
    app.add_api_route("/api/versions", create_version_info_endpoint(), methods=["GET"])
    return middleware


__all__ = [
    "APIVersion",
    "APIVersionRegistry",
    "VersionExtractor",
    "VersionInfo",
    "VersionMiddleware",
    "VersionStatus",
    "setup_versioning",
]
