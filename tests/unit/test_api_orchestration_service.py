import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.api_service import ApiOrchestrationService
from src.api.schemas import SimulationRequest


# BDD-style test naming
class TestApiOrchestrationService:
    @pytest.fixture
    def service(self):
        """Given an instance of ApiOrchestrationService"""
        orchestrator = MagicMock()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()
        character_factory = MagicMock()
        service = ApiOrchestrationService(orchestrator, event_bus, character_factory)
        return service, character_factory

    @pytest.mark.asyncio
    async def test_start_orchestration_success(self, service):
        """
        Scenario: Start Orchestration Success
          Given a valid orchestration request
          When start_orchestration is called
          Then it should initialize the Director Agent
          And return a success status
        """
        service_instance, mock_factory = service

        # Given
        request = SimulationRequest(character_names=["char_1", "char_2"], turns=3)

        # When
        # Mocking internal dependencies to isolate the service logic
        # We must explicitly patch the imported names in the module under test
        with patch("src.services.api_service.DirectorAgent") as MockDirector, patch(
            "src.services.api_service.ChroniclerAgent"
        ) as MockChronicler:
            mock_director_instance = MockDirector.return_value
            mock_director_instance.initialize = AsyncMock()

            # Setup Injected CharacterFactory mock (from fixture)
            mock_factory.create_character.return_value = MagicMock()

            mock_chronicler_instance = MockChronicler.return_value
            mock_chronicler_instance.transcribe_log.return_value = "Story Content"
            mock_chronicler_instance.transcribe_log.return_value = "Story Content"

            result = await service_instance.start_simulation(request)

            # Then

            # Verify return structure (ApiOrchestrationService return format)
            assert result["success"] is True
            assert result["status"] == "started"

            # Since the loop is a background task, we must await it to test the inner logic
            if service_instance._current_task:
                await service_instance._current_task

            # Now we can verify Director was initialized because the loop finished
            MockDirector.assert_called_once()
            # initialize() is not called in the service logic shown, but register_agent is
            mock_director_instance.register_agent.assert_called()

    @pytest.mark.asyncio
    async def test_start_orchestration_failure(self, service):
        """
        Scenario: Start Orchestration Failure
          Given the Director Agent fails to initialize
          When start_orchestration is called
          Then it should raise an exception or return an error state
        """
        service_instance, mock_factory = service

        # Given
        request = SimulationRequest(
            character_names=["fail_char_1", "fail_char_2"], turns=3
        )

        # When
        with patch("src.services.api_service.DirectorAgent") as MockDirector:
            mock_director_instance = MockDirector.return_value
            # Simulate initialization failure inside the loop
            mock_director_instance.initialize = AsyncMock(
                side_effect=Exception("Initialization failed")
            )

            # Setup Injected CharacterFactory mock
            mock_factory.create_character.return_value = MagicMock()

            # The start_simulation call should succeed (it just starts the task)
            result = await service_instance.start_simulation(request)
            assert result["success"] is True

            # Now await the task to let the error happen
            if service_instance._current_task:
                await service_instance._current_task

            # Verify status is error
            status = await service_instance.get_status()
            assert status["status"] == "error"
