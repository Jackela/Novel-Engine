#!/usr/bin/env python3
"""
Tests for InteractionApplicationService (Interaction Engine).

This module contains comprehensive tests for the interaction application service
including session management, proposal handling, and negotiation operations.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from src.contexts.interactions.application.services.interaction_application_service import (
    InteractionApplicationService,
)
from src.contexts.interactions.domain.aggregates.negotiation_session import (
    NegotiationSession,
)
from src.contexts.interactions.domain.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from src.contexts.interactions.domain.services.negotiation_service import (
    NegotiationService,
)
from src.contexts.interactions.domain.value_objects import (
    AuthorityLevel,
    CommunicationPreference,
    InteractionId,
    NegotiationCapability,
    NegotiationOutcome,
    NegotiationParty,
    NegotiationPhase,
    NegotiationStatus,
    NegotiationStyle,
    PartyPreferences,
    PartyRole,
    ProposalPriority,
    ProposalResponse,
    ProposalTerms,
    ProposalType,
    ResponseType,
    TermCondition,
    TermResponse,
    TermType,
    TerminationReason,
)


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return AsyncMock(spec=NegotiationSessionRepository)


@pytest.fixture
def mock_negotiation_service():
    """Create a mock negotiation service."""
    return MagicMock(spec=NegotiationService)


@pytest.fixture
def interaction_service(mock_repository, mock_negotiation_service):
    """Create an InteractionApplicationService instance."""
    return InteractionApplicationService(
        session_repository=mock_repository,
        negotiation_service=mock_negotiation_service,
    )


@pytest.fixture
def sample_party():
    """Create a sample negotiation party."""
    return NegotiationParty(
        party_id=uuid4(),
        entity_id=uuid4(),
        party_name="Test Party",
        role=PartyRole.PRIMARY_NEGOTIATOR,
        authority_level=AuthorityLevel.FULL_AUTHORITY,
        capabilities=[
            NegotiationCapability(
                capability_name="Diplomacy",
                proficiency_level=Decimal("80"),
                confidence_modifier=Decimal("5"),
                applicable_domains={"diplomacy", "trade"},
            )
        ],
        preferences=PartyPreferences(
            negotiation_style=NegotiationStyle.COLLABORATIVE,
            communication_preference=CommunicationPreference.DIRECT,
            risk_tolerance=Decimal("50"),
            time_pressure_sensitivity=Decimal("30"),
        ),
    )


@pytest.fixture
def sample_proposal():
    """Create a sample proposal."""
    return ProposalTerms.create(
        proposal_type=ProposalType.TRADE_OFFER,
        title="Test Trade Proposal",
        summary="A test proposal for trading resources",
        terms=[
            TermCondition(
                term_id="term_1",
                term_type=TermType.RESOURCE_QUANTITY,
                description="Offer 100 units of wood",
                value=100,
                priority=ProposalPriority.HIGH,
            )
        ],
    )


@pytest.fixture
def sample_session():
    """Create a sample negotiation session."""
    return NegotiationSession.create(
        session_name="Test Session",
        session_type="trade",
        created_by=uuid4(),
    )


class TestInteractionServiceInitialization:
    """Test suite for service initialization."""

    def test_initialization_with_repository_and_service(
        self, mock_repository, mock_negotiation_service
    ):
        """Test initialization with explicit repository and service."""
        service = InteractionApplicationService(
            session_repository=mock_repository,
            negotiation_service=mock_negotiation_service,
        )
        
        assert service.session_repository == mock_repository
        assert service.negotiation_service == mock_negotiation_service
        assert service.command_handler is not None

    def test_initialization_with_default_service(self, mock_repository):
        """Test initialization with default negotiation service."""
        service = InteractionApplicationService(
            session_repository=mock_repository,
        )
        
        assert service.negotiation_service is not None
        assert isinstance(service.negotiation_service, NegotiationService)


class TestCreateNegotiationSession:
    """Test suite for creating negotiation sessions."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, interaction_service):
        """Test successful session creation."""
        interaction_service.command_handler.handle_create_negotiation_session = AsyncMock(
            return_value={
                "session_id": str(uuid4()),
                "session_name": "Test Session",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "initiation",
                "max_parties": 10,
                "events": [],
            }
        )
        
        result = await interaction_service.create_negotiation_session(
            session_name="Test Session",
            session_type="trade",
            created_by=uuid4(),
        )
        
        assert result["operation"] == "create_negotiation_session"
        assert result["success"] is True
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_create_session_with_all_options(self, interaction_service):
        """Test session creation with all optional parameters."""
        interaction_service.command_handler.handle_create_negotiation_session = AsyncMock(
            return_value={
                "session_id": str(uuid4()),
                "session_name": "Complex Session",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "initiation",
                "max_parties": 5,
                "events": [],
            }
        )
        
        result = await interaction_service.create_negotiation_session(
            session_name="Complex Session",
            session_type="diplomatic",
            created_by=uuid4(),
            negotiation_domain="diplomacy",
            max_parties=5,
            session_timeout_hours=48,
            auto_advance_phases=False,
            require_unanimous_agreement=True,
            allow_partial_agreements=False,
            session_context={"key": "value"},
            priority_level="high",
            confidentiality_level="secret",
        )
        
        assert result["success"] is True


