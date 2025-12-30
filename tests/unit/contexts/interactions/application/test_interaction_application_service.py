#!/usr/bin/env python3
"""
Comprehensive Unit Tests for InteractionApplicationService

Test suite covering application service operations, session management, proposal handling,
analytics, health monitoring, and business rule enforcement in the Interaction Context.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from contexts.interactions.application.commands.interaction_command_handlers import (
    InteractionCommandHandler,
)
from contexts.interactions.application.services.interaction_application_service import (
    InteractionApplicationService,
)
from contexts.interactions.domain.aggregates.negotiation_session import (
    NegotiationSession,
)
from contexts.interactions.domain.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from contexts.interactions.domain.services.negotiation_service import NegotiationService
from contexts.interactions.domain.value_objects.interaction_id import InteractionId
from contexts.interactions.domain.value_objects.negotiation_party import (
    NegotiationParty,
)
from contexts.interactions.domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    TerminationReason,
)
from contexts.interactions.domain.value_objects.proposal_response import (
    ProposalResponse,
)
from contexts.interactions.domain.value_objects.proposal_terms import ProposalTerms


class TestInteractionApplicationServiceInitialization:
    """Test suite for InteractionApplicationService initialization."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_initialization_with_all_dependencies(self):
        """Test initialization with all dependencies provided."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)

        service = InteractionApplicationService(
            session_repository=mock_repository,
            negotiation_service=mock_negotiation_service,
        )

        assert service.session_repository is mock_repository
        assert service.negotiation_service is mock_negotiation_service
        assert isinstance(service.command_handler, InteractionCommandHandler)

    @pytest.mark.unit
    def test_initialization_with_minimal_dependencies(self):
        """Test initialization with minimal dependencies (default negotiation service)."""
        mock_repository = Mock(spec=NegotiationSessionRepository)

        service = InteractionApplicationService(session_repository=mock_repository)

        assert service.session_repository is mock_repository
        assert isinstance(service.negotiation_service, NegotiationService)
        assert isinstance(service.command_handler, InteractionCommandHandler)

    @pytest.mark.unit
    def test_command_handler_initialization(self):
        """Test that command handler is properly initialized with dependencies."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)

        with patch(
            "contexts.interactions.application.services.interaction_application_service.InteractionCommandHandler"
        ) as mock_handler_class:
            mock_handler = Mock()
            mock_handler_class.return_value = mock_handler

            service = InteractionApplicationService(
                session_repository=mock_repository,
                negotiation_service=mock_negotiation_service,
            )

            mock_handler_class.assert_called_once_with(
                session_repository=mock_repository,
                negotiation_service=mock_negotiation_service,
            )
            assert service.command_handler is mock_handler


