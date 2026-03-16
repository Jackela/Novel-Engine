"""
Tests for API router configuration.
"""

import pytest
from fastapi import APIRouter

from src.apps.api.router import api_router, register_context_routers


class TestRouterConfiguration:
    """Test router configuration."""

    def test_api_router_exists(self):
        """Test API router is created."""
        assert api_router is not None
        assert isinstance(api_router, APIRouter)

    def test_register_context_routers(self):
        """Test context router registration."""
        # Should not raise any errors even if contexts don't exist
        register_context_routers()

    def test_router_is_configurable(self):
        """Test router can include sub-routers."""
        test_router = APIRouter()

        @test_router.get("/test")
        def test_endpoint():
            return {"test": True}

        # Should be able to include without errors
        api_router.include_router(test_router, prefix="/test-prefix")

        # Check route was added
        routes = [r for r in api_router.routes if hasattr(r, "path")]
        assert any("/test-prefix" in str(r.path) for r in routes)


class TestRouterErrorHandling:
    """Test router error handling."""

    def test_invalid_router_import(self):
        """Test graceful handling of missing routers."""
        # register_context_routers handles ImportError gracefully
        register_context_routers()