class TestAddPartyToNegotiation:
    """Test suite for adding parties to negotiations."""

    @pytest.mark.asyncio
    async def test_add_party_success(
        self, interaction_service, sample_party
    ):
        """Test successful party addition."""
        session_id = uuid4()
        
        interaction_service.command_handler.handle_add_party_to_session = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "party_id": str(sample_party.party_id),
                "party_name": sample_party.party_name,
                "party_role": sample_party.role.value,
                "compatibility_score": 75.0,
                "total_parties": 2,
                "events": [],
            }
        )
        
        result = await interaction_service.add_party_to_negotiation(
            session_id=session_id,
            party=sample_party,
            initiated_by=uuid4(),
        )
        
        assert result["operation"] == "add_party_to_negotiation"
        assert result["success"] is True
        assert result["party_added"]["party_id"] == str(sample_party.party_id)

    @pytest.mark.asyncio
    async def test_add_party_without_compatibility_check(
        self, interaction_service, sample_party
    ):
        """Test adding party without compatibility validation."""
        session_id = uuid4()
        
        interaction_service.command_handler.handle_add_party_to_session = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "party_id": str(sample_party.party_id),
                "party_name": sample_party.party_name,
                "party_role": sample_party.role.value,
                "compatibility_score": None,
                "total_parties": 3,
                "events": [],
            }
        )
        
        result = await interaction_service.add_party_to_negotiation(
            session_id=session_id,
            party=sample_party,
            initiated_by=uuid4(),
            validate_compatibility=False,
        )
        
        assert result["success"] is True


class TestSubmitProposal:
    """Test suite for submitting proposals."""

    @pytest.mark.asyncio
    async def test_submit_proposal_success(
        self, interaction_service, sample_proposal
    ):
        """Test successful proposal submission."""
        session_id = uuid4()
        submitted_by = uuid4()
        
        interaction_service.command_handler.handle_analyze_proposal_viability = AsyncMock(
            return_value={
                "analysis_result": {
                    "overall_viability_score": Decimal("75"),
                    "acceptance_probability": Decimal("80"),
                }
            }
        )
        interaction_service.command_handler.handle_submit_proposal = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "proposal_id": str(sample_proposal.proposal_id),
                "proposal_title": sample_proposal.title,
                "proposal_type": sample_proposal.proposal_type.value,
                "terms_count": len(sample_proposal.terms),
                "current_phase": "opening",
                "submitted_by": str(submitted_by),
                "events": [],
            }
        )
        
        result = await interaction_service.submit_proposal(
            session_id=session_id,
            proposal=sample_proposal,
            submitted_by=submitted_by,
            submission_notes="Please consider this offer",
        )
        
        assert result["operation"] == "submit_proposal"
        assert result["success"] is True
        assert result["proposal_submitted"]["proposal_id"] == str(sample_proposal.proposal_id)


class TestSubmitProposalResponse:
    """Test suite for submitting proposal responses."""

    @pytest.mark.asyncio
    async def test_submit_response_success(self, interaction_service):
        """Test successful response submission."""
        session_id = uuid4()
        proposal_id = uuid4()
        responding_party_id = uuid4()
        
        response = ProposalResponse.create(
            proposal_id=proposal_id,
            responding_party_id=responding_party_id,
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(
                    term_id="term_1",
                    response_type=ResponseType.ACCEPT,
                )
            ],
        )
        
        interaction_service.command_handler.handle_submit_proposal_response = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "response_id": str(uuid4()),
                "proposal_id": str(proposal_id),
                "responding_party_id": str(responding_party_id),
                "overall_response": "accept",
                "acceptance_percentage": 100.0,
                "requires_follow_up": False,
                "current_phase": "bargaining",
                "events": [],
            }
        )
        interaction_service.command_handler.handle_calculate_negotiation_momentum = AsyncMock(
            return_value={
                "momentum_analysis": {
                    "momentum_score": Decimal("75"),
                    "direction": "positive",
                }
            }
        )
        
        result = await interaction_service.submit_proposal_response(
            session_id=session_id,
            response=response,
            submitted_by=responding_party_id,
        )
        
        assert result["operation"] == "submit_proposal_response"
        assert result["success"] is True


