"""Unit tests for OrchestrationService.

Tests cover orchestration operations, service availability checks,
and default character discovery for the orchestration service.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.api.schemas import (
    NarrativeData,
    OrchestrationStartRequest,
    OrchestrationStatusData,
)
from src.api.services.orchestration_service import OrchestrationService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_api_service():
    """Create a mock API service."""
    service = AsyncMock()
    service.get_status = AsyncMock(return_value={"status": "running", "active": True})
    service.start_simulation = AsyncMock(
        return_value={
            "success": True,
            "status": "started",
            "task_id": "task-001",
            "message": "Simulation started",
        }
    )
    service.stop_simulation = AsyncMock(
        return_value={"success": True, "message": "Simulation stopped"}
    )
    service.pause_simulation = AsyncMock(
        return_value={"success": True, "message": "Simulation paused"}
    )
    service.get_narrative = AsyncMock(
        return_value={
            "story": "Once upon a time...",
            "participants": ["char-001", "char-002"],
            "turns_completed": 5,
            "last_generated": "2024-01-15T10:30:00",
        }
    )
    return service


@pytest.fixture
def orchestration_service(mock_api_service):
    """Create an orchestration service with mock API service."""
    return OrchestrationService(api_service=mock_api_service)


@pytest.fixture
def orchestration_service_no_api():
    """Create an orchestration service without API service."""
    return OrchestrationService(api_service=None)


class TestOrchestrationServiceGetStatus:
    """Tests for get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_returns_status_data(
        self, orchestration_service, mock_api_service
    ):
        """get_status returns OrchestrationStatusData on success."""
        result = await orchestration_service.get_status()

        assert result.is_ok
        assert isinstance(result.value, OrchestrationStatusData)
        assert result.value.status == "running"
        assert result.value.active is True

    @pytest.mark.asyncio
    async def test_get_status_returns_error_when_no_service(
        self, orchestration_service_no_api
    ):
        """get_status returns error when API service unavailable."""
        result = await orchestration_service_no_api.get_status()

        assert result.is_error
        assert result.error.code == "SERVICE_UNAVAILABLE"
        assert "not available" in result.error.message.lower()


class TestOrchestrationServiceStart:
    """Tests for start method."""

    @pytest.mark.asyncio
    async def test_start_returns_task_info(
        self, orchestration_service, mock_api_service
    ):
        """start returns task info on success."""
        result = await orchestration_service.start()

        assert result.is_ok
        assert result.value["success"] is True
        assert result.value["task_id"] == "task-001"

    @pytest.mark.asyncio
    async def test_start_uses_default_characters(
        self, orchestration_service, mock_api_service
    ):
        """start uses default characters when none provided."""
        with patch.object(
            orchestration_service,
            "_get_default_characters",
            return_value=["char1", "char2"],
        ):
            await orchestration_service.start()

            mock_api_service.start_simulation.assert_called_once()
            call_args = mock_api_service.start_simulation.call_args[0][0]
            assert call_args.character_names == ["char1", "char2"]

    @pytest.mark.asyncio
    async def test_start_uses_provided_characters(
        self, orchestration_service, mock_api_service
    ):
        """start uses provided characters from request."""
        request = OrchestrationStartRequest(
            character_names=["hero", "villain"], total_turns=10
        )

        await orchestration_service.start(request)

        call_args = mock_api_service.start_simulation.call_args[0][0]
        assert call_args.character_names == ["hero", "villain"]
        assert call_args.turns == 10

    @pytest.mark.asyncio
    async def test_start_returns_error_when_no_service(
        self, orchestration_service_no_api
    ):
        """start returns error when API service unavailable."""
        result = await orchestration_service_no_api.start()

        assert result.is_error
        assert result.error.code == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_start_handles_value_error(
        self, orchestration_service, mock_api_service
    ):
        """start handles ValueError from API service."""
        mock_api_service.start_simulation.side_effect = ValueError("Invalid request")

        result = await orchestration_service.start()

        assert result.is_error
        assert result.error.code == "INVALID_REQUEST"
        assert "invalid request" in result.error.message.lower()


class TestOrchestrationServiceStop:
    """Tests for stop method."""

    @pytest.mark.asyncio
    async def test_stop_returns_stop_result(
        self, orchestration_service, mock_api_service
    ):
        """stop returns stop result on success."""
        result = await orchestration_service.stop()

        assert result.is_ok
        assert result.value["success"] is True
        assert "stopped" in result.value["message"].lower()
        mock_api_service.stop_simulation.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_returns_error_when_no_service(
        self, orchestration_service_no_api
    ):
        """stop returns error when API service unavailable."""
        result = await orchestration_service_no_api.stop()

        assert result.is_error
        assert result.error.code == "SERVICE_UNAVAILABLE"


