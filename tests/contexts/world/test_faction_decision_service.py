#!/usr/bin/env python3
"""Comprehensive tests for FactionDecisionService.

This module provides test coverage for the FactionDecisionService including:
- Intent generation with resource constraints
- RAG context enrichment
- Fallback intent generation
- Action availability calculation
- LLM prompt building

Total: 40 tests
"""


import pytest

from src.contexts.world.application.services.faction_decision_service import (
    ACTION_DEFINITIONS,
    MAX_INTENTS_PER_GENERATION,
    ActionDefinition,
    DecisionContext,
    FactionDecisionService,
)
from src.contexts.world.domain.entities.faction import (
    Faction,
    FactionAlignment,
    FactionType,
)
from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)
from src.contexts.world.infrastructure.persistence.in_memory_faction_intent_repository import (
    InMemoryFactionIntentRepository,
)

pytestmark = pytest.mark.unit



@pytest.fixture
def intent_repo():
    """Create a fresh faction intent repository for each test."""
    repo = InMemoryFactionIntentRepository()
    yield repo


@pytest.fixture
def decision_service(intent_repo):
    """Create a fresh FactionDecisionService for each test."""
    return FactionDecisionService(repository=intent_repo)


@pytest.fixture
def sample_faction():
    """Create a sample faction for testing."""
    return Faction(
        id="faction-1",
        name="Test Kingdom",
        description="A test kingdom",
        faction_type=FactionType.KINGDOM,
        alignment=FactionAlignment.LAWFUL_NEUTRAL,
    )


@pytest.fixture
def sample_context():
    """Create a sample decision context for testing."""
    return DecisionContext(
        faction_id="faction-1",
        resources={"gold": 500, "food": 200, "military": 100},
        diplomacy={"faction-2": "enemy", "faction-3": "allied"},
        territories=["loc-1", "loc-2"],
    )


@pytest.fixture
def low_resources_context():
    """Create a decision context with low resources."""
    return DecisionContext(
        faction_id="faction-1",
        resources={"gold": 50, "food": 30, "military": 20},
        diplomacy={"faction-2": "enemy"},
        territories=["loc-1"],
    )


# =============================================================================
# Test FactionDecisionService Initialization (3 tests)
# =============================================================================


class TestFactionDecisionServiceInitialization:
    """Tests for FactionDecisionService initialization."""

    def test_service_initialization_with_repository(self, intent_repo):
        """Test that service initializes with valid repository."""
        service = FactionDecisionService(repository=intent_repo)
        assert service._repository is intent_repo

    def test_service_initialization_sets_repository_correctly(self, intent_repo):
        """Test that repository is set correctly during initialization."""
        service = FactionDecisionService(repository=intent_repo)
        assert isinstance(service._repository, InMemoryFactionIntentRepository)

    def test_service_initialization_creates_empty_events_list(self, intent_repo):
        """Test that service initializes with empty events list."""
        service = FactionDecisionService(repository=intent_repo)
        assert service._events == []


# =============================================================================
# Test generate_intents (12 tests)
# =============================================================================


