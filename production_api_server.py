#!/usr/bin/env python3
"""Compatibility entrypoint for the production FastAPI server."""

from src.api.production_server import app

__all__ = ["app"]
