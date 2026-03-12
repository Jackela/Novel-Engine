"""Unit tests for API dependencies module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit

from src.api.deps import (
    get_guest_session_manager,
    get_optional_workspace_id,
    get_settings,
    get_workspace_character_store,
    get_workspace_store,
    require_workspace_id,
)
from src.api.settings import APISettings


@pytest.mark.unit
class TestGetSettings:
    """Tests for get_settings dependency."""

    def test_get_settings_from_app_state(self, mock_request) -> None:
        """Test getting settings from app.state."""
        existing_settings = APISettings.from_env()
        mock_request.app.state.settings = existing_settings

        result = get_settings(mock_request)

        assert result is existing_settings

    def test_get_settings_creates_new_if_none(self, mock_request) -> None:
        """Test creating new settings if not in app.state."""
        mock_request.app.state.settings = None

        result = get_settings(mock_request)

        assert isinstance(result, APISettings)
        # Should also set it back on app.state
        assert mock_request.app.state.settings is result

    def test_get_settings_creates_if_missing_attribute(self, mock_request) -> None:
        """Test creating new settings if app.state has no settings attribute."""
        delattr(mock_request.app.state, "settings")

        result = get_settings(mock_request)

        assert isinstance(result, APISettings)
        assert mock_request.app.state.settings is result


@pytest.mark.unit
class TestGetWorkspaceStore:
    """Tests for get_workspace_store dependency."""

    def test_get_workspace_store_success(self, mock_request) -> None:
        """Test getting workspace store from app state."""
        mock_store = MagicMock()
        mock_request.app.state.workspace_store = mock_store

        result = get_workspace_store(mock_request)

        assert result is mock_store

    def test_get_workspace_store_unavailable(self, mock_request) -> None:
        """Test 503 error when workspace store is unavailable."""
        mock_request.app.state.workspace_store = None

        with pytest.raises(HTTPException) as exc_info:
            get_workspace_store(mock_request)

        assert exc_info.value.status_code == 503
        assert "Workspace service unavailable" in exc_info.value.detail

    def test_get_workspace_store_missing_attribute(self, mock_request) -> None:
        """Test 503 error when workspace_store attribute is missing."""
        delattr(mock_request.app.state, "workspace_store")

        with pytest.raises(HTTPException) as exc_info:
            get_workspace_store(mock_request)

        assert exc_info.value.status_code == 503


@pytest.mark.unit
class TestGetWorkspaceCharacterStore:
    """Tests for get_workspace_character_store dependency."""

    def test_get_workspace_character_store_success(self, mock_request) -> None:
        """Test getting workspace character store from app state."""
        mock_store = MagicMock()
        mock_request.app.state.workspace_character_store = mock_store

        result = get_workspace_character_store(mock_request)

        assert result is mock_store

    def test_get_workspace_character_store_unavailable(self, mock_request) -> None:
        """Test 503 error when workspace character store is unavailable."""
        mock_request.app.state.workspace_character_store = None

        with pytest.raises(HTTPException) as exc_info:
            get_workspace_character_store(mock_request)

        assert exc_info.value.status_code == 503


@pytest.mark.unit
class TestGetGuestSessionManager:
    """Tests for get_guest_session_manager dependency."""

    def test_get_guest_session_manager_success(self, mock_request) -> None:
        """Test getting guest session manager from app state."""
        mock_manager = MagicMock()
        mock_request.app.state.guest_session_manager = mock_manager

        result = get_guest_session_manager(mock_request)

        assert result is mock_manager

    def test_get_guest_session_manager_unavailable(self, mock_request) -> None:
        """Test 503 error when guest session manager is unavailable."""
        mock_request.app.state.guest_session_manager = None

        with pytest.raises(HTTPException) as exc_info:
            get_guest_session_manager(mock_request)

        assert exc_info.value.status_code == 503


@pytest.mark.unit
class TestGetOptionalWorkspaceId:
    """Tests for get_optional_workspace_id dependency."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock guest session manager."""
        manager = MagicMock()
        manager.cookie_name = "workspace_token"
        manager.decode = MagicMock(return_value="decoded-workspace-id")
        return manager

    @pytest.fixture
    def mock_store(self):
        """Create a mock workspace store."""
        return MagicMock()

    def test_get_optional_workspace_id_with_valid_token(
        self, mock_request, mock_manager, mock_store
    ) -> None:
        """Test getting workspace ID with valid token."""
        mock_request.cookies = {"workspace_token": "valid-token"}

        result = get_optional_workspace_id(mock_request, mock_manager, mock_store)

        assert result == "decoded-workspace-id"
        mock_manager.decode.assert_called_once_with("valid-token")
        mock_store.get_or_create.assert_called_once_with("decoded-workspace-id")

    def test_get_optional_workspace_id_no_token_with_default(
        self, mock_request, mock_manager, mock_store
    ) -> None:
        """Test getting default workspace ID when no token and default exists."""
        mock_request.cookies = {}
        mock_request.app.state.default_workspace_id = "default-workspace"

        result = get_optional_workspace_id(mock_request, mock_manager, mock_store)

        assert result == "default-workspace"
        mock_store.get_or_create.assert_called_once_with("default-workspace")

    def test_get_optional_workspace_id_no_token_no_default(
        self, mock_request, mock_manager, mock_store
    ) -> None:
        """Test returning None when no token and no default workspace."""
        mock_request.cookies = {}
        mock_request.app.state.default_workspace_id = None

        result = get_optional_workspace_id(mock_request, mock_manager, mock_store)

        assert result is None

    def test_get_optional_workspace_id_invalid_token(
        self, mock_request, mock_manager, mock_store
    ) -> None:
        """Test returning None when token cannot be decoded."""
        mock_request.cookies = {"workspace_token": "invalid-token"}
        mock_manager.decode.return_value = None

        result = get_optional_workspace_id(mock_request, mock_manager, mock_store)

        assert result is None