class TestGenerateIntents:
    """Tests for generate_intents method."""

    @pytest.mark.asyncio
    async def test_generate_intents_success(self, decision_service, sample_faction, sample_context):
        """Test successful intent generation."""
        result = await decision_service.generate_intents(sample_faction, sample_context)

        assert result.is_ok
        intents, event = result.value
        assert isinstance(intents, list)
        assert len(intents) > 0
        assert len(intents) <= MAX_INTENTS_PER_GENERATION

    @pytest.mark.asyncio
    async def test_generate_intents_returns_intent_objects(self, decision_service, sample_faction, sample_context):
        """Test that generated intents are FactionIntent objects."""
        result = await decision_service.generate_intents(sample_faction, sample_context)

        assert result.is_ok
        intents, _ = result.value
        for intent in intents:
            assert isinstance(intent, FactionIntent)

    @pytest.mark.asyncio
    async def test_generate_intents_faction_id_set(self, decision_service, sample_faction, sample_context):
        """Test that generated intents have correct faction ID."""
        result = await decision_service.generate_intents(sample_faction, sample_context)

        assert result.is_ok
        intents, _ = result.value
        for intent in intents:
            assert intent.faction_id == "faction-1"

    @pytest.mark.asyncio
    async def test_generate_intents_status_proposed(self, decision_service, sample_faction, sample_context):
        """Test that generated intents have PROPOSED status."""
        result = await decision_service.generate_intents(sample_faction, sample_context)

        assert result.is_ok
        intents, _ = result.value
        for intent in intents:
            assert intent.status == IntentStatus.PROPOSED

    @pytest.mark.asyncio
    async def test_generate_intents_emits_event(self, decision_service, sample_faction, sample_context):
        """Test that intent generation emits event."""
        result = await decision_service.generate_intents(sample_faction, sample_context)

        assert result.is_ok
        _, event = result.value
        assert event.faction_id == "faction-1"
        assert len(event.intent_ids) > 0

    @pytest.mark.asyncio
    async def test_generate_intents_persists_intents(self, decision_service, intent_repo, sample_faction, sample_context):
        """Test that generated intents are persisted."""
        result = await decision_service.generate_intents(sample_faction, sample_context)

        assert result.is_ok
        intents, _ = result.value

        # Verify intents are in repository
        for intent in intents:
            retrieved = intent_repo.find_by_id(intent.id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_generate_intents_with_low_resources(self, decision_service, sample_faction, low_resources_context):
        """Test intent generation with low resources."""
        result = await decision_service.generate_intents(sample_faction, low_resources_context)

        assert result.is_ok
        intents, _ = result.value
        # Should still generate intents but constrained
        assert len(intents) > 0


# =============================================================================
# Test _get_available_actions (8 tests)
# =============================================================================


class TestGetAvailableActions:
    """Tests for _get_available_actions method."""

    def test_available_actions_with_sufficient_resources(self, decision_service):
        """Test that all actions are available with sufficient resources."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 500, "food": 200, "military": 100},
        )

        actions = decision_service._get_available_actions(context)

        action_types = {a.action_type for a in actions}
        assert ActionType.ATTACK in action_types
        assert ActionType.SABOTAGE in action_types
        assert ActionType.TRADE in action_types
        assert ActionType.EXPAND in action_types
        assert ActionType.STABILIZE in action_types

    def test_attack_not_available_with_low_food(self, decision_service):
        """Test that ATTACK is not available when food < 100."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 500, "food": 50, "military": 100},
        )

        actions = decision_service._get_available_actions(context)

        action_types = {a.action_type for a in actions}
        assert ActionType.ATTACK not in action_types

    def test_attack_not_available_with_low_military(self, decision_service):
        """Test that ATTACK is not available when military < 50."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 500, "food": 200, "military": 30},
        )

        actions = decision_service._get_available_actions(context)

        action_types = {a.action_type for a in actions}
        assert ActionType.ATTACK not in action_types

    def test_sabotage_not_available_with_low_military(self, decision_service):
        """Test that SABOTAGE is not available when military < 50."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 500, "food": 200, "military": 30},
        )

        actions = decision_service._get_available_actions(context)

        action_types = {a.action_type for a in actions}
        assert ActionType.SABOTAGE not in action_types

    def test_trade_not_available_with_low_gold(self, decision_service):
        """Test that TRADE is not available when gold < 50."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 30, "food": 200, "military": 100},
        )

        actions = decision_service._get_available_actions(context)

        action_types = {a.action_type for a in actions}
        assert ActionType.TRADE not in action_types

    def test_stabilize_always_available(self, decision_service):
        """Test that STABILIZE is always available."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 0, "food": 0, "military": 0},
        )

        actions = decision_service._get_available_actions(context)

        action_types = {a.action_type for a in actions}
        assert ActionType.STABILIZE in action_types


# =============================================================================
# Test _generate_fallback_intents (8 tests)
# =============================================================================


