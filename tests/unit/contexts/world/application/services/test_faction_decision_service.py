#!/usr/bin/env python3
"""Unit tests for FactionDecisionService.

Tests the application-layer service for AI-driven faction decision-making,
including context assembly, resource constraints, and fallback behavior.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.application.services.faction_decision_service import (
    ActionDefinition,
    DecisionContext,
    FactionDecisionService,
    ACTION_DEFINITIONS,
    FOOD_THRESHOLD_NO_ATTACK,
    GOLD_THRESHOLD_PRIORITIZE_TRADE,
    MAX_INTENTS_PER_GENERATION,
    MILITARY_THRESHOLD_NO_SABOTAGE,
)
from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)
from src.core.result import Ok, Err


class TestDecisionContext:
    """Tests for the DecisionContext dataclass."""

    @pytest.mark.unit
    def test_decision_context_creation(self):
        """Test creating a DecisionContext with all fields."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 500, "food": 100},
            diplomacy={"faction-2": "hostile"},
            territories=["territory-1", "territory-2"],
            recent_events=[{"type": "battle", "result": "victory"}],
            relevant_lore=[{"topic": "ancient_grudge"}],
        )

        assert context.faction_id == "faction-1"
        assert context.resources["gold"] == 500
        assert context.diplomacy["faction-2"] == "hostile"
        assert len(context.territories) == 2

    @pytest.mark.unit
    def test_get_resource_summary(self):
        """Test resource summary generation."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 500, "food": 100, "military": 50},
        )

        summary = context.get_resource_summary()

        # Summary should contain all resources
        assert "food=100" in summary
        assert "gold=500" in summary
        assert "military=50" in summary

    @pytest.mark.unit
    def test_get_resource_summary_empty(self):
        """Test resource summary with no resources."""
        context = DecisionContext(faction_id="faction-1")

        summary = context.get_resource_summary()

        assert summary == "no resources"


class TestActionDefinition:
    """Tests for the ActionDefinition dataclass."""

    @pytest.mark.unit
    def test_action_definitions_exist(self):
        """Test that all action types have definitions."""
        action_types = {ad.action_type for ad in ACTION_DEFINITIONS}

        expected_types = {
            ActionType.EXPAND,
            ActionType.ATTACK,
            ActionType.TRADE,
            ActionType.SABOTAGE,
            ActionType.STABILIZE,
        }

        assert action_types == expected_types

    @pytest.mark.unit
    def test_action_definition_requirements(self):
        """Test that action definitions have proper requirements."""
        for action_def in ACTION_DEFINITIONS:
            assert action_def.action_type is not None
            assert action_def.name is not None
            assert action_def.description is not None


class TestFactionDecisionServiceConstants:
    """Tests for service constants."""

    @pytest.mark.unit
    def test_threshold_values(self):
        """Test that threshold constants are properly defined."""
        assert FOOD_THRESHOLD_NO_ATTACK == 100
        assert MILITARY_THRESHOLD_NO_SABOTAGE == 50
        assert GOLD_THRESHOLD_PRIORITIZE_TRADE == 200
        assert MAX_INTENTS_PER_GENERATION == 3


class TestFactionDecisionService:
    """Tests for the FactionDecisionService class."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository for testing."""
        repo = MagicMock()
        repo.save = MagicMock()
        repo.find_by_faction = MagicMock(return_value=[])
        repo.count_active = MagicMock(return_value=0)
        repo.can_add_intent = MagicMock(return_value=True)
        return repo

    @pytest.fixture
    def service(self, mock_repository):
        """Create a FactionDecisionService instance."""
        return FactionDecisionService(
            repository=mock_repository,
            llm_client=None,
            retrieval_service=None,
        )

    @pytest.fixture
    def low_food_context(self):
        """Create a context with low food resources."""
        return DecisionContext(
            faction_id="hungry-faction",
            resources={"gold": 500, "food": 30, "military": 100},
            diplomacy={},
            territories=["t1"],
        )

    @pytest.fixture
    def low_military_context(self):
        """Create a context with low military resources."""
        return DecisionContext(
            faction_id="weak-faction",
            resources={"gold": 500, "food": 200, "military": 20},
            diplomacy={"enemy-faction": "hostile"},
            territories=["t1"],
        )

    @pytest.fixture
    def high_gold_context(self):
        """Create a context with high gold resources."""
        return DecisionContext(
            faction_id="rich-faction",
            resources={"gold": 1000, "food": 200, "military": 100},
            diplomacy={},
            territories=["t1", "t2"],
        )

    @pytest.mark.unit
    def test_service_creation(self, service):
        """Test that the service can be created."""
        assert service is not None

    @pytest.mark.unit
    def test_get_available_actions_low_food(self, service, low_food_context):
        """Test that low food prevents ATTACK actions."""
        available_actions = service._get_available_actions(low_food_context)

        # Should not include ATTACK when food is low
        action_types = [a.action_type for a in available_actions]
        assert ActionType.ATTACK not in action_types

    @pytest.mark.unit
    def test_get_available_actions_low_military(self, service, low_military_context):
        """Test that low military affects SABOTAGE actions."""
        available_actions = service._get_available_actions(low_military_context)

        # Low military should prevent SABOTAGE
        action_types = [a.action_type for a in available_actions]
        assert ActionType.SABOTAGE not in action_types
        assert ActionType.ATTACK not in action_types  # Also needs military >= 50

    @pytest.mark.unit
    def test_get_available_actions_high_resources(self, service, high_gold_context):
        """Test all actions available with abundant resources."""
        available_actions = service._get_available_actions(high_gold_context)

        # With high resources, most actions should be available
        action_types = [a.action_type for a in available_actions]
        assert ActionType.EXPAND in action_types
        assert ActionType.TRADE in action_types
        assert ActionType.STABILIZE in action_types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enrich_context_with_rag(self, service):
        """Test RAG context enrichment (stub implementation)."""
        context = DecisionContext(
            faction_id="test-faction",
            resources={"gold": 100},
        )

        # Issue 7: _enrich_context_with_rag now returns tuple (context, rag_success)
        enriched, rag_success = await service._enrich_context_with_rag(context)

        # Without retrieval service, should return same context and rag_success=False
        assert enriched.faction_id == context.faction_id
        assert rag_success is False