@pytest.mark.unit
class TestRequireWorkspaceId:
    """Tests for require_workspace_id dependency."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock API settings."""
        settings = MagicMock(spec=APISettings)
        settings.cookie_secure = True
        settings.cookie_httponly = True
        settings.cookie_samesite = "lax"
        return settings

    @pytest.fixture
    def mock_manager(self):
        """Create a mock guest session manager."""
        manager = MagicMock()
        manager.cookie_name = "workspace_token"
        manager.encode = MagicMock(return_value="encoded-token")
        manager.resolve_or_create = MagicMock()
        manager.resolve_or_create.return_value.workspace_id = "resolved-workspace"
        manager.cookie_max_age_seconds = MagicMock(return_value=86400)
        return manager

    @pytest.fixture
    def mock_store(self):
        """Create a mock workspace store."""
        return MagicMock()

    def test_require_workspace_id_with_valid_token(
        self, mock_request, mock_response, mock_settings, mock_manager, mock_store
    ) -> None:
        """Test requiring workspace ID with valid token."""
        mock_request.cookies = {"workspace_token": "valid-token"}

        result = require_workspace_id(
            mock_request, mock_response, mock_settings, mock_manager, mock_store
        )

        assert result == "resolved-workspace"
        mock_response.set_cookie.assert_called_once()
        call_args = mock_response.set_cookie.call_args
        assert call_args[0][0] == "workspace_token"
        assert call_args[1]["httponly"] is True
        assert call_args[1]["secure"] is True

    def test_require_workspace_id_no_token_with_default(
        self, mock_request, mock_response, mock_settings, mock_manager, mock_store
    ) -> None:
        """Test using default workspace when no token."""
        mock_request.cookies = {}
        mock_request.app.state.default_workspace_id = "default-workspace"

        result = require_workspace_id(
            mock_request, mock_response, mock_settings, mock_manager, mock_store
        )

        assert result == "default-workspace"
        mock_store.get_or_create.assert_called_with("default-workspace")

    def test_require_workspace_id_sets_cookie_correctly(
        self, mock_request, mock_response, mock_settings, mock_manager, mock_store
    ) -> None:
        """Test that cookie is set with correct attributes."""
        mock_request.cookies = {"workspace_token": "token"}
        mock_settings.cookie_secure = False
        mock_settings.cookie_samesite = "strict"

        require_workspace_id(
            mock_request, mock_response, mock_settings, mock_manager, mock_store
        )

        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["secure"] is False
        assert call_kwargs["samesite"] == "strict"
        assert call_kwargs["max_age"] == 86400
