"""Tests for Honcho configuration.

Tests the HonchoSettings configuration class with various scenarios.
"""

from typing import Literal, cast

import pytest
from src.shared.infrastructure.honcho.config import HonchoSettings


class TestHonchoSettings:
    """Test suite for HonchoSettings."""

    def test_default_settings(self) -> None:
        """Test default configuration values."""
        settings = HonchoSettings()

        assert settings.deployment == "self_hosted"
        assert settings.base_url == "http://localhost:8000"
        assert settings.timeout == 30
        assert settings.max_retries == 3
        assert settings.max_memories_per_query == 10
        assert settings.default_session_ttl_days == 365

    def test_cloud_deployment(self, monkeypatch) -> None:
        """Test cloud deployment configuration."""
        monkeypatch.setenv("HONCHO_DEPLOYMENT", "cloud")
        monkeypatch.setenv("HONCHO_BASE_URL", "https://api.honcho.dev")
        monkeypatch.setenv("HONCHO_API_KEY", "test-api-key")

        settings = HonchoSettings()

        assert settings.deployment == "cloud"
        assert settings.is_cloud is True
        assert settings.is_self_hosted is False
        assert settings.api_key == "test-api-key"

    def test_base_url_normalization(self) -> None:
        """Test that base_url is normalized without trailing slash."""
        settings = HonchoSettings(base_url="http://localhost:8000/")
        assert settings.base_url == "http://localhost:8000"

        settings2 = HonchoSettings(base_url="https://api.honcho.dev///")
        assert settings2.base_url == "https://api.honcho.dev"

    def test_get_workspace_id_with_story(self) -> None:
        """Test workspace ID generation with story ID."""
        settings = HonchoSettings()

        workspace_id = settings.get_workspace_id("story-123")
        assert workspace_id == "novel-engine-story-123"

    def test_get_workspace_id_default(self) -> None:
        """Test default workspace ID generation."""
        settings = HonchoSettings()

        workspace_id = settings.get_workspace_id()
        assert workspace_id == "novel-engine"

    def test_deployment_validation(self) -> None:
        """Test deployment mode validation and normalization."""
        # Test various cloud aliases
        cloud_values = ["cloud", "CLOUD", "Cloud", "managed"]
        for value in cloud_values:
            settings = HonchoSettings(
                deployment=cast(Literal["cloud", "self_hosted"], value)
            )
            assert settings.deployment == "cloud"

        # Test various self-hosted aliases
        self_hosted_values = ["self_hosted", "self-hosted", "local", "SELF_HOSTED"]
        for value in self_hosted_values:
            settings = HonchoSettings(
                deployment=cast(Literal["cloud", "self_hosted"], value)
            )
            assert settings.deployment == "self_hosted"

    def test_invalid_deployment(self) -> None:
        """Test that invalid deployment raises error."""
        with pytest.raises(ValueError, match="Invalid deployment mode"):
            # Use cast to bypass type checker for testing invalid values
            HonchoSettings(deployment=cast(Literal["cloud", "self_hosted"], "invalid"))

    def test_timeout_validation(self) -> None:
        """Test timeout validation constraints."""
        # Valid values
        HonchoSettings(timeout=5)
        HonchoSettings(timeout=300)

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            HonchoSettings(timeout=1)  # Too low

        with pytest.raises(ValueError):
            HonchoSettings(timeout=400)  # Too high

    def test_max_memories_validation(self) -> None:
        """Test max_memories_per_query validation."""
        # Valid values
        HonchoSettings(max_memories_per_query=1)
        HonchoSettings(max_memories_per_query=100)

        # Invalid values
        with pytest.raises(ValueError):
            HonchoSettings(max_memories_per_query=0)

        with pytest.raises(ValueError):
            HonchoSettings(max_memories_per_query=101)


class TestHonchoSettingsEnvironmentVariables:
    """Test environment variable configuration."""

    def test_env_prefix(self, monkeypatch) -> None:
        """Test that HONCHO_ prefix is used for env vars."""
        monkeypatch.setenv("HONCHO_TIMEOUT", "60")
        monkeypatch.setenv("HONCHO_MAX_RETRIES", "5")
        monkeypatch.setenv("HONCHO_DEFAULT_WORKSPACE_NAME", "my-novel")

        settings = HonchoSettings()

        assert settings.timeout == 60
        assert settings.max_retries == 5
        assert settings.default_workspace_name == "my-novel"
