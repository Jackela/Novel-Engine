"""
Tests for CORS configuration.
"""

import os
import pytest
from unittest.mock import patch

from src.apps.api.middleware.cors import (
    get_cors_config,
    get_cors_origins,
    is_origin_allowed,
)


class TestCorsConfig:
    """Test CORS configuration."""

    def test_default_cors_config(self):
        """Test default CORS configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_cors_config()

            assert "allow_origins" in config
            assert "allow_credentials" in config
            assert "allow_methods" in config
            assert "allow_headers" in config
            assert "expose_headers" in config
            assert "max_age" in config

            # Check default origins
            assert "http://localhost:3000" in config["allow_origins"]
            assert config["allow_credentials"] is True
            assert "GET" in config["allow_methods"]
            assert "Content-Type" in config["allow_headers"]

    def test_custom_origins_from_env(self):
        """Test custom origins from environment."""
        with patch.dict(
            os.environ,
            {
                "CORS_ALLOWED_ORIGINS": "https://app.example.com,https://admin.example.com"
            },
        ):
            config = get_cors_config()
            assert "https://app.example.com" in config["allow_origins"]
            assert "https://admin.example.com" in config["allow_origins"]

    def test_production_restrictions(self):
        """Test CORS restrictions in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            config = get_cors_config()
            # Wildcard should be removed in production
            assert "*" not in config["allow_origins"]

    def test_allow_credentials_from_env(self):
        """Test allow credentials from environment."""
        with patch.dict(os.environ, {"CORS_ALLOW_CREDENTIALS": "false"}):
            config = get_cors_config()
            assert config["allow_credentials"] is False


class TestGetCorsOrigins:
    """Test get_cors_origins function."""

    def test_get_cors_origins(self):
        """Test getting CORS origins."""
        origins = get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0


class TestIsOriginAllowed:
    """Test is_origin_allowed function."""

    def test_exact_match_allowed(self):
        """Test exact origin match."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "https://example.com"}):
            assert is_origin_allowed("https://example.com") is True

    def test_exact_match_not_allowed(self):
        """Test non-matching origin."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "https://example.com"}):
            assert is_origin_allowed("https://other.com") is False

    def test_wildcard_origin(self):
        """Test wildcard origin."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}):
            assert is_origin_allowed("https://any-domain.com") is True

    def test_wildcard_port(self):
        """Test wildcard port in origin."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:*"}):
            assert is_origin_allowed("http://localhost:3000") is True
            assert is_origin_allowed("http://localhost:8080") is True

    def test_empty_origin(self):
        """Test empty origin."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": ""}):
            # Should use defaults which include localhost
            assert is_origin_allowed("http://localhost:3000") is True
