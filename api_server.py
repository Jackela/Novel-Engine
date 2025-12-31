#!/usr/bin/env python3
"""
StoryForge API server entrypoint (compat wrapper).

Canonical app factory lives at `src.api.app:create_app`.
This module preserves the historical `api_server:app` import path for tests,
scripts, and Uvicorn runners.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import uvicorn

from src.api.app import create_app as _create_app
from src.api.settings import APISettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Settings/constants kept for backward compatibility with tests.
_SETTINGS = APISettings.from_env()
JWT_SECRET_KEY = _SETTINGS.jwt_secret_key
JWT_ALGORITHM = _SETTINGS.jwt_algorithm

# Import World Context API Router (for tests that introspect availability).
try:
    from apps.api.http import world_router as _world_router  # noqa: F401

    WORLD_ROUTER_AVAILABLE = True
except ImportError as exc:
    WORLD_ROUTER_AVAILABLE = False
    logger.warning("World context router not available: %s", exc)


def create_app():
    return _create_app(settings=_SETTINGS)


app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8000, debug: bool = False) -> None:
    """Run the FastAPI server via Uvicorn."""
    uvicorn.run("api_server:app", host=host, port=port, reload=debug, log_level="info")


if __name__ == "__main__":
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    debug_flag = os.getenv("API_DEBUG", "1")
    run_server(host=host, port=port, debug=debug_flag not in {"0", "false", "False"})