class TestOrchestrationServicePause:
    """Tests for pause method."""

    @pytest.mark.asyncio
    async def test_pause_returns_pause_result(
        self, orchestration_service, mock_api_service
    ):
        """pause returns pause result on success."""
        result = await orchestration_service.pause()

        assert result.is_ok
        assert result.value["success"] is True
        assert "paused" in result.value["message"].lower()
        mock_api_service.pause_simulation.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_returns_error_when_no_service(
        self, orchestration_service_no_api
    ):
        """pause returns error when API service unavailable."""
        result = await orchestration_service_no_api.pause()

        assert result.is_error
        assert result.error.code == "SERVICE_UNAVAILABLE"


class TestOrchestrationServiceGetNarrative:
    """Tests for get_narrative method."""

    @pytest.mark.asyncio
    async def test_get_narrative_returns_narrative_data(
        self, orchestration_service, mock_api_service
    ):
        """get_narrative returns NarrativeData on success."""
        result = await orchestration_service.get_narrative()

        assert result.is_ok
        assert isinstance(result.value, NarrativeData)
        assert result.value.story == "Once upon a time..."
        assert result.value.turns_completed == 5
        assert result.value.has_content is True

    @pytest.mark.asyncio
    async def test_get_narrative_handles_empty_story(
        self, orchestration_service, mock_api_service
    ):
        """get_narrative handles empty story correctly."""
        mock_api_service.get_narrative.return_value = {
            "story": "",
            "participants": [],
            "turns_completed": 0,
        }

        result = await orchestration_service.get_narrative()

        assert result.is_ok
        assert result.value.story == ""
        assert result.value.has_content is False

    @pytest.mark.asyncio
    async def test_get_narrative_returns_error_when_no_service(
        self, orchestration_service_no_api
    ):
        """get_narrative returns error when API service unavailable."""
        result = await orchestration_service_no_api.get_narrative()

        assert result.is_error
        assert result.error.code == "SERVICE_UNAVAILABLE"


class TestOrchestrationServiceGetDefaultCharacters:
    """Tests for _get_default_characters method."""

    def test_get_default_characters_returns_available_characters(self, tmp_path):
        """_get_default_characters returns available characters from filesystem."""
        # Create mock characters directory
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        (chars_dir / "hero").mkdir()
        (chars_dir / "villain").mkdir()
        (chars_dir / "sidekick").mkdir()
        (chars_dir / "extra").mkdir()

        service = OrchestrationService()
        with patch(
            "src.api.services.orchestration_service.get_characters_directory_path"
        ) as mock_path:
            mock_path.return_value = str(chars_dir)
            result = service._get_default_characters()

        assert len(result) <= 3
        assert all(isinstance(char, str) for char in result)

    def test_get_default_characters_returns_fallback_on_error(self):
        """_get_default_characters returns fallback on filesystem error."""
        service = OrchestrationService()

        with patch(
            "src.api.services.orchestration_service.get_characters_directory_path"
        ) as mock_path:
            mock_path.side_effect = Exception("Path error")
            result = service._get_default_characters()

        assert result == ["pilot", "scientist", "engineer"]

    def test_get_default_characters_returns_fallback_for_empty_dir(self, tmp_path):
        """_get_default_characters returns fallback for empty directory."""
        chars_dir = tmp_path / "empty_characters"
        chars_dir.mkdir()

        service = OrchestrationService()
        with patch(
            "src.api.services.orchestration_service.get_characters_directory_path"
        ) as mock_path:
            mock_path.return_value = str(chars_dir)
            result = service._get_default_characters()

        assert result == ["pilot", "scientist", "engineer"]


class TestOrchestrationServiceDefaultTurns:
    """Tests for default turns handling."""

    @pytest.mark.asyncio
    async def test_start_uses_default_turns_when_not_provided(
        self, orchestration_service, mock_api_service
    ):
        """start uses default 3 turns when not provided."""
        request = OrchestrationStartRequest(character_names=["char1"])

        await orchestration_service.start(request)

        call_args = mock_api_service.start_simulation.call_args[0][0]
        assert call_args.turns == 3


class TestOrchestrationServiceInitialization:
    """Tests for service initialization."""

    def test_can_create_without_api_service(self):
        """Can create service without API service."""
        service = OrchestrationService()

        assert service.api_service is None

    def test_can_create_with_api_service(self, mock_api_service):
        """Can create service with API service."""
        service = OrchestrationService(api_service=mock_api_service)

        assert service.api_service is mock_api_service
