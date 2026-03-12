#!/usr/bin/env python3
"""Unit tests for src/core/narrative/negotiation.py module."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.narrative.negotiation import AgentNegotiationEngine
from src.core.narrative.types import (
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
)


class TestAgentNegotiationEngineInit:
    """Tests for AgentNegotiationEngine initialization."""

    @pytest.mark.unit
    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        with patch("src.core.narrative.negotiation.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm
            engine = AgentNegotiationEngine()

        assert engine.llm_service is not None
        assert engine.active_sessions == {}
        assert engine.negotiation_history == []
        assert engine.agent_negotiation_profiles == {}

    @pytest.mark.unit
    def test_init_with_llm_service(self):
        """Test initialization with provided LLM service."""
        mock_llm = MagicMock()
        engine = AgentNegotiationEngine(llm_service=mock_llm)

        assert engine.llm_service == mock_llm
        assert engine.active_sessions == {}
        assert engine.negotiation_history == []
        assert engine.agent_negotiation_profiles == {}


class TestAgentNegotiationEngineInitializeAgentProfile:
    """Tests for initialize_agent_profile method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine instance."""
        return AgentNegotiationEngine(llm_service=MagicMock())

    @pytest.mark.unit
    def test_initialize_profile_defaults(self, engine):
        """Test initializing agent profile with defaults."""
        engine.initialize_agent_profile("agent_1")

        assert "agent_1" in engine.agent_negotiation_profiles
        profile = engine.agent_negotiation_profiles["agent_1"]

        assert profile["style"]["cooperativeness"] == 0.5
        assert profile["style"]["competitiveness"] == 0.5
        assert profile["style"]["compromise_willingness"] == 0.6
        assert profile["style"]["patience"] == 0.7
        assert profile["style"]["trust_level"] == 0.5
        assert profile["priorities"] == ["survival", "mission_success"]
        assert profile["successful_negotiations"] == 0
        assert profile["failed_negotiations"] == 0
        assert profile["reputation"] == 0.5

    @pytest.mark.unit
    def test_initialize_profile_custom_values(self, engine):
        """Test initializing agent profile with custom values."""
        style = {"cooperativeness": 0.8, "competitiveness": 0.2}
        priorities = ["wealth", "power"]

        engine.initialize_agent_profile("agent_1", negotiation_style=style, priorities=priorities)

        profile = engine.agent_negotiation_profiles["agent_1"]
        assert profile["style"] == style
        assert profile["priorities"] == priorities

    @pytest.mark.unit
    def test_initialize_profile_overwrite(self, engine):
        """Test that initializing profile overwrites existing."""
        engine.initialize_agent_profile("agent_1")
        # Reputation should be reset after re-initialization
        engine.initialize_agent_profile("agent_1", priorities=["new_priority"])

        assert engine.agent_negotiation_profiles["agent_1"]["priorities"] == ["new_priority"]


class TestAgentNegotiationEngineInitiateNegotiation:
    """Tests for initiate_negotiation method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine instance."""
        return AgentNegotiationEngine(llm_service=MagicMock())

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initiate_negotiation_basic(self, engine):
        """Test basic negotiation initiation."""
        with patch.object(engine, "_notify_agents_of_proposal", new_callable=AsyncMock):
            session_id = await engine.initiate_negotiation(
                initiator_id="agent_1",
                target_agents=["agent_2", "agent_3"],
                topic="resource_sharing",
                initial_proposal={"type": "offer", "resource": "gold", "amount": 100},
            )

        assert isinstance(session_id, str)
        assert session_id in engine.active_sessions

        session = engine.active_sessions[session_id]
        assert session.session_id == session_id
        assert session.participants == ["agent_1", "agent_2", "agent_3"]
        assert session.topic == "resource_sharing"
        assert session.status == NegotiationStatus.INITIATED
        assert len(session.proposals) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initiate_negotiation_creates_proposal(self, engine):
        """Test that negotiation initiation creates initial proposal."""
        with patch.object(engine, "_notify_agents_of_proposal", new_callable=AsyncMock):
            session_id = await engine.initiate_negotiation(
                initiator_id="agent_1",
                target_agents=["agent_2"],
                topic="test",
                initial_proposal={"type": "offer", "value": 50},
            )

        session = engine.active_sessions[session_id]
        proposal = session.proposals[0]

        assert proposal.proposer_id == "agent_1"
        assert proposal.target_agents == ["agent_2"]
        assert proposal.proposal_type == "offer"
        assert proposal.content == {"type": "offer", "value": 50}
        assert proposal.expires_at is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initiate_negotiation_notifies_agents(self, engine):
        """Test that negotiation initiation notifies agents."""
        with patch.object(engine, "_notify_agents_of_proposal", new_callable=AsyncMock) as mock_notify:
            await engine.initiate_negotiation(
                initiator_id="agent_1",
                target_agents=["agent_2", "agent_3"],
                topic="test",
                initial_proposal={},
            )

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "agent_2" in call_args[0][1]
        assert "agent_3" in call_args[0][1]


class TestAgentNegotiationEngineNotifyAgentsOfProposal:
    """Tests for _notify_agents_of_proposal method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine instance."""
        return AgentNegotiationEngine(llm_service=MagicMock())

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_notify_agents_logs_debug(self, engine):
        """Test that notifying agents logs debug messages."""
        proposal = MagicMock(spec=NegotiationProposal)
        proposal.proposal_id = "prop_123"

        with patch("src.core.narrative.negotiation.logger") as mock_logger:
            await engine._notify_agents_of_proposal(proposal, ["agent_1", "agent_2"])

        assert mock_logger.debug.call_count == 2


class TestAgentNegotiationEngineRespondToProposal:
    """Tests for respond_to_proposal method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine with an active session."""
        engine = AgentNegotiationEngine(llm_service=MagicMock())

        # Create a session with a proposal
        session_id = str(uuid.uuid4())
        proposal_id = str(uuid.uuid4())

        proposal = NegotiationProposal(
            proposal_id=proposal_id,
            proposer_id="agent_1",
            proposal_type="offer",
            content={"value": 100},
            target_agents=["agent_2", "agent_3"],
        )

        session = NegotiationSession(
            session_id=session_id,
            participants=["agent_1", "agent_2", "agent_3"],
            topic="test",
            status=NegotiationStatus.INITIATED,
            proposals=[proposal],
        )

        engine.active_sessions[session_id] = session
        engine.sessions_by_proposal = {proposal_id: session_id}

        return engine, proposal_id, session_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_respond_to_proposal_success(self, engine):
        """Test successful response to proposal."""
        engine, proposal_id, session_id = engine

        with patch.object(engine, "_evaluate_negotiation_status", new_callable=AsyncMock):
            result = await engine.respond_to_proposal(
                proposal_id=proposal_id,
                responder_id="agent_2",
                response_type="accept",
                response_content={"reason": "agreed"},
            )

        assert result is True
        session = engine.active_sessions[session_id]
        assert len(session.responses) == 1
        assert session.responses[0].responder_id == "agent_2"
        assert session.responses[0].response_type == "accept"
        assert session.status == NegotiationStatus.IN_PROGRESS

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_respond_to_proposal_not_found(self, engine):
        """Test response to non-existent proposal."""
        engine, _, _ = engine

        result = await engine.respond_to_proposal(
            proposal_id="nonexistent",
            responder_id="agent_2",
            response_type="accept",
        )

        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_respond_to_proposal_non_participant(self, engine):
        """Test response from non-participant agent."""
        engine, proposal_id, _ = engine

        result = await engine.respond_to_proposal(
            proposal_id=proposal_id,
            responder_id="agent_4",  # Not a participant
            response_type="accept",
        )

        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_respond_to_proposal_counter_generates_intelligent_response(self, engine):
        """Test that counter proposal triggers intelligent response generation."""
        engine, proposal_id, _ = engine

        with patch.object(engine, "_generate_intelligent_counter_proposal", new_callable=AsyncMock) as mock_gen:
            with patch.object(engine, "_evaluate_negotiation_status", new_callable=AsyncMock):
                await engine.respond_to_proposal(
                    proposal_id=proposal_id,
                    responder_id="agent_2",
                    response_type="counter",
                )

        mock_gen.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_respond_to_proposal_conditional_generates_intelligent_response(self, engine):
        """Test that conditional response triggers intelligent response generation."""
        engine, proposal_id, _ = engine

        with patch.object(engine, "_generate_intelligent_counter_proposal", new_callable=AsyncMock) as mock_gen:
            with patch.object(engine, "_evaluate_negotiation_status", new_callable=AsyncMock):
                await engine.respond_to_proposal(
                    proposal_id=proposal_id,
                    responder_id="agent_2",
                    response_type="conditional",
                )

        mock_gen.assert_called_once()


class TestAgentNegotiationEngineEvaluateNegotiationStatus:
    """Tests for _evaluate_negotiation_status method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine instance."""
        return AgentNegotiationEngine(llm_service=MagicMock())

    @pytest.fixture
    def sample_session(self, engine):
        """Create a sample negotiation session."""
        proposal = NegotiationProposal(
            proposal_id="prop_1",
            proposer_id="agent_1",
            proposal_type="offer",
            content={},
            target_agents=["agent_2"],
        )

        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1", "agent_2"],
            topic="test",
            status=NegotiationStatus.IN_PROGRESS,
            proposals=[proposal],
            created_at=datetime.now(),
            timeout_minutes=30,
        )

        engine.active_sessions["session_1"] = session
        return session

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_evaluate_timeout(self, engine, sample_session):
        """Test timeout detection."""
        # Set created_at to past timeout
        sample_session.created_at = datetime.now() - timedelta(minutes=31)

        with patch.object(engine, "_finalize_session") as mock_finalize:
            await engine._evaluate_negotiation_status(sample_session)

        assert sample_session.status == NegotiationStatus.TIMEOUT
        mock_finalize.assert_called_once_with(sample_session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_evaluate_not_timed_out(self, engine, sample_session):
        """Test when not timed out."""
        # Set created_at to within timeout
        sample_session.created_at = datetime.now()

        with patch.object(engine, "_attempt_resolution", new_callable=AsyncMock):
            await engine._evaluate_negotiation_status(sample_session)

        # _attempt_resolution is only called when all target agents have responded
        # With no responses, it won't be called
        # So we just verify the session status wasn't changed to timeout
        assert sample_session.status != NegotiationStatus.TIMEOUT


class TestAgentNegotiationEngineAttemptResolution:
    """Tests for _attempt_resolution method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine instance."""
        return AgentNegotiationEngine(llm_service=MagicMock())

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unanimous_acceptance(self, engine):
        """Test unanimous acceptance resolution."""
        proposal = NegotiationProposal(
            proposal_id="prop_1",
            proposer_id="agent_1",
            proposal_type="offer",
            content={"value": 100},
            target_agents=["agent_2", "agent_3"],
        )

        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1", "agent_2", "agent_3"],
            topic="test",
            status=NegotiationStatus.IN_PROGRESS,
            proposals=[proposal],
            responses=[
                NegotiationResponse(
                    response_id="resp_1",
                    proposal_id="prop_1",
                    responder_id="agent_2",
                    response_type="accept",
                    content={},
                ),
                NegotiationResponse(
                    response_id="resp_2",
                    proposal_id="prop_1",
                    responder_id="agent_3",
                    response_type="accept",
                    content={},
                ),
            ],
        )

        with patch.object(engine, "_finalize_session"):
            engine.initialize_agent_profile("agent_1")
            engine.initialize_agent_profile("agent_2")
            engine.initialize_agent_profile("agent_3")
            await engine._attempt_resolution(session)

        assert session.status == NegotiationStatus.RESOLVED
        assert session.resolution is not None
        assert session.resolution["type"] == "unanimous_acceptance"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_majority_rejection_with_counter(self, engine):
        """Test majority rejection with counter proposals."""
        proposal = NegotiationProposal(
            proposal_id="prop_1",
            proposer_id="agent_1",
            proposal_type="offer",
            content={},
            target_agents=["agent_2", "agent_3"],
        )

        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1", "agent_2", "agent_3"],
            topic="test",
            status=NegotiationStatus.IN_PROGRESS,
            proposals=[proposal],
            responses=[
                NegotiationResponse(
                    response_id="resp_1",
                    proposal_id="prop_1",
                    responder_id="agent_2",
                    response_type="reject",
                    content={},
                ),
                NegotiationResponse(
                    response_id="resp_2",
                    proposal_id="prop_1",
                    responder_id="agent_3",
                    response_type="counter",
                    content={},
                ),
            ],
        )

        with patch.object(engine, "_handle_counter_proposals", new_callable=AsyncMock) as mock_handle:
            await engine._attempt_resolution(session)

        mock_handle.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_majority_rejection_without_counter(self, engine):
        """Test majority rejection without counter proposals."""
        proposal = NegotiationProposal(
            proposal_id="prop_1",
            proposer_id="agent_1",
            proposal_type="offer",
            content={},
            target_agents=["agent_2"],
        )

        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1", "agent_2"],
            topic="test",
            status=NegotiationStatus.IN_PROGRESS,
            proposals=[proposal],
            responses=[
                NegotiationResponse(
                    response_id="resp_1",
                    proposal_id="prop_1",
                    responder_id="agent_2",
                    response_type="reject",
                    content={},
                ),
            ],
        )

        with patch.object(engine, "_finalize_session"):
            engine.initialize_agent_profile("agent_1")
            engine.initialize_agent_profile("agent_2")
            await engine._attempt_resolution(session)

        assert session.status == NegotiationStatus.FAILED


class TestAgentNegotiationEngineEvaluateProposalViability:
    """Tests for _evaluate_proposal_viability method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine instance."""
        return AgentNegotiationEngine(llm_service=MagicMock())

    @pytest.mark.unit
    def test_viability_none_proposal(self, engine):
        """Test viability of None proposal."""
        score = engine._evaluate_proposal_viability(None)
        assert score == 0.0

    @pytest.mark.unit
    def test_viability_base_score(self, engine):
        """Test base viability score."""
        proposal = {"type": "offer"}
        score = engine._evaluate_proposal_viability(proposal)
        assert score == 0.5  # Base score

    @pytest.mark.unit
    def test_viability_with_benefits(self, engine):
        """Test viability with benefits."""
        proposal = {"type": "offer", "benefits_offered": {"gold": 100}}
        score = engine._evaluate_proposal_viability(proposal)
        assert score == 0.7  # Base + 0.2

    @pytest.mark.unit
    def test_viability_with_requirements(self, engine):
        """Test viability with requirements (penalty)."""
        proposal = {"type": "offer", "requirements": ["req1", "req2", "req3"]}
        score = engine._evaluate_proposal_viability(proposal)
        assert score == 0.2  # Base - 0.3 (capped at 0)

    @pytest.mark.unit
    def test_viability_capped(self, engine):
        """Test that viability is capped between 0 and 1."""
        proposal = {"type": "offer", "benefits_offered": {"a": 1, "b": 2, "c": 3}}
        score = engine._evaluate_proposal_viability(proposal)
        assert 0.0 <= score <= 1.0


class TestAgentNegotiationEngineUpdateAgentReputations:
    """Tests for _update_agent_reputations method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine with profiles."""
        engine = AgentNegotiationEngine(llm_service=MagicMock())
        engine.initialize_agent_profile("agent_1")
        engine.initialize_agent_profile("agent_2")
        return engine

    @pytest.fixture
    def sample_session(self):
        """Create a sample negotiation session."""
        return NegotiationSession(
            session_id="session_1",
            participants=["agent_1", "agent_2"],
            topic="test",
            status=NegotiationStatus.RESOLVED,
        )

    @pytest.mark.unit
    def test_update_reputation_success(self, engine, sample_session):
        """Test reputation update on successful negotiation."""
        initial_reputation = engine.agent_negotiation_profiles["agent_1"]["reputation"]

        engine._update_agent_reputations(sample_session, success=True)

        assert engine.agent_negotiation_profiles["agent_1"]["successful_negotiations"] == 1
        assert engine.agent_negotiation_profiles["agent_1"]["reputation"] == initial_reputation + 0.1

    @pytest.mark.unit
    def test_update_reputation_failure(self, engine, sample_session):
        """Test reputation update on failed negotiation."""
        initial_reputation = engine.agent_negotiation_profiles["agent_1"]["reputation"]

        engine._update_agent_reputations(sample_session, success=False)

        assert engine.agent_negotiation_profiles["agent_1"]["failed_negotiations"] == 1
        assert engine.agent_negotiation_profiles["agent_1"]["reputation"] == initial_reputation - 0.05

    @pytest.mark.unit
    def test_update_reputation_capped(self, engine, sample_session):
        """Test that reputation is capped between 0 and 1."""
        # Set reputation near max
        engine.agent_negotiation_profiles["agent_1"]["reputation"] = 0.98

        engine._update_agent_reputations(sample_session, success=True)

        assert engine.agent_negotiation_profiles["agent_1"]["reputation"] == 1.0  # Capped

    @pytest.mark.unit
    def test_update_reputation_unknown_agent(self, engine, sample_session):
        """Test reputation update with unknown agent in session."""
        sample_session.participants.append("unknown_agent")

        # Should not raise exception
        engine._update_agent_reputations(sample_session, success=True)


class TestAgentNegotiationEngineFinalizeSession:
    """Tests for _finalize_session method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine with an active session."""
        engine = AgentNegotiationEngine(llm_service=MagicMock())
        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1"],
            topic="test",
            status=NegotiationStatus.RESOLVED,
        )
        engine.active_sessions["session_1"] = session
        return engine, session

    @pytest.mark.unit
    def test_finalize_removes_from_active(self, engine):
        """Test that finalizing removes session from active."""
        engine, session = engine

        engine._finalize_session(session)

        assert "session_1" not in engine.active_sessions

    @pytest.mark.unit
    def test_finalize_adds_to_history(self, engine):
        """Test that finalizing adds session to history."""
        engine, session = engine

        initial_history_len = len(engine.negotiation_history)
        engine._finalize_session(session)

        assert len(engine.negotiation_history) == initial_history_len + 1
        assert engine.negotiation_history[-1] == session

    @pytest.mark.unit
    def test_finalize_unknown_session(self, engine):
        """Test finalizing a session not in active sessions."""
        engine, _ = engine

        unknown_session = NegotiationSession(
            session_id="unknown",
            participants=["agent_1"],
            topic="test",
            status=NegotiationStatus.RESOLVED,
        )

        # Should not raise exception
        engine._finalize_session(unknown_session)


class TestAgentNegotiationEngineGetNegotiationSummary:
    """Tests for get_negotiation_summary method."""

    @pytest.fixture
    def engine(self):
        """Create an AgentNegotiationEngine with sessions."""
        engine = AgentNegotiationEngine(llm_service=MagicMock())

        # Create active session
        active_session = NegotiationSession(
            session_id="active_1",
            participants=["agent_1", "agent_2"],
            topic="active_topic",
            status=NegotiationStatus.IN_PROGRESS,
            proposals=[NegotiationProposal(
                proposal_id="prop_1",
                proposer_id="agent_1",
                proposal_type="offer",
                content={},
                target_agents=["agent_2"],
            )],
            created_at=datetime.now() - timedelta(minutes=10),
            updated_at=datetime.now(),
        )
        engine.active_sessions["active_1"] = active_session

        # Create historical session
        historical_session = NegotiationSession(
            session_id="hist_1",
            participants=["agent_3"],
            topic="historical_topic",
            status=NegotiationStatus.RESOLVED,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now() - timedelta(minutes=50),
        )
        engine.negotiation_history.append(historical_session)

        return engine

    @pytest.mark.unit
    def test_get_summary_active_session(self, engine):
        """Test getting summary of active session."""
        summary = engine.get_negotiation_summary("active_1")

        assert summary["session_id"] == "active_1"
        assert summary["topic"] == "active_topic"
        assert summary["status"] == "in_progress"
        assert summary["participants"] == ["agent_1", "agent_2"]

    @pytest.mark.unit
    def test_get_summary_historical_session(self, engine):
        """Test getting summary of historical session."""
        summary = engine.get_negotiation_summary("hist_1")

        assert summary["session_id"] == "hist_1"
        assert summary["topic"] == "historical_topic"
        assert summary["status"] == "resolved"

    @pytest.mark.unit
    def test_get_summary_not_found(self, engine):
        """Test getting summary of non-existent session."""
        summary = engine.get_negotiation_summary("nonexistent")

        assert summary == {}

    @pytest.mark.unit
    def test_get_summary_includes_duration(self, engine):
        """Test that summary includes duration."""
        summary = engine.get_negotiation_summary("active_1")

        assert "duration_minutes" in summary
        assert summary["duration_minutes"] > 0

    @pytest.mark.unit
    def test_get_summary_includes_counts(self, engine):
        """Test that summary includes proposal and response counts."""
        summary = engine.get_negotiation_summary("active_1")

        assert summary["proposal_count"] == 1
        assert summary["response_count"] == 0