class TestNegotiationSessionOperations:
    """Test suite for negotiation session management operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)
        mock_command_handler = AsyncMock(spec=InteractionCommandHandler)

        return {
            "repository": mock_repository,
            "negotiation_service": mock_negotiation_service,
            "command_handler": mock_command_handler,
        }

    @pytest.fixture
    def sample_negotiation_party(self):
        """Create sample negotiation party for testing."""
        return Mock(spec=NegotiationParty)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_negotiation_session_success(self, mock_dependencies):
        """Test successful negotiation session creation."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        # Mock command handler response
        session_id = uuid4()
        created_at = datetime.now(timezone.utc)
        mock_result = {
            "session_id": session_id,
            "session_name": "Test Negotiation",
            "created_at": created_at,
            "status": "initiation",
            "max_parties": 5,
            "events": ["session_created"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_create_negotiation_session.return_value = mock_result

        result = await service.create_negotiation_session(
            session_name="Test Negotiation",
            session_type="business_deal",
            created_by=uuid4(),
            max_parties=5,
            session_timeout_hours=48,
            auto_advance_phases=True,
            require_unanimous_agreement=False,
        )

        # Verify command was created and handled
        mock_dependencies[
            "command_handler"
        ].handle_create_negotiation_session.assert_called_once()

        # Verify result structure
        assert result["operation"] == "create_negotiation_session"
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert result["session_name"] == "Test Negotiation"
        assert result["created_at"] == created_at
        assert result["status"] == "initiation"
        assert result["configuration"]["max_parties"] == 5
        assert result["configuration"]["timeout_hours"] == 48
        assert result["configuration"]["auto_advance_phases"] is True
        assert result["configuration"]["require_unanimous"] is False
        assert result["events_generated"] == ["session_created"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_negotiation_session_with_defaults(self, mock_dependencies):
        """Test negotiation session creation with default parameters."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_result = {
            "session_id": session_id,
            "session_name": "Default Session",
            "created_at": datetime.now(timezone.utc),
            "status": "initiation",
            "max_parties": 10,  # Default value
            "events": ["session_created"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_create_negotiation_session.return_value = mock_result

        await service.create_negotiation_session(
            session_name="Default Session", session_type="general", created_by=uuid4()
        )

        # Verify default values were used
        call_args = mock_dependencies[
            "command_handler"
        ].handle_create_negotiation_session.call_args[0][0]
        assert call_args.max_parties == 10  # Default
        assert call_args.session_timeout_hours == 72  # Default
        assert call_args.auto_advance_phases is True  # Default
        assert call_args.require_unanimous_agreement is False  # Default

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_party_to_negotiation_success(
        self, mock_dependencies, sample_negotiation_party
    ):
        """Test successful party addition to negotiation session."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        party_id = uuid4()
        mock_result = {
            "session_id": session_id,
            "party_id": party_id,
            "party_name": "Test Party",
            "party_role": "buyer",
            "compatibility_score": 0.85,
            "total_parties": 3,
            "events": ["party_added"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_add_party_to_session.return_value = mock_result

        result = await service.add_party_to_negotiation(
            session_id=session_id,
            party=sample_negotiation_party,
            initiated_by=uuid4(),
            validate_compatibility=True,
        )

        # Verify command was handled
        mock_dependencies[
            "command_handler"
        ].handle_add_party_to_session.assert_called_once()
        call_args = mock_dependencies[
            "command_handler"
        ].handle_add_party_to_session.call_args[0][0]
        assert call_args.session_id == session_id
        assert call_args.party is sample_negotiation_party
        assert call_args.validate_compatibility is True

        # Verify result structure
        assert result["operation"] == "add_party_to_negotiation"
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert result["party_added"]["party_id"] == party_id
        assert result["party_added"]["party_name"] == "Test Party"
        assert result["party_added"]["compatibility_score"] == 0.85
        assert result["session_status"]["total_parties"] == 3
        assert result["session_status"]["can_start"] is True  # >= 2 parties

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_party_insufficient_parties(
        self, mock_dependencies, sample_negotiation_party
    ):
        """Test party addition when insufficient parties for negotiation start."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_result = {
            "session_id": session_id,
            "party_id": uuid4(),
            "party_name": "First Party",
            "party_role": "buyer",
            "compatibility_score": 0.90,
            "total_parties": 1,  # Only one party
            "events": ["party_added"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_add_party_to_session.return_value = mock_result

        result = await service.add_party_to_negotiation(
            session_id=session_id, party=sample_negotiation_party, initiated_by=uuid4()
        )

        assert result["session_status"]["can_start"] is False  # < 2 parties

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_advance_negotiation_phase_success(self, mock_dependencies):
        """Test successful negotiation phase advancement."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_result = {
            "session_id": session_id,
            "from_phase": "initiation",
            "to_phase": "preparation",
            "forced": False,
            "advancement_reason": "sufficient_parties_joined",
            "events": ["phase_advanced"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_advance_negotiation_phase.return_value = mock_result

        result = await service.advance_negotiation_phase(
            session_id=session_id,
            target_phase=NegotiationPhase.PREPARATION,
            initiated_by=uuid4(),
            force_advancement=False,
        )

        # Verify command was handled
        mock_dependencies[
            "command_handler"
        ].handle_advance_negotiation_phase.assert_called_once()
        call_args = mock_dependencies[
            "command_handler"
        ].handle_advance_negotiation_phase.call_args[0][0]
        assert call_args.session_id == session_id
        assert call_args.target_phase == NegotiationPhase.PREPARATION
        assert call_args.force_advancement is False

        # Verify result
        assert result["operation"] == "advance_negotiation_phase"
        assert result["success"] is True
        assert result["phase_transition"]["from_phase"] == "initiation"
        assert result["phase_transition"]["to_phase"] == "preparation"
        assert result["phase_transition"]["forced"] is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_advance_negotiation_phase_forced(self, mock_dependencies):
        """Test forced negotiation phase advancement."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_result = {
            "session_id": session_id,
            "from_phase": "opening",
            "to_phase": "closing",
            "forced": True,
            "advancement_reason": "administrative_override",
            "events": ["phase_forced_advanced"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_advance_negotiation_phase.return_value = mock_result

        result = await service.advance_negotiation_phase(
            session_id=session_id,
            target_phase=NegotiationPhase.CLOSING,
            initiated_by=uuid4(),
            force_advancement=True,
        )

        assert result["phase_transition"]["forced"] is True


class TestProposalOperations:
    """Test suite for proposal submission and response operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)
        mock_command_handler = AsyncMock(spec=InteractionCommandHandler)

        return {
            "repository": mock_repository,
            "negotiation_service": mock_negotiation_service,
            "command_handler": mock_command_handler,
        }

    @pytest.fixture
    def sample_proposal_terms(self):
        """Create sample proposal terms for testing."""
        proposal_terms = Mock(spec=ProposalTerms)
        proposal_terms.proposal_id = uuid4()
        proposal_terms.is_expired = False
        return proposal_terms

    @pytest.fixture
    def sample_proposal_response(self):
        """Create sample proposal response for testing."""
        response = Mock(spec=ProposalResponse)
        response.is_expired.return_value = False
        return response

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_submit_proposal_success(
        self, mock_dependencies, sample_proposal_terms
    ):
        """Test successful proposal submission."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        # Mock analysis result
        mock_analysis_result = {
            "analysis_result": {
                "overall_viability_score": 0.78,
                "acceptance_probability": 0.65,
                "risk_factors": ["timeline_aggressive"],
                "success_factors": ["price_competitive"],
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_analyze_proposal_viability.return_value = mock_analysis_result

        # Mock submission result
        mock_submission_result = {
            "session_id": session_id,
            "proposal_id": sample_proposal_terms.proposal_id,
            "proposal_title": "Test Proposal",
            "proposal_type": "business_terms",
            "terms_count": 5,
            "current_phase": "bargaining",
            "submitted_by": uuid4(),
            "events": ["proposal_submitted"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_submit_proposal.return_value = mock_submission_result

        result = await service.submit_proposal(
            session_id=session_id,
            proposal=sample_proposal_terms,
            submitted_by=uuid4(),
            submission_notes="Initial offer",
        )

        # Verify both analysis and submission were called
        mock_dependencies[
            "command_handler"
        ].handle_analyze_proposal_viability.assert_called_once()
        mock_dependencies["command_handler"].handle_submit_proposal.assert_called_once()

        # Verify result structure
        assert result["operation"] == "submit_proposal"
        assert result["success"] is True
        assert result["proposal_submitted"]["viability_score"] == 0.78
        assert result["proposal_submitted"]["acceptance_probability"] == 0.65
        assert (
            result["pre_submission_analysis"] == mock_analysis_result["analysis_result"]
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_submit_proposal_response_success(
        self, mock_dependencies, sample_proposal_response
    ):
        """Test successful proposal response submission."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        response_id = uuid4()
        proposal_id = uuid4()

        # Mock response submission result
        mock_response_result = {
            "session_id": session_id,
            "response_id": response_id,
            "proposal_id": proposal_id,
            "responding_party_id": uuid4(),
            "overall_response": "partial_accept",
            "acceptance_percentage": 0.75,
            "requires_follow_up": True,
            "current_phase": "bargaining",
            "events": ["response_submitted"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_submit_proposal_response.return_value = mock_response_result

        # Mock momentum calculation result
        mock_momentum_result = {
            "momentum_analysis": {
                "direction": "positive",
                "momentum_score": 0.68,
                "trend": "improving",
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        result = await service.submit_proposal_response(
            session_id=session_id,
            response=sample_proposal_response,
            submitted_by=uuid4(),
        )

        # Verify both response and momentum calculation were called
        mock_dependencies[
            "command_handler"
        ].handle_submit_proposal_response.assert_called_once()
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.assert_called_once()

        # Verify result structure
        assert result["operation"] == "submit_proposal_response"
        assert result["success"] is True
        assert result["response_submitted"]["response_id"] == response_id
        assert result["response_submitted"]["overall_response"] == "partial_accept"
        assert result["response_submitted"]["acceptance_percentage"] == 0.75
        assert (
            result["session_status"]["momentum"]
            == mock_momentum_result["momentum_analysis"]
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_submit_proposal_response_negative_momentum(
        self, mock_dependencies, sample_proposal_response
    ):
        """Test proposal response with negative momentum."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        mock_response_result = {
            "session_id": session_id,
            "response_id": uuid4(),
            "proposal_id": uuid4(),
            "responding_party_id": uuid4(),
            "overall_response": "reject",
            "acceptance_percentage": 0.10,
            "requires_follow_up": True,
            "current_phase": "bargaining",
            "events": ["response_rejected"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_submit_proposal_response.return_value = mock_response_result

        # Mock negative momentum
        mock_momentum_result = {
            "momentum_analysis": {
                "direction": "negative",
                "momentum_score": 0.25,
                "trend": "declining",
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        result = await service.submit_proposal_response(
            session_id=session_id,
            response=sample_proposal_response,
            submitted_by=uuid4(),
        )

        assert result["session_status"]["momentum"]["direction"] == "negative"
        assert result["session_status"]["momentum"]["momentum_score"] == 0.25


class TestNegotiationCompletion:
    """Test suite for negotiation completion operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)
        mock_command_handler = AsyncMock(spec=InteractionCommandHandler)

        return {
            "repository": mock_repository,
            "negotiation_service": mock_negotiation_service,
            "command_handler": mock_command_handler,
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_complete_negotiation_success(self, mock_dependencies):
        """Test successful negotiation completion."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        # Mock final momentum analysis
        mock_momentum_result = {
            "momentum_analysis": {
                "direction": "positive",
                "momentum_score": 0.85,
                "final_assessment": "successful_completion",
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        # Mock final conflicts analysis
        mock_conflicts_result = {
            "conflicts_detected": [{"severity": "low", "resolved": True}]
        }
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.return_value = mock_conflicts_result

        # Mock termination result
        mock_termination_result = {
            "session_id": session_id,
            "outcome": "agreement_reached",
            "termination_reason": "mutual_agreement",
            "terminated_at": datetime.now(timezone.utc),
            "duration": 3600 * 24 * 5,  # 5 days in seconds
            "events": ["negotiation_completed"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_terminate_negotiation_session.return_value = mock_termination_result

        result = await service.complete_negotiation(
            session_id=session_id,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            initiated_by=uuid4(),
            completion_notes="Successfully reached agreement",
        )

        # Verify all three operations were called
        assert (
            mock_dependencies[
                "command_handler"
            ].handle_calculate_negotiation_momentum.call_count
            == 1
        )
        assert (
            mock_dependencies[
                "command_handler"
            ].handle_detect_negotiation_conflicts.call_count
            == 1
        )
        assert (
            mock_dependencies[
                "command_handler"
            ].handle_terminate_negotiation_session.call_count
            == 1
        )

        # Verify result structure
        assert result["operation"] == "complete_negotiation"
        assert result["success"] is True
        assert result["completion_summary"]["outcome"] == "agreement_reached"
        assert result["completion_summary"]["termination_reason"] == "mutual_agreement"
        assert (
            result["completion_summary"]["completion_notes"]
            == "Successfully reached agreement"
        )
        assert (
            result["final_analysis"]["momentum"]
            == mock_momentum_result["momentum_analysis"]
        )
        assert (
            result["final_analysis"]["conflicts"]
            == mock_conflicts_result["conflicts_detected"]
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_complete_negotiation_with_conflicts(self, mock_dependencies):
        """Test negotiation completion with unresolved conflicts."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        # Mock momentum with declining trend
        mock_momentum_result = {
            "momentum_analysis": {
                "direction": "negative",
                "momentum_score": 0.30,
                "final_assessment": "forced_completion",
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        # Mock unresolved conflicts
        mock_conflicts_result = {
            "conflicts_detected": [
                {"severity": "high", "resolved": False, "type": "pricing_dispute"},
                {
                    "severity": "medium",
                    "resolved": False,
                    "type": "timeline_disagreement",
                },
                {"severity": "low", "resolved": True, "type": "documentation_format"},
            ]
        }
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.return_value = mock_conflicts_result

        # Mock termination with stalemate
        mock_termination_result = {
            "session_id": session_id,
            "outcome": "stalemate",
            "termination_reason": "irreconcilable_differences",
            "terminated_at": datetime.now(timezone.utc),
            "duration": 3600 * 24 * 10,  # 10 days in seconds
            "events": ["negotiation_terminated_stalemate"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_terminate_negotiation_session.return_value = mock_termination_result

        result = await service.complete_negotiation(
            session_id=session_id,
            outcome=NegotiationOutcome.STALEMATE,
            termination_reason=TerminationReason.IRRECONCILABLE_DIFFERENCES,
            initiated_by=uuid4(),
        )

        assert result["completion_summary"]["outcome"] == "stalemate"
        assert len(result["final_analysis"]["conflicts"]) == 3
        assert result["final_analysis"]["momentum"]["direction"] == "negative"


class TestAnalyticalOperations:
    """Test suite for analytical and insights operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)
        mock_command_handler = AsyncMock(spec=InteractionCommandHandler)

        return {
            "repository": mock_repository,
            "negotiation_service": mock_negotiation_service,
            "command_handler": mock_command_handler,
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_negotiation_insights_comprehensive(self, mock_dependencies):
        """Test comprehensive negotiation insights analysis."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        # Mock compatibility assessment
        mock_compatibility_result = {
            "overall_compatibility": 0.75,
            "party_compatibility_matrix": {},
            "compatibility_factors": ["shared_interests", "complementary_skills"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_assess_party_compatibility.return_value = mock_compatibility_result

        # Mock strategy recommendation
        mock_strategy_result = {
            "strategy_recommendation": {
                "primary_strategy": "collaborative",
                "key_tactics": ["build_rapport", "find_common_ground", "create_value"],
                "risk_mitigation": ["monitor_momentum", "address_conflicts_early"],
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_recommend_negotiation_strategy.return_value = mock_strategy_result

        # Mock conflicts detection
        mock_conflicts_result = {
            "conflicts_detected": [
                {
                    "severity": "medium",
                    "type": "timeline_pressure",
                    "resolution_suggestions": ["extend_deadline"],
                }
            ]
        }
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.return_value = mock_conflicts_result

        # Mock momentum analysis
        mock_momentum_result = {
            "momentum_analysis": {
                "direction": "positive",
                "momentum_score": 0.72,
                "trend": "stable",
                "predictions": {"success_probability": 0.78},
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        result = await service.get_negotiation_insights(
            session_id=session_id, initiated_by=uuid4(), analysis_depth="comprehensive"
        )

        # Verify all four analysis operations were called
        mock_dependencies[
            "command_handler"
        ].handle_assess_party_compatibility.assert_called_once()
        mock_dependencies[
            "command_handler"
        ].handle_recommend_negotiation_strategy.assert_called_once()
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.assert_called_once()
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.assert_called_once()

        # Verify result structure
        assert result["operation"] == "get_negotiation_insights"
        assert result["success"] is True
        assert result["analysis_depth"] == "comprehensive"
        assert result["insights"]["party_compatibility"] == mock_compatibility_result
        assert (
            result["insights"]["recommended_strategy"]
            == mock_strategy_result["strategy_recommendation"]
        )
        assert (
            result["insights"]["detected_conflicts"]
            == mock_conflicts_result["conflicts_detected"]
        )
        assert (
            result["insights"]["momentum_analysis"]
            == mock_momentum_result["momentum_analysis"]
        )

        # Verify overall assessment
        assert result["overall_assessment"]["compatibility_score"] == 0.75
        assert result["overall_assessment"]["conflict_level"] == 1
        assert result["overall_assessment"]["momentum_direction"] == "positive"
        assert "success_probability" in result["overall_assessment"]

        # Verify recommendations are included
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_negotiation_insights_low_compatibility(self, mock_dependencies):
        """Test insights analysis with low party compatibility."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        # Mock low compatibility
        mock_compatibility_result = {
            "overall_compatibility": 0.25,  # Low compatibility
            "party_compatibility_matrix": {},
            "compatibility_issues": ["conflicting_goals", "communication_barriers"],
        }
        mock_dependencies[
            "command_handler"
        ].handle_assess_party_compatibility.return_value = mock_compatibility_result

        # Mock defensive strategy
        mock_strategy_result = {
            "strategy_recommendation": {
                "primary_strategy": "defensive",
                "key_tactics": ["protect_interests", "clear_boundaries"],
                "mediation_recommended": True,
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_recommend_negotiation_strategy.return_value = mock_strategy_result

        # Mock high conflicts
        mock_conflicts_result = {
            "conflicts_detected": [
                {"severity": "high", "type": "fundamental_disagreement"},
                {"severity": "high", "type": "trust_issues"},
                {"severity": "medium", "type": "process_disputes"},
            ]
        }
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.return_value = mock_conflicts_result

        # Mock negative momentum
        mock_momentum_result = {
            "momentum_analysis": {
                "direction": "negative",
                "momentum_score": 0.20,
                "trend": "declining",
            }
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        result = await service.get_negotiation_insights(
            session_id=session_id, initiated_by=uuid4()
        )

        # Verify overall assessment reflects poor conditions
        assert result["overall_assessment"]["compatibility_score"] == 0.25
        assert (
            result["overall_assessment"]["conflict_level"] == 3
        )  # High number of conflicts
        assert result["overall_assessment"]["momentum_direction"] == "negative"

        # Success probability should be low due to poor conditions
        success_prob = result["overall_assessment"]["success_probability"]
        assert (
            success_prob < 50
        )  # Should be low due to poor compatibility, high conflicts, low momentum


class TestProposalOptimization:
    """Test suite for proposal optimization operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        mock_repository = AsyncMock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)
        mock_command_handler = AsyncMock(spec=InteractionCommandHandler)

        return {
            "repository": mock_repository,
            "negotiation_service": mock_negotiation_service,
            "command_handler": mock_command_handler,
        }

    @pytest.fixture
    def mock_negotiation_session(self):
        """Create mock negotiation session for testing."""
        session = Mock(spec=NegotiationSession)
        session.active_proposals = {uuid4(): Mock(), uuid4(): Mock(), uuid4(): Mock()}
        return session

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_optimize_active_proposals_success(
        self, mock_dependencies, mock_negotiation_session
    ):
        """Test successful proposal optimization."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_dependencies[
            "repository"
        ].get_by_id.return_value = mock_negotiation_session

        # Mock analysis results for each proposal
        proposal_ids = list(mock_negotiation_session.active_proposals.keys())
        analysis_results = []

        for i, proposal_id in enumerate(proposal_ids):
            mock_result = {
                "analysis_result": {
                    "overall_viability_score": 0.6 + (i * 0.1),  # Varying scores
                    "optimization_suggestions": [
                        f"suggestion_{i}_1",
                        f"suggestion_{i}_2",
                    ],
                    "risk_factors": [f"risk_{i}"],
                    "success_factors": [f"success_{i}"],
                }
            }
            analysis_results.append(mock_result)

        mock_dependencies[
            "command_handler"
        ].handle_analyze_proposal_viability.side_effect = analysis_results

        result = await service.optimize_active_proposals(
            session_id=session_id,
            initiated_by=uuid4(),
            optimization_target="maximize_acceptance",
        )

        # Verify session was retrieved
        mock_dependencies["repository"].get_by_id.assert_called_once_with(
            InteractionId(session_id)
        )

        # Verify analysis was called for each proposal
        assert (
            mock_dependencies[
                "command_handler"
            ].handle_analyze_proposal_viability.call_count
            == 3
        )

        # Verify result structure
        assert result["operation"] == "optimize_active_proposals"
        assert result["success"] is True
        assert result["optimization_target"] == "maximize_acceptance"
        assert result["proposals_analyzed"] == 3
        assert len(result["proposal_optimizations"]) == 3

        # Verify average viability calculation
        expected_avg = (0.6 + 0.7 + 0.8) / 3
        assert result["average_viability"] == expected_avg

        # Verify optimization recommendations are included
        assert "overall_recommendations" in result
        assert isinstance(result["overall_recommendations"], list)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_optimize_active_proposals_session_not_found(self, mock_dependencies):
        """Test proposal optimization when session is not found."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )

        session_id = uuid4()
        mock_dependencies["repository"].get_by_id.return_value = None

        with pytest.raises(ValueError, match=f"Session {session_id} not found"):
            await service.optimize_active_proposals(
                session_id=session_id, initiated_by=uuid4()
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_optimize_active_proposals_no_proposals(self, mock_dependencies):
        """Test proposal optimization with no active proposals."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()

        # Mock session with no active proposals
        empty_session = Mock(spec=NegotiationSession)
        empty_session.active_proposals = {}
        mock_dependencies["repository"].get_by_id.return_value = empty_session

        result = await service.optimize_active_proposals(
            session_id=session_id, initiated_by=uuid4()
        )

        # Verify no analysis was performed
        mock_dependencies[
            "command_handler"
        ].handle_analyze_proposal_viability.assert_not_called()

        # Verify result indicates no proposals
        assert result["proposals_analyzed"] == 0
        assert result["average_viability"] == 0
        assert len(result["proposal_optimizations"]) == 0


class TestSessionHealthMonitoring:
    """Test suite for session health monitoring operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        mock_repository = AsyncMock(spec=NegotiationSessionRepository)
        mock_negotiation_service = Mock(spec=NegotiationService)
        mock_command_handler = AsyncMock(spec=InteractionCommandHandler)

        return {
            "repository": mock_repository,
            "negotiation_service": mock_negotiation_service,
            "command_handler": mock_command_handler,
        }

    @pytest.fixture
    def mock_healthy_session(self):
        """Create mock healthy negotiation session."""
        session = Mock(spec=NegotiationSession)
        session.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        session.parties = [Mock(), Mock(), Mock()]  # 3 parties
        session.active_proposals = {uuid4(): Mock(), uuid4(): Mock()}  # 2 proposals
        session.total_responses = 15
        session.status = Mock()
        session.status.phase = NegotiationPhase.BARGAINING
        session.status.time_since_last_activity = 3600  # 1 hour ago
        session.is_timeout_approaching.return_value = False
        return session

    @pytest.fixture
    def mock_unhealthy_session(self):
        """Create mock unhealthy negotiation session."""
        session = Mock(spec=NegotiationSession)
        session.created_at = datetime.now(timezone.utc) - timedelta(
            days=7
        )  # Old session
        session.parties = [Mock()]  # Only 1 party
        session.active_proposals = {}  # No proposals
        session.total_responses = 2
        session.status = Mock()
        session.status.phase = NegotiationPhase.BARGAINING
        session.status.time_since_last_activity = (
            3600 * 6
        )  # 6 hours ago (exceeds threshold)
        session.is_timeout_approaching.return_value = True  # Approaching timeout
        return session

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_monitor_session_health_healthy_session(
        self, mock_dependencies, mock_healthy_session
    ):
        """Test health monitoring for healthy session."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_dependencies["repository"].get_by_id.return_value = mock_healthy_session

        # Mock low conflicts
        mock_conflicts_result = {
            "conflicts_detected": [{"severity": "low", "resolved": True}]
        }
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.return_value = mock_conflicts_result

        # Mock positive momentum
        mock_momentum_result = {
            "momentum_analysis": {"direction": "positive", "momentum_score": 0.75}
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        result = await service.monitor_session_health(
            session_id=session_id, initiated_by=uuid4()
        )

        # Verify session was retrieved
        mock_dependencies["repository"].get_by_id.assert_called_once_with(
            InteractionId(session_id)
        )

        # Verify result structure
        assert result["operation"] == "monitor_session_health"
        assert result["success"] is True

        # Should have good health score (few/no alerts for healthy session)
        health_score = result["health_summary"]["health_score"]
        assert health_score > 70  # Should be reasonably high

        # Should have minimal alerts
        active_alerts = result["health_summary"]["active_alerts"]
        assert len(active_alerts) <= 1  # Healthy session should have few alerts

        # Verify key metrics
        assert result["key_metrics"]["total_parties"] == 3
        assert result["key_metrics"]["active_proposals"] == 2
        assert result["key_metrics"]["total_responses"] == 15
        assert result["key_metrics"]["current_phase"] == "bargaining"
        assert result["key_metrics"]["momentum_direction"] == "positive"
        assert result["key_metrics"]["conflict_count"] == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_monitor_session_health_unhealthy_session(
        self, mock_dependencies, mock_unhealthy_session
    ):
        """Test health monitoring for unhealthy session."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )
        service.command_handler = mock_dependencies["command_handler"]

        session_id = uuid4()
        mock_dependencies["repository"].get_by_id.return_value = mock_unhealthy_session

        # Mock many conflicts
        mock_conflicts_result = {
            "conflicts_detected": [
                {"severity": "high", "resolved": False},
                {"severity": "high", "resolved": False},
                {"severity": "medium", "resolved": False},
                {"severity": "low", "resolved": False},
            ]
        }
        mock_dependencies[
            "command_handler"
        ].handle_detect_negotiation_conflicts.return_value = mock_conflicts_result

        # Mock negative momentum
        mock_momentum_result = {
            "momentum_analysis": {"direction": "negative", "momentum_score": 0.25}
        }
        mock_dependencies[
            "command_handler"
        ].handle_calculate_negotiation_momentum.return_value = mock_momentum_result

        result = await service.monitor_session_health(
            session_id=session_id, initiated_by=uuid4()
        )

        # Should have poor health score
        health_score = result["health_summary"]["health_score"]
        assert health_score < 50  # Should be low due to multiple issues

        # Should have multiple alerts
        active_alerts = result["health_summary"]["active_alerts"]
        alert_types = [alert["type"] for alert in active_alerts]

        # Should have timeout warning (session.is_timeout_approaching returns True)
        assert "timeout_warning" in alert_types

        # Should have inactivity warning (6 hours > 4 hour threshold)
        assert "inactivity_warning" in alert_types

        # Should have conflict warning (4 conflicts > 3 threshold)
        assert "conflict_warning" in alert_types

        # Should have momentum warning (negative direction)
        assert "momentum_warning" in alert_types

        # Verify key metrics reflect unhealthy state
        assert result["key_metrics"]["total_parties"] == 1
        assert result["key_metrics"]["active_proposals"] == 0
        assert result["key_metrics"]["momentum_direction"] == "negative"
        assert result["key_metrics"]["conflict_count"] == 4

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_monitor_session_health_session_not_found(self, mock_dependencies):
        """Test health monitoring when session is not found."""
        service = InteractionApplicationService(
            session_repository=mock_dependencies["repository"],
            negotiation_service=mock_dependencies["negotiation_service"],
        )

        session_id = uuid4()
        mock_dependencies["repository"].get_by_id.return_value = None

        with pytest.raises(ValueError, match=f"Session {session_id} not found"):
            await service.monitor_session_health(
                session_id=session_id, initiated_by=uuid4()
            )


class TestPrivateHelperMethods:
    """Test suite for private helper methods in InteractionApplicationService."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_calculate_success_probability(self):
        """Test success probability calculation."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        service = InteractionApplicationService(session_repository=mock_repository)

        # Test high success scenario
        high_success = service._calculate_success_probability(
            compatibility_score=90.0,  # High compatibility
            conflict_count=1,  # Few conflicts
            momentum_score=85.0,  # High momentum
        )
        assert high_success > 80.0
        assert high_success <= 100.0

        # Test low success scenario
        low_success = service._calculate_success_probability(
            compatibility_score=20.0,  # Low compatibility
            conflict_count=8,  # Many conflicts
            momentum_score=15.0,  # Low momentum
        )
        assert low_success < 30.0
        assert low_success >= 0.0

        # Test boundary conditions
        max_success = service._calculate_success_probability(100.0, 0, 100.0)
        assert max_success == 100.0

        # Test with very high conflict count
        min_success = service._calculate_success_probability(0.0, 20, 0.0)
        assert min_success == 0.0

    @pytest.mark.unit
    def test_generate_recommendations(self):
        """Test recommendation generation logic."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        service = InteractionApplicationService(session_repository=mock_repository)

        # Mock analysis results
        compatibility_result = {"overall_compatibility": 45.0}  # Below 50 threshold

        strategy_result = {
            "strategy_recommendation": {"key_tactics": ["tactic1", "tactic2"]}
        }

        conflicts_result = {
            "conflicts_detected": [
                {
                    "severity": "high",
                    "resolution_suggestions": ["resolve_high_1", "resolve_high_2"],
                },
                {"severity": "low", "resolution_suggestions": ["resolve_low_1"]},
            ]
        }

        momentum_result = {
            "momentum_analysis": {
                "recommendations": ["momentum_rec_1", "momentum_rec_2"]
            }
        }

        recommendations = service._generate_recommendations(
            compatibility_result, strategy_result, conflicts_result, momentum_result
        )

        # Should include compatibility recommendation
        assert any("mediation" in rec.lower() for rec in recommendations)

        # Should include strategy tactics
        assert "tactic1" in recommendations
        assert "tactic2" in recommendations

        # Should include high severity conflict resolutions
        assert "resolve_high_1" in recommendations
        assert "resolve_high_2" in recommendations

        # Should include momentum recommendations
        assert "momentum_rec_1" in recommendations
        assert "momentum_rec_2" in recommendations

        # Should limit to 10 recommendations
        assert len(recommendations) <= 10

        # Should remove duplicates
        assert len(recommendations) == len(set(recommendations))

    @pytest.mark.unit
    def test_calculate_health_score(self):
        """Test health score calculation."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        service = InteractionApplicationService(session_repository=mock_repository)

        # Mock healthy session
        healthy_session = Mock()
        healthy_session.status.time_since_last_activity = 3600  # 1 hour
        healthy_session.status.phase = NegotiationPhase.BARGAINING
        healthy_session.active_proposals = {
            uuid4(): Mock(),
            uuid4(): Mock(),
        }  # Has proposals

        healthy_score = service._calculate_health_score(
            session=healthy_session,
            conflicts=[],  # No conflicts
            momentum_analysis={"momentum_score": 85},  # High momentum
        )

        # Should have high health score
        assert healthy_score >= 100.0  # Perfect conditions get bonus

        # Mock unhealthy session
        unhealthy_session = Mock()
        unhealthy_session.status.time_since_last_activity = (
            3600 * 25
        )  # 25 hours (> 24h threshold)
        unhealthy_session.status.phase = NegotiationPhase.BARGAINING
        unhealthy_session.active_proposals = {}  # No proposals in bargaining phase

        unhealthy_score = service._calculate_health_score(
            session=unhealthy_session,
            conflicts=[
                {"severity": "critical"},
                {"severity": "high"},
                {"severity": "medium"},
                {"severity": "low"},
            ],
            momentum_analysis={"momentum_score": 20},  # Low momentum
        )

        # Should have low health score
        assert unhealthy_score < 50.0
        assert unhealthy_score >= 0.0

    @pytest.mark.unit
    def test_get_health_status(self):
        """Test health status description conversion."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        service = InteractionApplicationService(session_repository=mock_repository)

        # Test all health status levels
        assert service._get_health_status(95.0) == "excellent"
        assert service._get_health_status(75.0) == "good"
        assert service._get_health_status(55.0) == "fair"
        assert service._get_health_status(40.0) == "poor"
        assert service._get_health_status(20.0) == "critical"

        # Test boundary conditions
        assert service._get_health_status(80.0) == "excellent"
        assert service._get_health_status(65.0) == "good"
        assert service._get_health_status(50.0) == "fair"
        assert service._get_health_status(35.0) == "poor"
        assert service._get_health_status(0.0) == "critical"

    @pytest.mark.unit
    def test_generate_health_recommendations(self):
        """Test health recommendation generation."""
        mock_repository = Mock(spec=NegotiationSessionRepository)
        service = InteractionApplicationService(session_repository=mock_repository)

        # Test with various alert types
        health_alerts = [
            {"type": "timeout_warning", "severity": "high"},
            {"type": "inactivity_warning", "severity": "medium"},
            {"type": "conflict_warning", "severity": "high"},
            {"type": "momentum_warning", "severity": "medium"},
        ]

        recommendations = service._generate_health_recommendations(
            health_score=45.0, health_alerts=health_alerts  # Poor health
        )

        # Should address each alert type
        assert any(
            "timeline" in rec.lower() or "extend" in rec.lower()
            for rec in recommendations
        )
        assert any(
            "follow-up" in rec.lower() or "meeting" in rec.lower()
            for rec in recommendations
        )
        assert any("conflict resolution" in rec.lower() for rec in recommendations)
        assert any(
            "momentum" in rec.lower() or "approach" in rec.lower()
            for rec in recommendations
        )

        # Should include general recommendations for poor health
        assert any("mediator" in rec.lower() for rec in recommendations)

        # Should limit recommendations
        assert len(recommendations) <= 8
