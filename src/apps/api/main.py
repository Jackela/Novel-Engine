"""Canonical FastAPI application for Novel Studio."""

# mypy: disable-error-code=misc

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.apps.api.middleware.cors import get_cors_config
from src.apps.api.middleware.error_handler import setup_exception_handlers
from src.apps.api.runtime import StudioRuntime, attach_runtime, create_runtime, lifespan
from src.apps.api.swagger_ui import add_docs_route
from src.contexts.studio.interface.http.dependencies import attach_studio_store
from src.shared.infrastructure.config.settings import (
    NovelEngineSettings,
    get_settings,
)
from src.shared.infrastructure.middleware import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
)


class NovelStudioApplication(FastAPI):
    def openapi(self) -> dict[str, Any]:
        return custom_openapi(self)


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate the canonical OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "cookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "novel_studio_session",
        },
    }
    _apply_openapi_security(openapi_schema)
    openapi_schema["servers"] = [
        {"url": "/", "description": "Same-origin Novel Studio service"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _apply_openapi_security(openapi_schema: dict[str, Any]) -> None:
    """Normalize generated auth metadata to browser cookie session schemes."""
    cookie_auth: list[dict[str, list[Any]]] = [{"cookieAuth": []}]
    paths = openapi_schema.get("paths", {})
    if not isinstance(paths, dict):
        return

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue

            if path in {
                "/api/setup",
                "/api/session/login",
                "/api/session/guest",
            }:
                operation["security"] = []
            elif path.startswith(
                (
                    "/api/projects",
                    "/api/providers",
                    "/api/imports",
                    "/api/session",
                )
            ):
                operation["security"] = cookie_auth


def _new_fastapi_app(resolved_settings: NovelEngineSettings) -> FastAPI:
    return NovelStudioApplication(
        title=resolved_settings.project_name,
        description=(
            "Novel Studio API for projects, Markdown revisions, AI proposals, "
            "reviews, snapshots, exports, sessions, and durable jobs."
        ),
        version=resolved_settings.project_version,
        docs_url=None,
        redoc_url=resolved_settings.api.redoc_url,
        openapi_url=resolved_settings.api.openapi_url,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Health and readiness endpoints"},
            {"name": "studio", "description": "Novel Studio product operations"},
        ],
    )


def _add_http_middleware(
    app: FastAPI,
    resolved_settings: NovelEngineSettings,
) -> None:
    app.state.settings = resolved_settings
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    cors_config = get_cors_config(resolved_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
        expose_headers=cors_config["expose_headers"]
        + [CORRELATION_ID_HEADER, REQUEST_ID_HEADER],
        max_age=cors_config["max_age"],
    )

    app.add_middleware(LoggingMiddleware)
    if resolved_settings.monitoring.metrics_enabled:
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RateLimitMiddleware)


def _include_application_routes(app: FastAPI) -> None:
    from src.apps.api.health import health_router
    from src.apps.api.router import api_router

    setup_exception_handlers(app)

    app.include_router(health_router, tags=["health"])
    app.include_router(api_router, prefix="/api")


def _mount_frontend(app: FastAPI, resolved_settings: NovelEngineSettings) -> None:
    frontend_dist = resolved_settings.base_dir / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="studio-assets")

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def studio_spa(full_path: str) -> FileResponse | dict[str, str]:
        if full_path.startswith(("api/", "health", "metrics", "docs", "openapi")):
            return {
                "name": resolved_settings.project_name,
                "version": resolved_settings.project_version,
                "api_base": "/api",
            }
        candidate = (frontend_dist / full_path).resolve()
        if (
            frontend_dist.resolve() in {candidate, *candidate.parents}
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        index = frontend_dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return {
            "name": resolved_settings.project_name,
            "version": resolved_settings.project_version,
            "message": "Build frontend/ to enable the Studio UI.",
        }


def create_application(
    settings: NovelEngineSettings | None = None,
    *,
    runtime: StudioRuntime | None = None,
) -> FastAPI:
    """Create and configure the canonical FastAPI application."""
    resolved_settings = settings or get_settings()
    resolved_runtime = runtime or create_runtime(resolved_settings)
    app = _new_fastapi_app(resolved_settings)
    attach_runtime(app, resolved_runtime)
    attach_studio_store(app, resolved_runtime.store)
    _add_http_middleware(app, resolved_settings)
    _include_application_routes(app)
    add_docs_route(app, resolved_settings.api)
    _mount_frontend(app, resolved_settings)
    return app


def main() -> None:
    """Run the canonical FastAPI app with Uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.apps.api.main:create_application",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.logging.level.value.lower(),
        factory=True,
    )


__all__ = ["create_application", "main"]
