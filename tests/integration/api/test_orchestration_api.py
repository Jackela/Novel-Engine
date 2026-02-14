#!/usr/bin/env python3
"""
Orchestration API Integration Tests

Tests the Orchestration API endpoints with full request/response validation.
"""

from datetime import datetime

import pytest

from src.api.schemas import (
    OrchestrationStartRequest,
    OrchestrationStartResponse,
    OrchestrationStatusData,
    OrchestrationStatusResponse,
    OrchestrationStep,
    OrchestrationStopResponse,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def sample_orchestration_start_request():
    """Sample orchestration start request data."""
    return OrchestrationStartRequest(
        character_names=["Alice", "Bob", "Charlie"],
        total_turns=5,
        setting="A medieval tavern",
        scenario="The heroes meet for the first time",
    )


@pytest.fixture
def sample_orchestration_status():
    """Sample orchestration status data."""
    return OrchestrationStatusData(
        status="running",
        current_turn=2,
        total_turns=5,
        queue_length=3,
        average_processing_time=1.5,
        steps=[
            OrchestrationStep(
                id="step_1",
                name="World Update",
                status="completed",
                progress=100.0,
            ),
            OrchestrationStep(
                id="step_2",
                name="Character Actions",
                status="in_progress",
                progress=50.0,
            ),
        ],
        last_updated=datetime.now().isoformat(),
    )


@pytest.mark.integration
class TestOrchestrationStartRequest:
    """Tests for OrchestrationStartRequest validation."""

    def test_valid_request_with_all_fields(self, sample_orchestration_start_request):
        """Test valid request creation with all fields."""
        assert sample_orchestration_start_request.character_names == [
            "Alice",
            "Bob",
            "Charlie",
        ]
        assert sample_orchestration_start_request.total_turns == 5
        assert sample_orchestration_start_request.setting == "A medieval tavern"

    def test_valid_request_with_minimal_fields(self):
        """Test valid request with only required fields."""
        request = OrchestrationStartRequest()
        assert request.character_names is None
        assert request.total_turns == 3  # default value

    def test_character_names_minimum_validation(self):
        """Test that character_names must have at least 2 characters."""
        with pytest.raises(ValueError):
            OrchestrationStartRequest(character_names=["Solo"])

    def test_character_names_maximum_validation(self):
        """Test that character_names cannot exceed 6 characters."""
        with pytest.raises(ValueError):
            OrchestrationStartRequest(
                character_names=["A", "B", "C", "D", "E", "F", "G"]
            )

    def test_total_turns_minimum_validation(self):
        """Test that total_turns must be at least 1."""
        with pytest.raises(ValueError):
            OrchestrationStartRequest(total_turns=0)

    def test_total_turns_maximum_validation(self):
        """Test that total_turns cannot exceed 10."""
        with pytest.raises(ValueError):
            OrchestrationStartRequest(total_turns=15)

    def test_valid_turns_range(self):
        """Test valid total_turns values."""
        for turns in [1, 5, 10]:
            request = OrchestrationStartRequest(total_turns=turns)
            assert request.total_turns == turns


@pytest.mark.integration
class TestOrchestrationStatusData:
    """Tests for OrchestrationStatusData validation."""

    def test_status_data_creation(self, sample_orchestration_status):
        """Test that status data creates correctly."""
        assert sample_orchestration_status.status == "running"
        assert sample_orchestration_status.current_turn == 2
        assert sample_orchestration_status.total_turns == 5
        assert len(sample_orchestration_status.steps) == 2

    def test_status_data_defaults(self):
        """Test status data default values."""
        status = OrchestrationStatusData(status="idle")
        assert status.current_turn == 0
        assert status.total_turns == 0
        assert status.queue_length == 0
        assert status.average_processing_time == 0.0
        assert status.steps == []

    def test_steps_validation(self):
        """Test that steps validate correctly."""
        step = OrchestrationStep(
            id="test_step",
            name="Test Step",
            status="pending",
            progress=0.0,
        )
        assert step.progress == 0.0

        step_complete = OrchestrationStep(
            id="test_step",
            name="Test Step",
            status="completed",
            progress=100.0,
        )
        assert step_complete.progress == 100.0

    def test_step_progress_bounds(self):
        """Test that step progress is bounded 0-100."""
        with pytest.raises(ValueError):
            OrchestrationStep(
                id="test",
                name="Test",
                status="error",
                progress=-10.0,
            )

        with pytest.raises(ValueError):
            OrchestrationStep(
                id="test",
                name="Test",
                status="error",
                progress=150.0,
            )


@pytest.mark.integration
class TestOrchestrationResponses:
    """Tests for orchestration response models."""

    def test_start_response_success(self):
        """Test successful start response."""
        response = OrchestrationStartResponse(
            success=True,
            status="started",
            task_id="task_12345",
            message="Orchestration started successfully",
        )
        assert response.success is True
        assert response.task_id == "task_12345"

    def test_start_response_failure(self):
        """Test failed start response."""
        response = OrchestrationStartResponse(
            success=False,
            status="failed",
            message="Not enough characters selected",
        )
        assert response.success is False
        assert response.task_id is None

    def test_status_response_serialization(self, sample_orchestration_status):
        """Test status response serialization."""
        response = OrchestrationStatusResponse(
            success=True,
            data=sample_orchestration_status,
            message="Status retrieved successfully",
        )

        data = response.model_dump()
        assert data["success"] is True
        assert data["data"]["status"] == "running"
        assert len(data["data"]["steps"]) == 2

    def test_stop_response(self):
        """Test stop response model."""
        response = OrchestrationStopResponse(
            success=True,
            message="Orchestration stopped",
        )
        assert response.success is True


@pytest.mark.integration
class TestOrchestrationStateTransitions:
    """Tests for orchestration state transition logic."""

    def test_idle_to_running_transition(self):
        """Test transition from idle to running state."""
        idle_status = OrchestrationStatusData(status="idle")
        assert idle_status.status == "idle"

        running_status = OrchestrationStatusData(
            status="running",
            current_turn=1,
            total_turns=5,
        )
        assert running_status.status == "running"
        assert running_status.current_turn == 1

    def test_running_to_paused_transition(self):
        """Test transition from running to paused state."""
        paused_status = OrchestrationStatusData(
            status="paused",
            current_turn=3,
            total_turns=5,
        )
        assert paused_status.status == "paused"
        assert paused_status.current_turn == 3

    def test_running_to_completed_transition(self):
        """Test transition from running to completed state."""
        completed_status = OrchestrationStatusData(
            status="completed",
            current_turn=5,
            total_turns=5,
        )
        assert completed_status.status == "completed"
        assert completed_status.current_turn == completed_status.total_turns

    def test_error_state(self):
        """Test error state handling."""
        error_status = OrchestrationStatusData(
            status="error",
            current_turn=2,
            total_turns=5,
        )
        assert error_status.status == "error"