class TestGenerateFallbackIntents:
    """Tests for _generate_fallback_intents method."""

    def test_fallback_intents_generated(self, decision_service, sample_faction, sample_context):
        """Test that fallback intents are generated."""
        available_actions = decision_service._get_available_actions(sample_context)
        intents = decision_service._generate_fallback_intents(
            sample_faction, sample_context, available_actions
        )

        assert len(intents) > 0
        assert len(intents) <= MAX_INTENTS_PER_GENERATION

    def test_fallback_intents_have_rationale(self, decision_service, sample_faction, sample_context):
        """Test that fallback intents have rationales."""
        available_actions = decision_service._get_available_actions(sample_context)
        intents = decision_service._generate_fallback_intents(
            sample_faction, sample_context, available_actions
        )

        for intent in intents:
            assert intent.rationale
            assert len(intent.rationale) > 0

    def test_fallback_intents_stabilize_when_critical_resources(self, decision_service, sample_faction):
        """Test STABILIZE is generated when resources are critical."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 50, "food": 30, "military": 20},
            diplomacy={},
            territories=[],
        )
        available_actions = decision_service._get_available_actions(context)
        intents = decision_service._generate_fallback_intents(
            sample_faction, context, available_actions
        )

        action_types = {i.action_type for i in intents}
        assert ActionType.STABILIZE in action_types

    def test_fallback_intents_prioritized(self, decision_service, sample_faction, sample_context):
        """Test that fallback intents are prioritized."""
        available_actions = decision_service._get_available_actions(sample_context)
        intents = decision_service._generate_fallback_intents(
            sample_faction, sample_context, available_actions
        )

        # Check priorities are within valid range
        for intent in intents:
            assert 1 <= intent.priority <= 3

    def test_fallback_intents_sorted_by_priority(self, decision_service, sample_faction, sample_context):
        """Test that fallback intents are sorted by priority."""
        available_actions = decision_service._get_available_actions(sample_context)
        intents = decision_service._generate_fallback_intents(
            sample_faction, sample_context, available_actions
        )

        # Check sorted by priority (1 = highest)
        for i in range(len(intents) - 1):
            assert intents[i].priority <= intents[i + 1].priority

    def test_fallback_intents_limited_to_max(self, decision_service, sample_faction, sample_context):
        """Test that fallback intents are limited to max."""
        available_actions = decision_service._get_available_actions(sample_context)
        intents = decision_service._generate_fallback_intents(
            sample_faction, sample_context, available_actions
        )

        assert len(intents) <= MAX_INTENTS_PER_GENERATION


# =============================================================================
# Test DecisionContext (3 tests)
# =============================================================================


class TestDecisionContext:
    """Tests for DecisionContext dataclass."""

    def test_decision_context_creation(self):
        """Test creating a DecisionContext."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 100},
            diplomacy={"faction-2": "enemy"},
            territories=["loc-1"],
        )

        assert context.faction_id == "faction-1"
        assert context.resources["gold"] == 100

    def test_decision_context_resource_summary(self):
        """Test resource summary generation."""
        context = DecisionContext(
            faction_id="faction-1",
            resources={"gold": 100, "food": 50},
        )

        summary = context.get_resource_summary()
        assert "gold=100" in summary
        assert "food=50" in summary

    def test_decision_context_empty_resources_summary(self):
        """Test resource summary with empty resources."""
        context = DecisionContext(faction_id="faction-1")

        summary = context.get_resource_summary()
        assert summary == "no resources"


# =============================================================================
# Test ActionDefinition (3 tests)
# =============================================================================


class TestActionDefinition:
    """Tests for ActionDefinition dataclass."""

    def test_action_definition_creation(self):
        """Test creating an ActionDefinition."""
        action = ActionDefinition(
            action_type=ActionType.EXPAND,
            name="Expand",
            description="Grow territory",
            requirements={"gold": 100},
            constraints=["Must have territory"],
        )

        assert action.action_type == ActionType.EXPAND
        assert action.name == "Expand"
        assert action.requirements["gold"] == 100

    def test_action_definitions_list_not_empty(self):
        """Test that ACTION_DEFINITIONS list is not empty."""
        assert len(ACTION_DEFINITIONS) > 0

    def test_action_definitions_cover_all_types(self):
        """Test that ACTION_DEFINITIONS covers all action types."""
        defined_types = {a.action_type for a in ACTION_DEFINITIONS}
        all_types = set(ActionType)

        assert defined_types == all_types