class TestFactionDecisionServiceIntegration:
    """Integration-style tests for FactionDecisionService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository that tracks calls."""
        repo = MagicMock()
        repo.saved_intents = []

        def track_save(intent):
            repo.saved_intents.append(intent)

        repo.save = MagicMock(side_effect=track_save)
        repo.count_active = MagicMock(return_value=0)
        repo.can_add_intent = MagicMock(return_value=True)
        return repo

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_intents_saves_to_repository(self, mock_repository):
        """Test that generated intents are saved to the repository."""
        service = FactionDecisionService(
            repository=mock_repository,
            llm_client=None,
            retrieval_service=None,
        )

        # Create a faction and context for the test
        from src.contexts.world.domain.entities.faction import Faction
        faction = Faction(id="test-faction", name="Test Faction")
        context = DecisionContext(
            faction_id="test-faction",
            resources={"gold": 500, "food": 200, "military": 100},
        )

        result = await service.generate_intents(faction, context)

        # Should have saved intents
        assert result.is_ok, f"Expected Ok result, got error: {result.error if result.is_error else 'unknown'}"
        assert len(mock_repository.saved_intents) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_intents_returns_event(self, mock_repository):
        """Test that generating intents returns an event."""
        service = FactionDecisionService(
            repository=mock_repository,
            llm_client=None,
            retrieval_service=None,
        )

        from src.contexts.world.domain.entities.faction import Faction
        faction = Faction(id="test-faction", name="Test Faction")
        context = DecisionContext(
            faction_id="test-faction",
            resources={"gold": 500, "food": 200, "military": 100},
        )

        result = await service.generate_intents(faction, context)

        # Should return intents with event
        assert result.is_ok, f"Expected Ok result, got error: {result.error if result.is_error else 'unknown'}"
        intents, event = result.value
        assert event is not None
        assert event.faction_id == "test-faction"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_intents_capacity_check(self, mock_repository):
        """Test that generation respects max active intents."""
        # Mock repository at capacity
        mock_repository.count_active = MagicMock(return_value=10)

        service = FactionDecisionService(
            repository=mock_repository,
            llm_client=None,
            retrieval_service=None,
        )

        from src.contexts.world.domain.entities.faction import Faction
        faction = Faction(id="test-faction", name="Test Faction")
        context = DecisionContext(faction_id="test-faction")

        result = await service.generate_intents(faction, context)

        # Should return error when at capacity
        assert result.is_error

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_intents_with_low_resources(self, mock_repository):
        """Test generation with constrained resources."""
        service = FactionDecisionService(
            repository=mock_repository,
            llm_client=None,
            retrieval_service=None,
        )

        from src.contexts.world.domain.entities.faction import Faction
        faction = Faction(id="test-faction", name="Test Faction")
        context = DecisionContext(
            faction_id="test-faction",
            resources={"gold": 10, "food": 10, "military": 10},
        )

        result = await service.generate_intents(faction, context)

        # Should still generate intents (fallback), but with limited options
        assert result.is_ok, f"Expected Ok result, got error: {result.error if result.is_error else 'unknown'}"
        intents, event = result.value
        # Should not have ATTACK or SABOTAGE due to low resources
        action_types = [i.action_type for i in intents]
        assert ActionType.ATTACK not in action_types
        assert ActionType.SABOTAGE not in action_types


