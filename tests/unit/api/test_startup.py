"""Unit tests for API startup initialization."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from src.api.startup import (
    NON_EMPTY_WHEN_SET,
    PRODUCTION_REQUIRED_ENV_VARS,
    REQUIRED_ENV_VARS,
    EnvironmentValidationError,
    initialize_app_state,
    validate_environment,
)


@pytest.mark.unit
class TestEventBusInitialization:
    """Tests for EventBus initialization."""

    @pytest.mark.asyncio
    async def test_uses_enterprise_event_bus(self) -> None:
        """Test that startup uses Enterprise EventBus from src.events."""
        from src.events.event_bus import EventBus as EnterpriseEventBus

        app = MagicMock()
        app.state = MagicMock()

        with patch("src.api.startup.get_service_container") as mock_container:
            mock_container.return_value = MagicMock()

            await initialize_app_state(app)

            # Verify the event bus is Enterprise version
            assert hasattr(app.state, "event_bus")
            assert isinstance(app.state.event_bus, EnterpriseEventBus)


@pytest.mark.unit
class TestEnvironmentValidation:
    """Tests for environment variable validation at startup."""

    def test_validate_environment_passes_in_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation passes in development mode with no required vars."""
        # Clear any existing environment settings
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        # Should not raise in development mode
        validate_environment()

    def test_validate_environment_fails_in_production_missing_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation fails in production when SECRET_KEY is missing."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        with pytest.raises(EnvironmentValidationError) as exc_info:
            validate_environment()

        assert "SECRET_KEY" in str(exc_info.value)

    def test_validate_environment_fails_in_production_missing_jwt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation fails in production when JWT_SECRET_KEY is missing."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        with pytest.raises(EnvironmentValidationError) as exc_info:
            validate_environment()

        assert "JWT_SECRET_KEY" in str(exc_info.value)

    def test_validate_environment_passes_in_production_with_required_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation passes in production when all required vars are set."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "secure-secret-key-for-testing")
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-jwt-key-for-testing")

        # Should not raise
        validate_environment()

    def test_validate_environment_fails_with_empty_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation fails when an API key is explicitly set to empty string."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "")  # Empty string

        with pytest.raises(EnvironmentValidationError) as exc_info:
            validate_environment()

        assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_validate_environment_passes_with_valid_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation passes when API keys are properly set."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "valid-api-key-12345")

        # Should not raise
        validate_environment()

    def test_validate_environment_warns_about_placeholder_values(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that validation warns about placeholder values in API keys."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key_here")

        # Should not raise but should log warning
        validate_environment()

        assert any("placeholder" in record.message.lower() for record in caplog.records)

    def test_required_env_vars_constant_exists(self) -> None:
        """Test that REQUIRED_ENV_VARS constant is defined."""
        assert isinstance(REQUIRED_ENV_VARS, list)

    def test_production_required_env_vars_constant_exists(self) -> None:
        """Test that PRODUCTION_REQUIRED_ENV_VARS constant is defined."""
        assert isinstance(PRODUCTION_REQUIRED_ENV_VARS, list)
        assert "SECRET_KEY" in PRODUCTION_REQUIRED_ENV_VARS
        assert "JWT_SECRET_KEY" in PRODUCTION_REQUIRED_ENV_VARS

    def test_non_empty_when_set_constant_exists(self) -> None:
        """Test that NON_EMPTY_WHEN_SET constant is defined."""
        assert isinstance(NON_EMPTY_WHEN_SET, set)
        assert "GEMINI_API_KEY" in NON_EMPTY_WHEN_SET
        assert "OPENAI_API_KEY" in NON_EMPTY_WHEN_SET
        assert "ANTHROPIC_API_KEY" in NON_EMPTY_WHEN_SET

    def test_validate_environment_fails_with_empty_secret_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation fails when SECRET_KEY is empty in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "")  # Empty string
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        with pytest.raises(EnvironmentValidationError) as exc_info:
            validate_environment()

        error_msg = str(exc_info.value)
        assert "SECRET_KEY" in error_msg or "JWT_SECRET_KEY" in error_msg

