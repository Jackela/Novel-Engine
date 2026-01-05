#!/usr/bin/env python3
"""
Decision API Unit Tests

Comprehensive tests for the Decision API endpoints that enable
user participatory interaction during story generation.

Test Coverage:
- GET /api/decision/status - Decision system status
- POST /api/decision/respond - Submit decision response
- POST /api/decision/confirm - Confirm negotiation result
- POST /api/decision/skip - Skip current decision
- GET /api/decision/history - Get decision history
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Import decision module components
try:
    from src.decision.api_router import (
        DecisionResponseRequest,
        NegotiationConfirmRequest,
        SkipDecisionRequest,
        broadcast_decision_event,
        initialize_decision_system,
    )
    from src.decision.decision_point_detector import DecisionPointDetector
    from src.decision.models import (
        DecisionOption,
        DecisionPoint,
        DecisionPointType,
        FeasibilityResult,
        NegotiationResult,
        PauseState,
        PendingDecision,
        UserDecision,
    )
    from src.decision.negotiation_engine import NegotiationEngine
    from src.decision.pause_controller import InteractionPauseController

    DECISION_MODULE_AVAILABLE = True
except ImportError:
    DECISION_MODULE_AVAILABLE = False


# ===================================================================
# Test Fixtures
# ===================================================================


@pytest.fixture
def mock_pause_controller():
    """Create a mock pause controller."""
    controller = MagicMock(spec=InteractionPauseController)
    controller.is_paused = False
    controller.current_decision_point = None
    controller.get_status.return_value = {
        "state": "running",
        "is_paused": False,
        "current_decision": None,
        "negotiation_result": None,
    }
    return controller


@pytest.fixture
def mock_decision_detector():
    """Create a mock decision point detector."""
    detector = MagicMock(spec=DecisionPointDetector)
    detector.decision_count = 0
    return detector


@pytest.fixture
def mock_negotiation_engine():
    """Create a mock negotiation engine."""
    engine = MagicMock(spec=NegotiationEngine)
    return engine


@pytest.fixture
def sample_decision_options():
    """Create sample decision options."""
    return [
        DecisionOption(
            option_id=1,
            label="Investigate Signal",
            description="Proceed with caution to investigate the mysterious signal",
            icon="🔍",
            impact_preview="May reveal hidden information",
        ),
        DecisionOption(
            option_id=2,
            label="Evacuate Area",
            description="Prioritize safety and evacuate the area immediately",
            icon="⚠️",
            impact_preview="Ensures character safety",
        ),
        DecisionOption(
            option_id=3,
            label="Call for Backup",
            description="Request additional support before proceeding",
            icon="📡",
            impact_preview="Delays action but increases resources",
        ),
    ]


@pytest.fixture
def sample_decision_point(sample_decision_options):
    """Create a sample decision point."""
    return DecisionPoint(
        decision_id="test-decision-001",
        decision_type=DecisionPointType.CHARACTER_CHOICE,
        turn_number=5,
        title="Critical Decision Point",
        description="The story has reached a pivotal moment.",
        narrative_context="Aria stands at the crossroads of the Meridian Station...",
        options=sample_decision_options,
        default_option_id=1,
        dramatic_tension=Decimal("8.0"),
        emotional_intensity=Decimal("7.0"),
        timeout_seconds=120,
    )


@pytest.fixture
def sample_negotiation_result():
    """Create a sample negotiation result."""
    return NegotiationResult(
        decision_id="test-decision-001",
        feasibility=FeasibilityResult.MINOR_ADJUSTMENT,
        explanation="The action is mostly feasible but needs a small adjustment.",
        adjusted_action="Have the character investigate cautiously",
        alternatives=[],
    )


# ===================================================================
# Model Tests
# ===================================================================


@pytest.mark.skipif(
    not DECISION_MODULE_AVAILABLE, reason="Decision module not available"
)
class TestDecisionModels:
    """Tests for decision data models."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_option_creation(self):
        """Test DecisionOption creation and serialization."""
        option = DecisionOption(
            option_id=1,
            label="Test Option",
            description="A test option",
            icon="🧪",
            impact_preview="Test impact",
        )

        assert option.option_id == 1
        assert option.label == "Test Option"
        assert option.description == "A test option"
        assert option.icon == "🧪"
        assert option.impact_preview == "Test impact"

        # Test serialization
        option_dict = option.to_dict()
        assert option_dict["option_id"] == 1
        assert option_dict["label"] == "Test Option"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_point_creation(self, sample_decision_options):
        """Test DecisionPoint creation."""
        dp = DecisionPoint(
            decision_id="test-dp-001",
            decision_type=DecisionPointType.TURNING_POINT,
            turn_number=3,
            title="Test Decision",
            description="A test decision point",
            options=sample_decision_options,
            default_option_id=1,
        )

        assert dp.decision_id == "test-dp-001"
        assert dp.decision_type == DecisionPointType.TURNING_POINT
        assert dp.turn_number == 3
        assert len(dp.options) == 3
        assert dp.default_option_id == 1
        assert dp.is_resolved is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_point_serialization(self, sample_decision_point):
        """Test DecisionPoint serialization to dict."""
        dp_dict = sample_decision_point.to_dict()

        assert dp_dict["decision_id"] == "test-decision-001"
        assert dp_dict["decision_type"] == "character_choice"
        assert dp_dict["turn_number"] == 5
        assert dp_dict["title"] == "Critical Decision Point"
        assert len(dp_dict["options"]) == 3
        assert dp_dict["default_option_id"] == 1
        assert dp_dict["timeout_seconds"] == 120
        assert dp_dict["dramatic_tension"] == 8.0
        assert dp_dict["emotional_intensity"] == 7.0
        assert "created_at" in dp_dict

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_point_from_dict(self):
        """Test DecisionPoint creation from dict."""
        data = {
            "decision_id": "dp-fromdict",
            "decision_type": "crisis",
            "turn_number": 10,
            "title": "Crisis Point",
            "description": "A critical crisis",
            "options": [
                {"option_id": 1, "label": "Option A", "description": "Desc A"},
                {"option_id": 2, "label": "Option B", "description": "Desc B"},
            ],
            "default_option_id": 2,
            "dramatic_tension": "9.5",
            "timeout_seconds": 60,
        }

        dp = DecisionPoint.from_dict(data)

        assert dp.decision_id == "dp-fromdict"
        assert dp.decision_type == DecisionPointType.CRISIS
        assert dp.turn_number == 10
        assert len(dp.options) == 2
        assert dp.dramatic_tension == Decimal("9.5")
        assert dp.timeout_seconds == 60

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_point_type_enum(self):
        """Test all DecisionPointType enum values."""
        assert DecisionPointType.TURNING_POINT.value == "turning_point"
        assert DecisionPointType.CRISIS.value == "crisis"
        assert DecisionPointType.CLIMAX.value == "climax"
        assert DecisionPointType.REVELATION.value == "revelation"
        assert DecisionPointType.TRANSFORMATION.value == "transformation"
        assert DecisionPointType.CHARACTER_CHOICE.value == "character_choice"
        assert DecisionPointType.RELATIONSHIP_CHANGE.value == "relationship_change"
        assert DecisionPointType.CONFLICT_ESCALATION.value == "conflict_escalation"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_feasibility_result_enum(self):
        """Test all FeasibilityResult enum values."""
        assert FeasibilityResult.ACCEPTED.value == "accepted"
        assert FeasibilityResult.MINOR_ADJUSTMENT.value == "minor_adjustment"
        assert FeasibilityResult.ALTERNATIVE_REQUIRED.value == "alternative_required"
        assert FeasibilityResult.REJECTED.value == "rejected"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_pause_state_enum(self):
        """Test all PauseState enum values."""
        assert PauseState.RUNNING.value == "running"
        assert PauseState.AWAITING_INPUT.value == "awaiting_input"
        assert PauseState.NEGOTIATING.value == "negotiating"
        assert PauseState.RESUMING.value == "resuming"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_user_decision_creation(self):
        """Test UserDecision creation."""
        # Option selection
        user_decision = UserDecision(
            decision_id="test-001",
            input_type="option",
            selected_option_id=2,
        )

        assert user_decision.decision_id == "test-001"
        assert user_decision.input_type == "option"
        assert user_decision.selected_option_id == 2
        assert user_decision.free_text is None
        assert user_decision.use_default is False

        # Free text
        user_decision_text = UserDecision(
            decision_id="test-002",
            input_type="freetext",
            free_text="Make the character run away quickly",
        )

        assert user_decision_text.input_type == "freetext"
        assert user_decision_text.free_text == "Make the character run away quickly"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_user_decision_serialization(self):
        """Test UserDecision serialization."""
        user_decision = UserDecision(
            decision_id="test-001",
            input_type="freetext",
            free_text="Custom action",
        )

        ud_dict = user_decision.to_dict()

        assert ud_dict["decision_id"] == "test-001"
        assert ud_dict["input_type"] == "freetext"
        assert ud_dict["free_text"] == "Custom action"
        assert "submitted_at" in ud_dict

    @pytest.mark.unit
    @pytest.mark.fast
    def test_negotiation_result_creation(self):
        """Test NegotiationResult creation."""
        result = NegotiationResult(
            decision_id="test-001",
            feasibility=FeasibilityResult.MINOR_ADJUSTMENT,
            explanation="Small adjustment needed",
            adjusted_action="Modified action",
        )

        assert result.decision_id == "test-001"
        assert result.feasibility == FeasibilityResult.MINOR_ADJUSTMENT
        assert result.explanation == "Small adjustment needed"
        assert result.adjusted_action == "Modified action"
        assert result.user_confirmed is False
        assert result.user_insisted is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_negotiation_result_serialization(self, sample_negotiation_result):
        """Test NegotiationResult serialization."""
        nr_dict = sample_negotiation_result.to_dict()

        assert nr_dict["decision_id"] == "test-decision-001"
        assert nr_dict["feasibility"] == "minor_adjustment"
        assert "explanation" in nr_dict
        assert "adjusted_action" in nr_dict
        assert nr_dict["user_confirmed"] is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_pending_decision_creation(self, sample_decision_point):
        """Test PendingDecision creation."""
        pending = PendingDecision(
            decision_point=sample_decision_point,
            state=PauseState.AWAITING_INPUT,
        )

        assert pending.decision_point == sample_decision_point
        assert pending.state == PauseState.AWAITING_INPUT
        assert pending.user_response is None
        assert pending.negotiation_result is None
        assert pending.resolved_at is None


