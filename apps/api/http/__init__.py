#!/usr/bin/env python3
"""
API HTTP Layer

This package contains FastAPI routers for different domain contexts,
providing RESTful endpoints with proper validation and error handling.

Available Routers:
- world_router: World context CQRS endpoints for commands and queries
"""

from .world_router import router as world_router

__all__ = [
    "world_router"
]