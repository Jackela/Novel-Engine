"""
Novel Engine API Application

FastAPI 0.116+ application with OpenAPI documentation,
comprehensive middleware, and Clean Architecture.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from src.apps.api.router import api_router
from src.apps.api.middleware.error_handler import setup_exception_handlers
from src.apps.api.middleware.cors import get_cors_config


def custom_openapi(app: FastAPI) -> dict:
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add security schemes
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication",
        },
    }

    # Add server information
    openapi_schema["servers"] = [
        {"url": "/api/v1", "description": "API Version 1"},
        {"url": "http://localhost:8000/api/v1", "description": "Local development"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events."""
    # Startup
    import structlog

    logger = structlog.get_logger()
    await logger.ainfo("api_startup", message="Starting Novel Engine API")

    yield

    # Shutdown
    await logger.ainfo("api_shutdown", message="Shutting down Novel Engine API")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Novel Engine API",
        description="""
        AI-powered narrative engine with Clean Architecture.
        
        ## Features
        
        - **Character Management**: Create and manage story characters
        - **Narrative Generation**: AI-powered story generation
        - **Knowledge Management**: Context-aware knowledge system
        - **Real-time Updates**: WebSocket support for live interactions
        
        ## Authentication
        
        Most endpoints require authentication via JWT Bearer token or API key.
        """,
        version="2.0.0",
        docs_url=None,  # Custom docs endpoint
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints"},
            {"name": "auth", "description": "Authentication operations"},
            {"name": "characters", "description": "Character management"},
            {"name": "narrative", "description": "Narrative generation"},
            {"name": "knowledge", "description": "Knowledge management"},
        ],
    )

    # Override OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

    # Add middleware (order matters - last added is executed first)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS
    cors_config = get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
        expose_headers=cors_config["expose_headers"],
        max_age=cors_config["max_age"],
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include routers
    from src.apps.api.health import health_router

    app.include_router(health_router, tags=["health"])
    app.include_router(api_router, prefix="/api/v1")

    # Custom docs endpoint
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": "Novel Engine API",
            "version": "2.0.0",
            "documentation": "/docs",
            "health": "/health",
        }

    return app


# Create application instance
app = create_application()
