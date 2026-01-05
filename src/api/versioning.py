#!/usr/bin/env python3
"""
API Versioning and Backward Compatibility System.

Provides comprehensive API versioning, backward compatibility handling,
and smooth migration paths for API consumers.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request, Response, status
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


class APIVersion(str, Enum):
    """Supported API versions."""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class VersionStatus(str, Enum):
    """API version lifecycle status."""

    CURRENT = "current"
    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


@dataclass
class VersionInfo:
    """API version information."""

    version: APIVersion
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    description: str = ""
    breaking_changes: List[str] = None
    migration_guide_url: Optional[str] = None

    def __post_init__(self):
        if self.breaking_changes is None:
            self.breaking_changes = []


class APIVersionRegistry:
    """Registry for managing API versions and their metadata."""

    def __init__(self):
        self.versions: Dict[APIVersion, VersionInfo] = {}
        self._initialize_versions()

    def _initialize_versions(self):
        """Initialize default version information."""

        # Version 1.0 - Initial API version
        self.versions[APIVersion.V1_0] = VersionInfo(
            version=APIVersion.V1_0,
            status=VersionStatus.CURRENT,
            release_date=datetime(2024, 1, 1),
            description="Initial Novel Engine API release",
            breaking_changes=[],
            migration_guide_url="/docs/migration/v1.0",
        )

        # Version 1.1 - Enhanced error handling and health checks
        self.versions[APIVersion.V1_1] = VersionInfo(
            version=APIVersion.V1_1,
            status=VersionStatus.CURRENT,
            release_date=datetime.now(),
            description="Enhanced error handling, standardized responses, and health monitoring",
            breaking_changes=[
                "Error response format standardized",
                "Health check endpoint response format changed",
                "Validation error format updated",
            ],
            migration_guide_url="/docs/migration/v1.1",
        )

        # Version 2.0 - Future major release (example)
        self.versions[APIVersion.V2_0] = VersionInfo(
            version=APIVersion.V2_0,
            status=VersionStatus.SUPPORTED,
            release_date=datetime(2024, 6, 1),
            description="Next generation API with improved performance and new features",
            breaking_changes=[
                "Authentication required for all endpoints",
                "Pagination required for list endpoints",
                "Resource IDs changed to UUIDs",
            ],
            migration_guide_url="/docs/migration/v2.0",
        )

    def get_version_info(self, version: APIVersion) -> Optional[VersionInfo]:
        """Get version information."""
        return self.versions.get(version)

    def get_current_version(self) -> APIVersion:
        """Get the current recommended API version."""
        current_versions = [
            v for v in self.versions.values() if v.status == VersionStatus.CURRENT
        ]
        if current_versions:
            # Return the latest current version
            return max(current_versions, key=lambda v: v.release_date).version
        return APIVersion.V1_0

    def is_version_supported(self, version: APIVersion) -> bool:
        """Check if a version is currently supported."""
        version_info = self.get_version_info(version)
        if not version_info:
            return False
        return version_info.status in [VersionStatus.CURRENT, VersionStatus.SUPPORTED]

    def get_supported_versions(self) -> List[APIVersion]:
        """Get all currently supported versions."""
        return [
            v.version
            for v in self.versions.values()
            if v.status in [VersionStatus.CURRENT, VersionStatus.SUPPORTED]
        ]

    def mark_deprecated(
        self, version: APIVersion, sunset_date: Optional[datetime] = None
    ):
        """Mark a version as deprecated."""
        if version in self.versions:
            self.versions[version].status = VersionStatus.DEPRECATED
            self.versions[version].deprecation_date = datetime.now()
            if sunset_date:
                self.versions[version].sunset_date = sunset_date


class VersionExtractor:
    """Extract API version from requests."""

    def __init__(self, default_version: APIVersion = APIVersion.V1_0):
        self.default_version = default_version

    def extract_from_request(self, request: Request) -> APIVersion:
        """Extract API version from request using multiple methods."""

        # Method 1: Accept header (preferred)
        accept_header = request.headers.get("accept", "")
        if "application/vnd.novel-engine.v" in accept_header:
            try:
                version_part = accept_header.split("application/vnd.novel-engine.v")[
                    1
                ].split("+")[0]
                return APIVersion(version_part)
            except (IndexError, ValueError):
                logger.debug("Invalid Accept header API version", exc_info=True)

        # Method 2: Custom header
        version_header = request.headers.get("X-API-Version")
        if version_header:
            try:
                return APIVersion(version_header)
            except ValueError:
                logger.debug("Invalid X-API-Version header", exc_info=True)

        # Method 3: Query parameter
        version_param = request.query_params.get("version")
        if version_param:
            try:
                return APIVersion(version_param)
            except ValueError:
                logger.debug("Invalid version query parameter", exc_info=True)

        # Method 4: URL path (if using path-based versioning)
        path = request.url.path
        if "/api/v" in path:
            try:
                version_part = path.split("/api/v")[1].split("/")[0]
                # Convert path version to enum (e.g., "1" -> "1.0")
                if "." not in version_part:
                    version_part += ".0"
                return APIVersion(version_part)
            except (IndexError, ValueError):
                logger.debug("Invalid path-based API version", exc_info=True)

        return self.default_version


class CompatibilityLayer:
    """Handle backward compatibility transformations."""

    def __init__(self):
        self.transformers: Dict[APIVersion, List[Callable]] = {
            APIVersion.V1_0: [self._transform_to_v1_0],
            APIVersion.V1_1: [self._transform_to_v1_1],
        }

    def transform_response(
        self, response_data: Dict[str, Any], target_version: APIVersion
    ) -> Dict[str, Any]:
        """Transform response to match target API version format."""

        if target_version not in self.transformers:
            return response_data

        transformed_data = response_data.copy()

        for transformer in self.transformers[target_version]:
            transformed_data = transformer(transformed_data)

        return transformed_data

    def _transform_to_v1_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response to v1.0 format (legacy)."""

        # Convert new error format back to simple format
        if "error" in data and isinstance(data["error"], dict):
            if "message" in data["error"]:
                data["detail"] = data["error"]["message"]
                data.pop("error", None)

        # Remove new metadata fields
        data.pop("metadata", None)
        data.pop("pagination", None)

        # Convert new status field
        if "status" in data:
            if data["status"] == "success":
                data.pop("status", None)  # v1.0 didn't have status field for success
            elif data["status"] == "error":
                data["error"] = True
                data.pop("status", None)

        return data

    def _transform_to_v1_1(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response to v1.1 format."""
        # v1.1 is the current standard format, no transformation needed
        return data


class VersionMiddleware:
    """Middleware to handle API versioning."""

    def __init__(self):
        self.registry = APIVersionRegistry()
        self.extractor = VersionExtractor()
        self.compatibility = CompatibilityLayer()

    async def __call__(self, request: Request, call_next):
        """Process request with version handling."""

        # Extract API version
        api_version = self.extractor.extract_from_request(request)

        # Check if version is supported
        if not self.registry.is_version_supported(api_version):
            return Response(
                content=f"API version {api_version.value} is not supported",
                status_code=status.HTTP_400_BAD_REQUEST,
                headers={"Content-Type": "application/json"},
            )

        # Store version in request state
        request.state.api_version = api_version

        # Get version info for deprecation warnings
        version_info = self.registry.get_version_info(api_version)

        # Process request
        response = await call_next(request)

        # Add version headers
        response.headers["X-API-Version"] = api_version.value
        response.headers["X-Supported-Versions"] = ",".join(
            v.value for v in self.registry.get_supported_versions()
        )

        # Add deprecation warning if needed
        if version_info and version_info.status == VersionStatus.DEPRECATED:
            response.headers["Deprecation"] = "true"
            if version_info.sunset_date:
                response.headers["Sunset"] = version_info.sunset_date.strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )
            if version_info.migration_guide_url:
                response.headers["Link"] = (
                    f'<{version_info.migration_guide_url}>; rel="migration-guide"'
                )

        return response


class VersionedRoute(APIRoute):
    """Custom route that supports version-specific handling."""

    def __init__(
        self,
        *args,
        version_handlers: Optional[Dict[APIVersion, Callable]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.version_handlers = version_handlers or {}

    async def handle_request(self, request: Request) -> Response:
        """Handle request with version-specific logic."""

        # Get API version from request state (set by middleware)
        api_version = getattr(request.state, "api_version", APIVersion.V1_0)

        # Use version-specific handler if available
        if api_version in self.version_handlers:
            return await self.version_handlers[api_version](request)

        # Fall back to default handler
        return await super().handle_request(request)


def create_version_info_endpoint():
    """Create endpoint that returns API version information."""

    def get_api_versions():
        """Get information about all API versions."""
        registry = APIVersionRegistry()

        versions_info = {}
        for version, info in registry.versions.items():
            versions_info[version.value] = {
                "status": info.status.value,
                "release_date": info.release_date.isoformat(),
                "deprecation_date": (
                    info.deprecation_date.isoformat() if info.deprecation_date else None
                ),
                "sunset_date": (
                    info.sunset_date.isoformat() if info.sunset_date else None
                ),
                "description": info.description,
                "breaking_changes": info.breaking_changes,
                "migration_guide_url": info.migration_guide_url,
            }

        return {
            "current_version": registry.get_current_version().value,
            "supported_versions": [v.value for v in registry.get_supported_versions()],
            "versions": versions_info,
        }

    return get_api_versions


def setup_versioning(app):
    """Setup API versioning middleware and endpoints."""

    # Add versioning middleware
    version_middleware = VersionMiddleware()
    app.middleware("http")(version_middleware)

    # Add version info endpoint
    version_info_handler = create_version_info_endpoint()
    app.add_api_route(
        "/api/versions", version_info_handler, methods=["GET"], tags=["System"]
    )

    logger.info("API versioning system initialized")
    return version_middleware


__all__ = [
    "APIVersion",
    "VersionStatus",
    "VersionInfo",
    "APIVersionRegistry",
    "VersionExtractor",
    "CompatibilityLayer",
    "VersionMiddleware",
    "VersionedRoute",
    "setup_versioning",
]
