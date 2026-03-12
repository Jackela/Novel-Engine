"""Unit tests for API settings module."""

from __future__ import annotations

import pytest

from src.api.settings import APISettings

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestAPISettings:
    """Tests for APISettings dataclass."""

    def test_api_settings_creation(self) -> None:
        """Test creating APISettings with explicit values."""
        settings = APISettings(
            cors_allow_origins=["http://localhost:3000"],
            cookie_name="access_token",
            refresh_cookie_name="refresh_token",
            csrf_cookie_name="csrf_token",
            guest_session_cookie_name="guest_session",
            cookie_secure=True,
            cookie_httponly=True,
            cookie_samesite="lax",
            cookie_max_age_seconds=86400,
            refresh_cookie_max_age_seconds=2592000,
            csrf_cookie_max_age_seconds=86400,
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            jwt_access_token_expire_minutes=15,
            guest_workspace_ttl_days=30,
        )

        assert settings.cookie_name == "access_token"
        assert settings.jwt_secret_key == "test-secret"
        assert settings.cookie_secure is True
        assert settings.guest_workspace_ttl_days == 30

    def test_from_env_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that from_env creates settings with default values."""
        # Clear environment variables
        monkeypatch.delenv("COOKIE_SECURE", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("GUEST_WORKSPACE_TTL_DAYS", raising=False)

        settings = APISettings.from_env()

        assert settings.cookie_secure is True  # Default is true
        assert settings.jwt_secret_key == "development-secret-key-change-in-production"
        assert settings.guest_workspace_ttl_days == 30
        assert settings.cookie_name == "access_token"
        assert settings.cors_allow_origins == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def test_from_env_cookie_secure_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test COOKIE_SECURE=false sets cookie_secure to False."""
        monkeypatch.setenv("COOKIE_SECURE", "false")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        settings = APISettings.from_env()
        assert settings.cookie_secure is False

    def test_from_env_cookie_secure_variants(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test various COOKIE_SECURE values."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        # Test "1" as true
        monkeypatch.setenv("COOKIE_SECURE", "1")
        settings = APISettings.from_env()
        assert settings.cookie_secure is True

        # Test "yes" as true
        monkeypatch.setenv("COOKIE_SECURE", "yes")
        settings = APISettings.from_env()
        assert settings.cookie_secure is True

        # Test "0" as false
        monkeypatch.setenv("COOKIE_SECURE", "0")
        settings = APISettings.from_env()
        assert settings.cookie_secure is False

    def test_from_env_jwt_secret_key_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test JWT_SECRET_KEY takes priority over SECRET_KEY."""
        monkeypatch.setenv("JWT_SECRET_KEY", "jwt-specific-key")
        monkeypatch.setenv("SECRET_KEY", "general-secret-key")

        settings = APISettings.from_env()
        assert settings.jwt_secret_key == "jwt-specific-key"

    def test_from_env_fallback_to_secret_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to SECRET_KEY when JWT_SECRET_KEY not set."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("SECRET_KEY", "general-secret-key")

        settings = APISettings.from_env()
        assert settings.jwt_secret_key == "general-secret-key"

    def test_from_env_ttl_days_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test valid GUEST_WORKSPACE_TTL_DAYS values."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        monkeypatch.setenv("GUEST_WORKSPACE_TTL_DAYS", "60")
        settings = APISettings.from_env()
        assert settings.guest_workspace_ttl_days == 60

    def test_from_env_ttl_days_invalid_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test invalid GUEST_WORKSPACE_TTL_DAYS falls back to default."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        monkeypatch.setenv("GUEST_WORKSPACE_TTL_DAYS", "invalid")
        settings = APISettings.from_env()
        assert settings.guest_workspace_ttl_days == 30

    def test_from_env_ttl_days_zero_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test zero GUEST_WORKSPACE_TTL_DAYS falls back to default."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        monkeypatch.setenv("GUEST_WORKSPACE_TTL_DAYS", "0")
        settings = APISettings.from_env()
        assert settings.guest_workspace_ttl_days == 30

    def test_from_env_ttl_days_negative_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test negative GUEST_WORKSPACE_TTL_DAYS falls back to default."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        monkeypatch.setenv("GUEST_WORKSPACE_TTL_DAYS", "-5")
        settings = APISettings.from_env()
        assert settings.guest_workspace_ttl_days == 30

    def test_settings_is_frozen(self) -> None:
        """Test that APISettings is immutable (frozen dataclass)."""
        settings = APISettings(
            cors_allow_origins=["http://localhost:3000"],
            cookie_name="access_token",
            refresh_cookie_name="refresh_token",
            csrf_cookie_name="csrf_token",
            guest_session_cookie_name="guest_session",
            cookie_secure=True,
            cookie_httponly=True,
            cookie_samesite="lax",
            cookie_max_age_seconds=86400,
            refresh_cookie_max_age_seconds=2592000,
            csrf_cookie_max_age_seconds=86400,
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            jwt_access_token_expire_minutes=15,
            guest_workspace_ttl_days=30,
        )

        with pytest.raises(AttributeError):
            settings.cookie_name = "new_name"  # type: ignore[misc]

    def test_settings_default_attributes(self) -> None:
        """Test default attribute values in from_env."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        with monkeypatch.context() as m:
            m.delenv("JWT_SECRET_KEY", raising=False)
            m.delenv("SECRET_KEY", raising=False)
            settings = APISettings.from_env()

            assert settings.cookie_httponly is True
            assert settings.cookie_samesite == "lax"
            assert settings.cookie_max_age_seconds == 86400  # 24 hours
            assert settings.refresh_cookie_max_age_seconds == 2592000  # 30 days
            assert settings.csrf_cookie_max_age_seconds == 86400  # 24 hours
            assert settings.jwt_algorithm == "HS256"
            assert settings.jwt_access_token_expire_minutes == 15