class TestAdvanceNegotiationPhase:
    """Test suite for advancing negotiation phases."""

    @pytest.mark.asyncio
    async def test_advance_phase_success(self, interaction_service):
        """Test successful phase advancement."""
        session_id = uuid4()
        
        interaction_service.command_handler.handle_advance_negotiation_phase = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "from_phase": "opening",
                "to_phase": "bargaining",
                "forced": False,
                "advancement_reason": "proposal_submitted",
                "events": [],
            }
        )
        
        result = await interaction_service.advance_negotiation_phase(
            session_id=session_id,
            target_phase=NegotiationPhase.BARGAINING,
            initiated_by=uuid4(),
        )
        
        assert result["operation"] == "advance_negotiation_phase"
        assert result["success"] is True
        assert result["phase_transition"]["to_phase"] == "bargaining"

    @pytest.mark.asyncio
    async def test_advance_phase_forced(self, interaction_service):
        """Test forced phase advancement."""
        session_id = uuid4()
        
        interaction_service.command_handler.handle_advance_negotiation_phase = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "from_phase": "preparation",
                "to_phase": "opening",
                "forced": True,
                "advancement_reason": "manual_override",
                "events": [],
            }
        )
        
        result = await interaction_service.advance_negotiation_phase(
            session_id=session_id,
            target_phase=NegotiationPhase.OPENING,
            initiated_by=uuid4(),
            force_advancement=True,
        )
        
        assert result["phase_transition"]["forced"] is True


class TestCompleteNegotiation:
    """Test suite for completing negotiations."""

    @pytest.mark.asyncio
    async def test_complete_negotiation_success(self, interaction_service):
        """Test successful negotiation completion."""
        session_id = uuid4()
        
        interaction_service.command_handler.handle_calculate_negotiation_momentum = AsyncMock(
            return_value={
                "momentum_analysis": {
                    "momentum_score": Decimal("85"),
                    "direction": "positive",
                }
            }
        )
        interaction_service.command_handler.handle_detect_negotiation_conflicts = AsyncMock(
            return_value={"conflicts_detected": []}
        )
        interaction_service.command_handler.handle_terminate_negotiation_session = AsyncMock(
            return_value={
                "session_id": str(session_id),
                "outcome": "agreement_reached",
                "termination_reason": "mutual_agreement",
                "terminated_at": datetime.now(timezone.utc).isoformat(),
                "duration": 3600,
                "events": [],
            }
        )
        
        result = await interaction_service.complete_negotiation(
            session_id=session_id,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            initiated_by=uuid4(),
            completion_notes="All parties reached agreement",
        )
        
        assert result["operation"] == "complete_negotiation"
        assert result["success"] is True
        assert result["completion_summary"]["outcome"] == "agreement_reached"


class TestGetNegotiationInsights:
    """Test suite for getting negotiation insights."""

    @pytest.mark.asyncio
    async def test_get_insights_comprehensive(self, interaction_service):
        """Test getting comprehensive negotiation insights."""
        session_id = uuid4()
        
        interaction_service.command_handler.handle_assess_party_compatibility = AsyncMock(
            return_value={
                "overall_compatibility": 75.0,
                "party_analysis": [],
            }
        )
        interaction_service.command_handler.handle_recommend_negotiation_strategy = AsyncMock(
            return_value={
                "strategy_recommendation": {
                    "recommended_approach": "collaborative",
                    "key_tactics": ["Listen actively"],
                }
            }
        )
        interaction_service.command_handler.handle_detect_negotiation_conflicts = AsyncMock(
            return_value={"conflicts_detected": []}
        )
        interaction_service.command_handler.handle_calculate_negotiation_momentum = AsyncMock(
            return_value={
                "momentum_analysis": {
                    "momentum_score": Decimal("70"),
                    "direction": "positive",
                }
            }
        )
        
        result = await interaction_service.get_negotiation_insights(
            session_id=session_id,
            initiated_by=uuid4(),
            analysis_depth="comprehensive",
        )
        
        assert result["operation"] == "get_negotiation_insights"
        assert result["success"] is True
        assert "insights" in result
        assert "overall_assessment" in result