class TestFactionDecisionServiceErrorPaths:
    """Tests for error handling and failure scenarios."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository for testing."""
        repo = MagicMock()
        repo.save = MagicMock()
        repo.find_by_faction = MagicMock(return_value=[])
        repo.count_active = MagicMock(return_value=0)
        repo.can_add_intent = MagicMock(return_value=True)
        return repo

    @pytest.fixture
    def faction(self):
        """Create a test faction."""
        from src.contexts.world.domain.entities.faction import Faction
        return Faction(id="test-faction", name="Test Faction")

    @pytest.fixture
    def context(self):
        """Create a test context."""
        return DecisionContext(
            faction_id="test-faction",
            resources={"gold": 500, "food": 200, "military": 100},
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rag_service_timeout_falls_back_gracefully(
        self, mock_repository, faction, context
    ):
        """When RAG times out, should continue without RAG context."""
        # Create mock retrieval service that raises TimeoutError
        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve_relevant.side_effect = TimeoutError("RAG timeout")

        service = FactionDecisionService(
            repository=mock_repository,
            retrieval_service=mock_retrieval,
        )

        # Should still generate intents despite RAG failure
        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        assert len(intents) > 0
        # Context should not have RAG data (fell back gracefully)
        assert context.recent_events == []
        assert context.relevant_lore == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rag_service_returns_empty_results(
        self, mock_repository, faction, context
    ):
        """When RAG returns no results, should generate without context."""
        # Create mock retrieval service that returns empty results
        mock_retrieval = AsyncMock()

        # Create a mock RetrievalResult with empty chunks
        mock_result = MagicMock()
        mock_result.chunks = []
        mock_retrieval.retrieve_relevant.return_value = mock_result

        service = FactionDecisionService(
            repository=mock_repository,
            retrieval_service=mock_retrieval,
        )

        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        assert len(intents) > 0
        # Context should have empty RAG data
        assert context.recent_events == []
        assert context.relevant_lore == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_timeout_uses_fallback_intents(
        self, mock_repository, faction, context
    ):
        """When LLM times out (or is unavailable), should use rule-based fallback."""
        service = FactionDecisionService(
            repository=mock_repository,
            llm_client=None,  # No LLM = triggers fallback
        )

        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        # Event should indicate fallback was used
        assert event.fallback is True
        assert len(intents) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rag_service_connection_error_falls_back(
        self, mock_repository, faction, context
    ):
        """When RAG has connection error, should continue without RAG context."""
        # Create mock retrieval service that raises connection error
        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve_relevant.side_effect = ConnectionError(
            "Cannot connect to vector store"
        )

        service = FactionDecisionService(
            repository=mock_repository,
            retrieval_service=mock_retrieval,
        )

        # Should still generate intents despite RAG failure
        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        assert len(intents) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rag_service_generic_exception_falls_back(
        self, mock_repository, faction, context
    ):
        """When RAG throws generic exception, should continue without RAG context."""
        # Create mock retrieval service that raises generic exception
        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve_relevant.side_effect = Exception("Unexpected RAG error")

        service = FactionDecisionService(
            repository=mock_repository,
            retrieval_service=mock_retrieval,
        )

        # Should still generate intents despite RAG failure
        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        assert len(intents) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_retrieval_service_continues_without_rag(
        self, mock_repository, faction, context
    ):
        """When no RetrievalService is configured, should generate without RAG."""
        service = FactionDecisionService(
            repository=mock_repository,
            retrieval_service=None,  # No RAG service configured
        )

        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        assert len(intents) > 0
        # Context should remain unchanged (no RAG enrichment)
        assert context.recent_events == []
        assert context.relevant_lore == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rag_service_returns_successful_results(
        self, mock_repository, faction, context
    ):
        """When RAG successfully returns results, should enrich context."""
        # Create mock retrieval service that returns results
        mock_retrieval = AsyncMock()

        # Create mock chunks for events
        mock_event_chunk = MagicMock()
        mock_event_chunk.content = "Faction won a major battle"
        mock_event_chunk.source_id = "event-001"

        # Create mock chunks for lore
        mock_lore_chunk = MagicMock()
        mock_lore_chunk.content = "Ancient grudge against northern clans"
        mock_lore_chunk.source_id = "lore-001"

        # Create mock results
        events_result = MagicMock()
        events_result.chunks = [mock_event_chunk]

        lore_result = MagicMock()
        lore_result.chunks = [mock_lore_chunk]

        # Configure mock to return different results for different calls
        mock_retrieval.retrieve_relevant.side_effect = [events_result, lore_result]

        service = FactionDecisionService(
            repository=mock_repository,
            retrieval_service=mock_retrieval,
        )

        result = await service.generate_intents(faction, context)
        assert result.is_ok

        intents, event = result.value
        assert len(intents) > 0
        # Original context should remain unchanged (no mutation)
        assert context.recent_events == []
        assert context.relevant_lore == []


class TestSelectIntentMethod:
    """Tests for the select_intent method."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository for testing."""
        repo = MagicMock()
        repo.save = MagicMock()
        repo.find_by_faction = MagicMock(return_value=[])
        repo.count_active = MagicMock(return_value=0)
        repo.can_add_intent = MagicMock(return_value=True)
        repo.mark_selected = MagicMock(return_value=True)
        return repo

    @pytest.fixture
    def service(self, mock_repository):
        """Create a FactionDecisionService instance."""
        return FactionDecisionService(
            repository=mock_repository,
            llm_client=None,
            retrieval_service=None,
        )

    @pytest.mark.unit
    def test_select_intent_success(self, service, mock_repository):
        """Test successfully selecting an intent."""
        from src.contexts.world.domain.entities.faction_intent import FactionIntent

        intent = FactionIntent(
            faction_id="test-faction",
            action_type=ActionType.EXPAND,
            rationale="Test rationale",
            status=IntentStatus.PROPOSED,
        )
        mock_repository.find_by_id = MagicMock(return_value=intent)

        result = service.select_intent(intent.id, "test-faction")

        assert result.is_ok
        assert result.value == intent
        mock_repository.mark_selected.assert_called_once_with(intent.id)

    @pytest.mark.unit
    def test_select_intent_not_found(self, service, mock_repository):
        """Test selecting a non-existent intent."""
        mock_repository.find_by_id = MagicMock(return_value=None)

        result = service.select_intent("nonexistent-id", "test-faction")

        assert result.is_error
        assert "not found" in result.error.lower()

    @pytest.mark.unit
    def test_select_intent_faction_mismatch(self, service, mock_repository):
        """Test selecting an intent from a different faction."""
        from src.contexts.world.domain.entities.faction_intent import FactionIntent

        intent = FactionIntent(
            faction_id="other-faction",
            action_type=ActionType.EXPAND,
            rationale="Test rationale",
            status=IntentStatus.PROPOSED,
        )
        mock_repository.find_by_id = MagicMock(return_value=intent)

        result = service.select_intent(intent.id, "test-faction")

        assert result.is_error
        assert "does not belong" in result.error.lower()

    @pytest.mark.unit
    def test_select_intent_mark_failed(self, service, mock_repository):
        """Test when repository fails to mark intent as selected."""
        from src.contexts.world.domain.entities.faction_intent import FactionIntent

        intent = FactionIntent(
            faction_id="test-faction",
            action_type=ActionType.EXPAND,
            rationale="Test rationale",
            status=IntentStatus.PROPOSED,
        )
        mock_repository.find_by_id = MagicMock(return_value=intent)
        mock_repository.mark_selected = MagicMock(return_value=False)

        result = service.select_intent(intent.id, "test-faction")

        assert result.is_error
        assert "failed" in result.error.lower()

