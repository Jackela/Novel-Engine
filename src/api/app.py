from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.api.errors import install_error_handlers
from src.api.settings import APISettings
from src.api.startup import (
    ensure_workspace_services,
    initialize_app_state,
    shutdown_app_state,
)

logger = logging.getLogger(__name__)


def create_app(
    *, settings: Optional[APISettings] = None, debug: bool = False
) -> FastAPI:
    resolved_settings = settings or APISettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        await initialize_app_state(app)
        yield
        await shutdown_app_state(app)

    app = FastAPI(
        title="StoryForge AI API",
        description="RESTful API for the StoryForge AI Interactive Story Engine.",
        version="1.0.0",
        lifespan=lifespan,
    )

    ensure_workspace_services(app, resolved_settings)

    app.state.api_start_time = datetime.now(UTC)

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _cors_preflight_middleware(request: Request, call_next):
        if request.method == "OPTIONS":
            origin = (
                resolved_settings.cors_allow_origins[0]
                if resolved_settings.cors_allow_origins
                else "*"
            )
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                },
            )
        return await call_next(request)

    install_error_handlers(app, debug=debug)

    from src.api.routers.auth import router as auth_router
    from src.api.routers.cache import router as cache_router
    from src.api.routers.campaigns import router as campaigns_router
    from src.api.routers.characters import router as characters_router
    from src.api.routers.events import router as events_router
    from src.api.routers.generation import router as generation_router
    from src.api.routers.guest import router as guest_router
    from src.api.routers.health import router as health_router
    from src.api.routers.meta import router as meta_router
    from src.api.routers.orchestration import router as orchestration_router
    from src.api.routers.simulations import router as simulations_router

    app.include_router(health_router)
    app.include_router(meta_router)
    app.include_router(cache_router)
    app.include_router(orchestration_router)
    app.include_router(simulations_router)
    app.include_router(characters_router)
    app.include_router(campaigns_router)
    app.include_router(guest_router)
    app.include_router(events_router)
    app.include_router(generation_router)
    app.include_router(auth_router)

    app.include_router(health_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")
    app.include_router(cache_router, prefix="/api")
    app.include_router(orchestration_router, prefix="/api")
    app.include_router(simulations_router, prefix="/api")
    app.include_router(characters_router, prefix="/api")
    app.include_router(campaigns_router, prefix="/api")
    app.include_router(guest_router, prefix="/api")
    app.include_router(events_router, prefix="/api")
    app.include_router(generation_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")

    try:
        from src.api.prompts_router import router as prompts_router

        app.include_router(prompts_router)
        app.include_router(prompts_router, prefix="/api")
        app.state.prompts_router_available = True
        logger.info("Prompts router included with prefix /api")
    except ImportError as exc:
        app.state.prompts_router_available = False
        logger.warning("Prompts router not available: %s", exc)

    try:
        from src.decision import decision_router

        app.include_router(decision_router)
        app.include_router(decision_router, prefix="/api")
        app.state.decision_router_available = True
        logger.info("Decision router included with prefix /api")
    except ImportError as exc:
        app.state.decision_router_available = False
        logger.warning("Decision router not available: %s", exc)

    try:
        from apps.api.http import world_router

        app.include_router(world_router)
        app.include_router(world_router, prefix="/api")
        app.state.world_router_available = True
        logger.info("World context router included with prefix /api")
    except ImportError as exc:
        app.state.world_router_available = False
        logger.warning("World context router not available: %s", exc)

    return app