class TestOptimizeActiveProposals:
    """Test suite for optimizing active proposals."""

    @pytest.mark.asyncio
    async def test_optimize_proposals_success(
        self, interaction_service, mock_repository, sample_proposal
    ):
        """Test successful proposal optimization."""
        session_id = uuid4()
        
        # Create a mock session with active proposals
        mock_session = MagicMock()
        mock_session.active_proposals = {sample_proposal.proposal_id: sample_proposal}
        mock_repository.get_by_id = AsyncMock(return_value=mock_session)
        
        interaction_service.command_handler.handle_analyze_proposal_viability = AsyncMock(
            return_value={
                "analysis_result": {
                    "overall_viability_score": Decimal("65"),
                    "optimization_suggestions": ["Consider lowering price"],
                    "risk_factors": [],
                    "success_factors": ["Good timing"],
                }
            }
        )
        
        result = await interaction_service.optimize_active_proposals(
            session_id=session_id,
            initiated_by=uuid4(),
        )
        
        assert result["operation"] == "optimize_active_proposals"
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_optimize_proposals_session_not_found(
        self, interaction_service, mock_repository
    ):
        """Test optimization with non-existent session."""
        session_id = uuid4()
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Session .* not found"):
            await interaction_service.optimize_active_proposals(
                session_id=session_id,
                initiated_by=uuid4(),
            )


class TestMonitorSessionHealth:
    """Test suite for session health monitoring."""

    @pytest.mark.asyncio
    async def test_monitor_session_health(
        self, interaction_service, mock_repository
    ):
        """Test session health monitoring."""
        session_id = uuid4()
        
        mock_session = MagicMock()
        mock_session.status.time_since_last_activity = 7200  # 2 hours
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.parties = {}
        mock_session.active_proposals = {}
        mock_session.total_responses = 0
        mock_session.status.phase.value = "opening"
        
        mock_repository.get_by_id = AsyncMock(return_value=mock_session)
        
        interaction_service.command_handler.handle_detect_negotiation_conflicts = AsyncMock(
            return_value={"conflicts_detected": []}
        )
        interaction_service.command_handler.handle_calculate_negotiation_momentum = AsyncMock(
            return_value={
                "momentum_analysis": {
                    "momentum_score": Decimal("60"),
                    "direction": "stable",
                }
            }
        )
        
        result = await interaction_service.monitor_session_health(
            session_id=session_id,
            initiated_by=uuid4(),
        )
        
        assert result["operation"] == "monitor_session_health"
        assert result["success"] is True
        assert "health_summary" in result
        assert "health_score" in result["health_summary"]

    @pytest.mark.asyncio
    async def test_monitor_session_not_found(
        self, interaction_service, mock_repository
    ):
        """Test monitoring non-existent session."""
        session_id = uuid4()
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Session .* not found"):
            await interaction_service.monitor_session_health(
                session_id=session_id,
                initiated_by=uuid4(),
            )


class TestPrivateHelperMethods:
    """Test suite for private helper methods."""

    def test_calculate_success_probability(self, interaction_service):
        """Test success probability calculation."""
        probability = interaction_service._calculate_success_probability(
            compatibility_score=75.0,
            conflict_count=2,
            momentum_score=70.0,
        )
        
        assert 0 <= probability <= 100

    def test_generate_recommendations(self, interaction_service):
        """Test recommendation generation."""
        compatibility_result = {
            "overall_compatibility": 40.0,
        }
        strategy_result = {
            "strategy_recommendation": {
                "key_tactics": ["Build trust"],
            }
        }
        conflicts_result = {
            "conflicts_detected": [
                {"severity": "high", "resolution_suggestions": ["Mediate"]}
            ],
        }
        momentum_result = {
            "momentum_analysis": {
                "recommendations": ["Act quickly"],
            }
        }
        
        recommendations = interaction_service._generate_recommendations(
            compatibility_result,
            strategy_result,
            conflicts_result,
            momentum_result,
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_calculate_health_score(self, interaction_service):
        """Test health score calculation."""
        mock_session = MagicMock()
        mock_session.status.time_since_last_activity = 3600
        mock_session.status.phase.value = "opening"
        mock_session.active_proposals = {}
        
        conflicts = []
        momentum_analysis = {"momentum_score": Decimal("75")}
        
        score = interaction_service._calculate_health_score(
            mock_session, conflicts, momentum_analysis
        )
        
        assert 0 <= score <= 100

    def test_get_health_status(self, interaction_service):
        """Test health status categorization."""
        assert interaction_service._get_health_status(85) == "excellent"
        assert interaction_service._get_health_status(70) == "good"
        assert interaction_service._get_health_status(55) == "fair"
        assert interaction_service._get_health_status(40) == "poor"
        assert interaction_service._get_health_status(20) == "critical"

    def test_generate_health_recommendations(self, interaction_service):
        """Test health recommendation generation."""
        health_alerts = [
            {"type": "timeout_warning"},
            {"type": "inactivity_warning"},
        ]
        
        recommendations = interaction_service._generate_health_recommendations(
            health_score=45.0,
            health_alerts=health_alerts,
        )
        
        assert isinstance(recommendations, list)