# ===================================================================
# Request/Response Model Tests
# ===================================================================


@pytest.mark.skipif(
    not DECISION_MODULE_AVAILABLE, reason="Decision module not available"
)
class TestRequestModels:
    """Tests for API request models."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_response_request_option(self):
        """Test DecisionResponseRequest for option selection."""
        request = DecisionResponseRequest(
            decision_id="test-001",
            input_type="option",
            selected_option_id=2,
        )

        assert request.decision_id == "test-001"
        assert request.input_type == "option"
        assert request.selected_option_id == 2
        assert request.free_text is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_response_request_freetext(self):
        """Test DecisionResponseRequest for free text input."""
        request = DecisionResponseRequest(
            decision_id="test-001",
            input_type="freetext",
            free_text="Make the character escape",
        )

        assert request.decision_id == "test-001"
        assert request.input_type == "freetext"
        assert request.free_text == "Make the character escape"
        assert request.selected_option_id is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_negotiation_confirm_request(self):
        """Test NegotiationConfirmRequest creation."""
        # Accept adjustment
        request = NegotiationConfirmRequest(
            decision_id="test-001",
            accepted=True,
            insist_original=False,
        )

        assert request.decision_id == "test-001"
        assert request.accepted is True
        assert request.insist_original is False

        # Insist original
        request_insist = NegotiationConfirmRequest(
            decision_id="test-001",
            accepted=False,
            insist_original=True,
        )

        assert request_insist.accepted is False
        assert request_insist.insist_original is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skip_decision_request(self):
        """Test SkipDecisionRequest creation."""
        request = SkipDecisionRequest(decision_id="test-001")

        assert request.decision_id == "test-001"


# ===================================================================
# API Endpoint Tests (with mocked dependencies)
# ===================================================================


@pytest.mark.skipif(
    not DECISION_MODULE_AVAILABLE, reason="Decision module not available"
)
class TestDecisionAPIEndpoints:
    """Tests for Decision API endpoints."""

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_success(
        self, mock_pause_controller, mock_decision_detector, mock_negotiation_engine
    ):
        """Test GET /api/decision/status - success case."""
        # Initialize the decision system
        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch(
            "src.decision.api_router._decision_detector", mock_decision_detector
        ), patch(
            "src.decision.api_router._negotiation_engine", mock_negotiation_engine
        ):
            # Call the endpoint function directly
            from src.decision.api_router import get_decision_status

            result = await get_decision_status()

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["state"] == "running"
            assert result["data"]["is_paused"] is False

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_system_not_initialized(self):
        """Test GET /api/decision/status - system not initialized."""
        with patch("src.decision.api_router._pause_controller", None):
            from src.decision.api_router import get_decision_status

            result = await get_decision_status()

            assert result["success"] is False
            assert "message" in result
            assert result["data"] is None

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_with_pending_decision(
        self,
        mock_pause_controller,
        mock_decision_detector,
        mock_negotiation_engine,
        sample_decision_point,
    ):
        """Test GET /api/decision/status - with pending decision."""
        mock_pause_controller.is_paused = True
        mock_pause_controller.current_decision_point = sample_decision_point
        mock_pause_controller.get_status.return_value = {
            "state": "awaiting_input",
            "is_paused": True,
            "current_decision": sample_decision_point.to_dict(),
            "negotiation_result": None,
        }

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import get_decision_status

            result = await get_decision_status()

            assert result["success"] is True
            assert result["data"]["state"] == "awaiting_input"
            assert result["data"]["is_paused"] is True
            assert result["data"]["current_decision"] is not None

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_response_option_success(
        self, mock_pause_controller, sample_decision_point
    ):
        """Test POST /api/decision/respond - option selection success."""
        mock_pause_controller.is_paused = True
        mock_pause_controller.current_decision_point = sample_decision_point
        mock_pause_controller.submit_response = AsyncMock(return_value=True)

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch("src.decision.api_router._broadcast_sse_event", MagicMock()):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id="test-decision-001",
                input_type="option",
                selected_option_id=2,
            )

            result = await submit_decision_response(request)

            assert result["success"] is True
            assert result["data"]["needs_negotiation"] is False
            mock_pause_controller.submit_response.assert_called_once()

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_response_no_pending_decision(self, mock_pause_controller):
        """Test POST /api/decision/respond - no pending decision."""
        mock_pause_controller.is_paused = False

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id="test-001",
                input_type="option",
                selected_option_id=1,
            )

            with pytest.raises(HTTPException) as exc_info:
                await submit_decision_response(request)

            assert exc_info.value.status_code == 400
            assert "No pending decision" in exc_info.value.detail

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_response_option_without_id(self, mock_pause_controller):
        """Test POST /api/decision/respond - option type without option_id."""
        mock_pause_controller.is_paused = True

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id="test-001",
                input_type="option",
                selected_option_id=None,
            )

            with pytest.raises(HTTPException) as exc_info:
                await submit_decision_response(request)

            assert exc_info.value.status_code == 400
            assert "selected_option_id required" in exc_info.value.detail

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_response_freetext_without_text(self, mock_pause_controller):
        """Test POST /api/decision/respond - freetext type without text."""
        mock_pause_controller.is_paused = True

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id="test-001",
                input_type="freetext",
                free_text=None,
            )

            with pytest.raises(HTTPException) as exc_info:
                await submit_decision_response(request)

            assert exc_info.value.status_code == 400
            assert "free_text required" in exc_info.value.detail

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_response_freetext_needs_negotiation(
        self,
        mock_pause_controller,
        mock_negotiation_engine,
        sample_decision_point,
        sample_negotiation_result,
    ):
        """Test POST /api/decision/respond - freetext needs negotiation."""
        mock_pause_controller.is_paused = True
        mock_pause_controller.current_decision_point = sample_decision_point
        mock_pause_controller.start_negotiation = AsyncMock()
        mock_negotiation_engine.evaluate_input = AsyncMock(
            return_value=sample_negotiation_result
        )

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch(
            "src.decision.api_router._negotiation_engine", mock_negotiation_engine
        ), patch(
            "src.decision.api_router._broadcast_sse_event", MagicMock()
        ):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id="test-decision-001",
                input_type="freetext",
                free_text="Make the character do something unusual",
            )

            result = await submit_decision_response(request)

            assert result["success"] is True
            assert result["data"]["needs_negotiation"] is True
            assert "negotiation" in result["data"]
            mock_pause_controller.start_negotiation.assert_called_once()

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_response_expired(
        self, mock_pause_controller, sample_decision_point
    ):
        """Test POST /api/decision/respond - decision expired."""
        mock_pause_controller.is_paused = True
        mock_pause_controller.current_decision_point = sample_decision_point
        mock_pause_controller.submit_response = AsyncMock(return_value=False)

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id="test-decision-001",
                input_type="option",
                selected_option_id=1,
            )

            with pytest.raises(HTTPException) as exc_info:
                await submit_decision_response(request)

            assert exc_info.value.status_code == 400
            assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confirm_negotiation_accept(self, mock_pause_controller):
        """Test POST /api/decision/confirm - accept adjustment."""
        mock_pause_controller.confirm_negotiation = AsyncMock(return_value=True)

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch("src.decision.api_router._broadcast_sse_event", MagicMock()):
            from src.decision.api_router import confirm_negotiation

            request = NegotiationConfirmRequest(
                decision_id="test-001",
                accepted=True,
                insist_original=False,
            )

            result = await confirm_negotiation(request)

            assert result["success"] is True
            mock_pause_controller.confirm_negotiation.assert_called_once_with(
                decision_id="test-001",
                accepted=True,
                insist_original=False,
            )

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confirm_negotiation_insist(self, mock_pause_controller):
        """Test POST /api/decision/confirm - insist original."""
        mock_pause_controller.confirm_negotiation = AsyncMock(return_value=True)

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch("src.decision.api_router._broadcast_sse_event", MagicMock()):
            from src.decision.api_router import confirm_negotiation

            request = NegotiationConfirmRequest(
                decision_id="test-001",
                accepted=False,
                insist_original=True,
            )

            result = await confirm_negotiation(request)

            assert result["success"] is True
            mock_pause_controller.confirm_negotiation.assert_called_once_with(
                decision_id="test-001",
                accepted=False,
                insist_original=True,
            )

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confirm_negotiation_failure(self, mock_pause_controller):
        """Test POST /api/decision/confirm - failure."""
        mock_pause_controller.confirm_negotiation = AsyncMock(return_value=False)

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import confirm_negotiation

            request = NegotiationConfirmRequest(
                decision_id="test-001",
                accepted=True,
                insist_original=False,
            )

            with pytest.raises(HTTPException) as exc_info:
                await confirm_negotiation(request)

            assert exc_info.value.status_code == 400

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skip_decision_success(self, mock_pause_controller):
        """Test POST /api/decision/skip - success."""
        mock_pause_controller.skip_decision = AsyncMock(return_value=True)

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch("src.decision.api_router._broadcast_sse_event", MagicMock()):
            from src.decision.api_router import skip_decision

            request = SkipDecisionRequest(decision_id="test-001")

            result = await skip_decision(request)

            assert result["success"] is True
            assert result["message"] == "Decision skipped"
            mock_pause_controller.skip_decision.assert_called_once_with("test-001")

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skip_decision_failure(self, mock_pause_controller):
        """Test POST /api/decision/skip - failure."""
        mock_pause_controller.skip_decision = AsyncMock(return_value=False)

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import skip_decision

            request = SkipDecisionRequest(decision_id="test-001")

            with pytest.raises(HTTPException) as exc_info:
                await skip_decision(request)

            assert exc_info.value.status_code == 400

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_history_success(self, mock_decision_detector):
        """Test GET /api/decision/history - success."""
        mock_decision_detector.decision_count = 5

        with patch(
            "src.decision.api_router._decision_detector", mock_decision_detector
        ):
            from src.decision.api_router import get_decision_history

            result = await get_decision_history()

            assert result["success"] is True
            assert result["data"]["total_decisions"] == 5

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_history_not_initialized(self):
        """Test GET /api/decision/history - not initialized."""
        with patch("src.decision.api_router._decision_detector", None):
            from src.decision.api_router import get_decision_history

            result = await get_decision_history()

            assert result["success"] is False
            assert "message" in result


# ===================================================================
# Integration-style Tests
# ===================================================================


@pytest.mark.skipif(
    not DECISION_MODULE_AVAILABLE, reason="Decision module not available"
)
class TestDecisionSystemIntegration:
    """Integration tests for the decision system."""

    @pytest.mark.integration
    @pytest.mark.unit
    def test_initialize_decision_system(
        self, mock_pause_controller, mock_decision_detector, mock_negotiation_engine
    ):
        """Test decision system initialization."""
        mock_broadcast = MagicMock()

        # Reset global state
        with patch("src.decision.api_router._pause_controller", None), patch(
            "src.decision.api_router._decision_detector", None
        ), patch("src.decision.api_router._negotiation_engine", None):
            initialize_decision_system(
                pause_controller=mock_pause_controller,
                decision_detector=mock_decision_detector,
                negotiation_engine=mock_negotiation_engine,
                broadcast_sse_event=mock_broadcast,
            )

    @pytest.mark.integration
    @pytest.mark.unit
    def test_broadcast_decision_event(self):
        """Test SSE event broadcasting."""
        mock_broadcast = MagicMock()

        with patch("src.decision.api_router._broadcast_sse_event", mock_broadcast):
            broadcast_decision_event(
                "decision_required",
                {
                    "decision_id": "test-001",
                    "description": "A decision is required",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0][0]
            assert call_args["type"] == "decision_required"
            assert "decision_id" in call_args["data"]

    @pytest.mark.integration
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_decision_workflow_option_selection(
        self,
        mock_pause_controller,
        mock_decision_detector,
        mock_negotiation_engine,
        sample_decision_point,
    ):
        """Test complete workflow: decision detected -> option selected -> resolved."""
        # 1. Initial state - running
        mock_pause_controller.is_paused = False
        mock_pause_controller.get_status.return_value = {
            "state": "running",
            "is_paused": False,
        }

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            from src.decision.api_router import get_decision_status

            result = await get_decision_status()
            assert result["data"]["state"] == "running"

        # 2. Decision detected - awaiting input
        mock_pause_controller.is_paused = True
        mock_pause_controller.current_decision_point = sample_decision_point
        mock_pause_controller.get_status.return_value = {
            "state": "awaiting_input",
            "is_paused": True,
            "current_decision": sample_decision_point.to_dict(),
        }

        with patch("src.decision.api_router._pause_controller", mock_pause_controller):
            result = await get_decision_status()
            assert result["data"]["state"] == "awaiting_input"
            assert result["data"]["current_decision"] is not None

        # 3. User submits option
        mock_pause_controller.submit_response = AsyncMock(return_value=True)

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch("src.decision.api_router._broadcast_sse_event", MagicMock()):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id=sample_decision_point.decision_id,
                input_type="option",
                selected_option_id=2,
            )

            result = await submit_decision_response(request)
            assert result["success"] is True

    @pytest.mark.integration
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_decision_workflow_freetext_with_negotiation(
        self,
        mock_pause_controller,
        mock_negotiation_engine,
        sample_decision_point,
        sample_negotiation_result,
    ):
        """Test workflow: freetext input -> negotiation -> accept."""
        # Setup
        mock_pause_controller.is_paused = True
        mock_pause_controller.current_decision_point = sample_decision_point
        mock_pause_controller.start_negotiation = AsyncMock()
        mock_negotiation_engine.evaluate_input = AsyncMock(
            return_value=sample_negotiation_result
        )

        # 1. Submit freetext - triggers negotiation
        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch(
            "src.decision.api_router._negotiation_engine", mock_negotiation_engine
        ), patch(
            "src.decision.api_router._broadcast_sse_event", MagicMock()
        ):
            from src.decision.api_router import submit_decision_response

            request = DecisionResponseRequest(
                decision_id=sample_decision_point.decision_id,
                input_type="freetext",
                free_text="Make the character do something special",
            )

            result = await submit_decision_response(request)
            assert result["success"] is True
            assert result["data"]["needs_negotiation"] is True

        # 2. User accepts negotiation
        mock_pause_controller.confirm_negotiation = AsyncMock(return_value=True)

        with patch(
            "src.decision.api_router._pause_controller", mock_pause_controller
        ), patch("src.decision.api_router._broadcast_sse_event", MagicMock()):
            from src.decision.api_router import confirm_negotiation

            confirm_request = NegotiationConfirmRequest(
                decision_id=sample_decision_point.decision_id,
                accepted=True,
                insist_original=False,
            )

            result = await confirm_negotiation(confirm_request)
            assert result["success"] is True


# ===================================================================
# Helper function to run tests
# ===================================================================


def run_decision_api_tests():
    """Run all decision API tests."""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-m",
            "api or unit",
            "--tb=short",
            __file__,
        ],
        capture_output=True,
        text=True,
    )

    print("Decision API Test Results:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    run_decision_api_tests()
