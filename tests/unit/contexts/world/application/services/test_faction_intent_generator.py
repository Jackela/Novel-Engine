#!/usr/bin/env python3
"""
Unit tests for FactionIntentGenerator Service

Comprehensive test suite for the FactionIntentGenerator service covering
all rule-based decision logic, edge cases, and intent prioritization.
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()


# Create mock event bus classes for testing
class MockEventPriority(Enum):
    """Mock EventPriority for testing."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockEvent:
    """Mock Event class that supports dataclass functionality."""
    event_id: str = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    priority: MockEventPriority = MockEventPriority.NORMAL
    timestamp: datetime = None
    tags: Set = field(default_factory=set)
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MockEventBusModule:
    Event = MockEvent
    EventPriority = MockEventPriority


# Save original module if it exists
_original_event_bus = sys.modules.get("src.events.event_bus")
sys.modules["src.events.event_bus"] = MockEventBusModule()

# Import after mocking
from src.contexts.world.application.services.faction_intent_generator import (
    FactionIntentGenerator,
)
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import (
    Faction,
    FactionStatus,
)
from src.contexts.world.domain.entities.faction_intent import IntentType
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

# Restore original module to avoid polluting other tests
if _original_event_bus is not None:
    sys.modules["src.events.event_bus"] = _original_event_bus
else:
    del sys.modules["src.events.event_bus"]


class TestFactionIntentGenerator:
    """Test suite for FactionIntentGenerator."""

    @pytest.fixture
    def generator(self) -> FactionIntentGenerator:
        """Create a FactionIntentGenerator instance."""
        return FactionIntentGenerator()

    @pytest.fixture
    def world(self) -> WorldState:
        """Create a basic WorldState for testing."""
        return WorldState(
            id="world-test",
            name="Test World",
            calendar=WorldCalendar(year=100, month=1, day=1, era_name="Test Age"),
        )

    @pytest.fixture
    def diplomacy(self) -> DiplomacyMatrix:
        """Create a basic DiplomacyMatrix for testing."""
        matrix = DiplomacyMatrix(id="diplo-test", world_id="world-test")
        return matrix

    @pytest.fixture
    def wealthy_faction(self) -> Faction:
        """Create a wealthy faction for testing."""
        return Faction(
            id="faction-wealthy",
            name="Wealthy Kingdom",
            economic_power=80,
            military_strength=60,
            influence=70,
            territories=["territory-1", "territory-2"],
        )

    @pytest.fixture
    def poor_faction(self) -> Faction:
        """Create a poor faction for testing."""
        return Faction(
            id="faction-poor",
            name="Poor Kingdom",
            economic_power=10,
            military_strength=30,
            influence=20,
            territories=["territory-3"],
        )

    @pytest.fixture
    def military_faction(self) -> Faction:
        """Create a militarily strong faction."""
        return Faction(
            id="faction-military",
            name="Military Power",
            economic_power=50,
            military_strength=90,
            influence=60,
            territories=["territory-4"],
        )

    # === Edge Case Tests ===

    @pytest.mark.integration
    def test_collapsed_faction_returns_empty_list(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that a disbanded faction returns no intents."""
        faction = Faction(
            id="faction-dead",
            name="Dead Faction",
            status=FactionStatus.DISBANDED,
        )

        intents = generator.generate_intents(faction, world, diplomacy)

        assert intents == []

    # === Rule 1: RECOVER Intent Tests ===

    @pytest.mark.integration
    def test_low_wealth_triggers_recover_intent(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that low wealth (< 20) generates RECOVER intent."""
        faction = Faction(
            id="faction-poor",
            name="Poor Faction",
            economic_power=15,
            military_strength=50,
        )

        intents = generator.generate_intents(faction, world, diplomacy)

        assert len(intents) >= 1
        assert intents[0].intent_type == IntentType.RECOVER
        assert intents[0].priority == 9
        assert "economic" in intents[0].narrative.lower()

    @pytest.mark.integration
    def test_recover_intent_priority_highest(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that RECOVER intent has highest priority when triggered."""
        faction = Faction(
            id="faction-poor",
            name="Poor Faction",
            economic_power=10,
            military_strength=90,
        )
        diplomacy.set_status(faction.id, "enemy-faction", DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        # RECOVER should be first (highest priority = 9)
        assert intents[0].intent_type == IntentType.RECOVER
        assert intents[0].priority == 9

    # === Rule 2: ATTACK Intent Tests ===

    @pytest.mark.integration
    def test_attack_intent_with_weak_enemy(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test ATTACK intent when faction has enemies and sufficient military."""
        faction = Faction(
            id="faction-strong",
            name="Strong Faction",
            economic_power=60,
            military_strength=70,
        )
        enemy_id = "enemy-faction"
        diplomacy.set_status(faction.id, enemy_id, DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        attack_intents = [i for i in intents if i.intent_type == IntentType.ATTACK]
        assert len(attack_intents) == 1
        assert attack_intents[0].target_id == enemy_id
        assert attack_intents[0].priority == 7

    @pytest.mark.integration
    def test_no_attack_without_enemies(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no ATTACK intent when faction has no enemies."""
        faction = Faction(
            id="faction-isolated",
            name="Isolated Faction",
            economic_power=60,
            military_strength=70,
        )
        # No enemies set

        intents = generator.generate_intents(faction, world, diplomacy)

        attack_intents = [i for i in intents if i.intent_type == IntentType.ATTACK]
        assert len(attack_intents) == 0

    @pytest.mark.integration
    def test_no_attack_with_low_military(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no ATTACK intent when military strength is low (< 30)."""
        faction = Faction(
            id="faction-weak",
            name="Weak Faction",
            economic_power=60,
            military_strength=20,
        )
        diplomacy.set_status(faction.id, "enemy-faction", DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        attack_intents = [i for i in intents if i.intent_type == IntentType.ATTACK]
        assert len(attack_intents) == 0

    # === Rule 3: ALLY Intent Tests ===

    @pytest.mark.integration
    def test_ally_intent_isolated_and_wealthy(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test ALLY intent when faction is isolated and wealthy."""
        faction = Faction(
            id="faction-isolated",
            name="Isolated Faction",
            economic_power=70,
            military_strength=40,
        )
        neutral_faction = "neutral-faction"
        diplomacy.set_status(faction.id, neutral_faction, DiplomaticStatus.NEUTRAL)

        intents = generator.generate_intents(faction, world, diplomacy)

        ally_intents = [i for i in intents if i.intent_type == IntentType.ALLY]
        assert len(ally_intents) == 1
        assert ally_intents[0].target_id == neutral_faction
        assert ally_intents[0].priority == 6

    @pytest.mark.integration
    def test_no_ally_intent_with_existing_allies(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no ALLY intent when faction already has allies."""
        faction = Faction(
            id="faction-allied",
            name="Allied Faction",
            economic_power=70,
            military_strength=40,
        )
        diplomacy.set_status(faction.id, "ally-faction", DiplomaticStatus.ALLIED)

        intents = generator.generate_intents(faction, world, diplomacy)

        ally_intents = [i for i in intents if i.intent_type == IntentType.ALLY]
        assert len(ally_intents) == 0

    @pytest.mark.integration
    def test_no_ally_intent_without_wealth(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no ALLY intent when faction lacks wealth."""
        faction = Faction(
            id="faction-poor",
            name="Poor Faction",
            economic_power=30,  # <= 40
            military_strength=40,
        )
        diplomacy.set_status(faction.id, "neutral-faction", DiplomaticStatus.NEUTRAL)

        intents = generator.generate_intents(faction, world, diplomacy)

        ally_intents = [i for i in intents if i.intent_type == IntentType.ALLY]
        assert len(ally_intents) == 0

    # === Rule 4: EXPAND Intent Tests ===

    @pytest.mark.integration
    def test_expand_intent_few_territories_and_wealthy(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test EXPAND intent when faction has few territories and wealth."""
        faction = Faction(
            id="faction-expanding",
            name="Expanding Faction",
            economic_power=70,
            military_strength=40,
            territories=["territory-1"],  # Only 1 territory (< 3)
        )

        intents = generator.generate_intents(faction, world, diplomacy)

        expand_intents = [i for i in intents if i.intent_type == IntentType.EXPAND]
        assert len(expand_intents) == 1
        assert expand_intents[0].priority == 5
        assert "expand" in expand_intents[0].narrative.lower()

    @pytest.mark.integration
    def test_no_expand_with_many_territories(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no EXPAND intent when faction has 3+ territories."""
        faction = Faction(
            id="faction-large",
            name="Large Faction",
            economic_power=70,
            territories=["t1", "t2", "t3"],  # 3 territories
        )

        intents = generator.generate_intents(faction, world, diplomacy)

        expand_intents = [i for i in intents if i.intent_type == IntentType.EXPAND]
        assert len(expand_intents) == 0

    @pytest.mark.integration
    def test_no_expand_without_wealth(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no EXPAND intent when faction lacks wealth."""
        faction = Faction(
            id="faction-poor",
            name="Poor Faction",
            economic_power=40,  # <= 50
            territories=["t1"],
        )

        intents = generator.generate_intents(faction, world, diplomacy)

        expand_intents = [i for i in intents if i.intent_type == IntentType.EXPAND]
        assert len(expand_intents) == 0

    # === Rule 5: DEFEND Intent Tests ===

    @pytest.mark.integration
    def test_defend_intent_strong_military_with_enemies(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test DEFEND intent when military > 80 and has enemies."""
        faction = Faction(
            id="faction-military",
            name="Military Faction",
            economic_power=50,
            military_strength=90,  # > 80
            territories=["border-territory"],
        )
        diplomacy.set_status(faction.id, "enemy-faction", DiplomaticStatus.AT_WAR)

        intents = generator.generate_intents(faction, world, diplomacy)

        defend_intents = [i for i in intents if i.intent_type == IntentType.DEFEND]
        assert len(defend_intents) == 1
        assert defend_intents[0].priority == 4
        assert "defens" in defend_intents[0].narrative.lower()  # matches "defensive" or "defend"

    @pytest.mark.integration
    def test_no_defend_without_enemies(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no DEFEND intent when faction has no enemies."""
        faction = Faction(
            id="faction-peaceful",
            name="Peaceful Faction",
            military_strength=90,
        )
        # No enemies

        intents = generator.generate_intents(faction, world, diplomacy)

        defend_intents = [i for i in intents if i.intent_type == IntentType.DEFEND]
        assert len(defend_intents) == 0

    @pytest.mark.integration
    def test_no_defend_with_low_military(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test no DEFEND intent when military strength is not > 80."""
        faction = Faction(
            id="faction-average",
            name="Average Faction",
            military_strength=70,
        )
        diplomacy.set_status(faction.id, "enemy-faction", DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        defend_intents = [i for i in intents if i.intent_type == IntentType.DEFEND]
        assert len(defend_intents) == 0

    # === Rule 6: Default CONSOLIDATE Intent Tests ===

    @pytest.mark.integration
    def test_default_consolidate_intent(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test CONSOLIDATE intent as default when no other rules match."""
        faction = Faction(
            id="faction-normal",
            name="Normal Faction",
            economic_power=50,  # Not low, not high enough for expand
            military_strength=50,  # Not strong enough for defend
            territories=["t1", "t2", "t3"],  # Enough territories
        )
        # No allies, no enemies

        intents = generator.generate_intents(faction, world, diplomacy)

        assert len(intents) == 1
        assert intents[0].intent_type == IntentType.CONSOLIDATE
        assert intents[0].priority == 1
        assert "internal" in intents[0].narrative.lower()

    # === Max Intents and Priority Tests ===

    @pytest.mark.integration
    def test_max_three_intents_returned(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that at most 3 intents are returned."""
        faction = Faction(
            id="faction-active",
            name="Active Faction",
            economic_power=15,  # Triggers RECOVER
            military_strength=90,  # Triggers DEFEND
            territories=["t1"],  # Triggers EXPAND
        )
        diplomacy.set_status(faction.id, "enemy", DiplomaticStatus.HOSTILE)
        diplomacy.set_status(faction.id, "neutral", DiplomaticStatus.NEUTRAL)

        intents = generator.generate_intents(faction, world, diplomacy)

        assert len(intents) <= 3

    @pytest.mark.integration
    def test_intents_sorted_by_priority_descending(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that intents are sorted by priority (highest first)."""
        faction = Faction(
            id="faction-active",
            name="Active Faction",
            economic_power=10,  # Triggers RECOVER (priority 9)
            military_strength=90,  # Triggers DEFEND (priority 4)
            territories=["t1"],  # Triggers EXPAND (priority 5)
        )
        diplomacy.set_status(faction.id, "enemy", DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        # Should be sorted: RECOVER (9), EXPAND (5), DEFEND (4)
        priorities = [i.priority for i in intents]
        assert priorities == sorted(priorities, reverse=True)

    # === Integration Tests ===

    @pytest.mark.integration
    def test_multiple_intents_generated(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that multiple intents can be generated for a faction."""
        faction = Faction(
            id="faction-complex",
            name="Complex Faction",
            economic_power=60,
            military_strength=85,
            territories=["t1"],
        )
        diplomacy.set_status(faction.id, "enemy", DiplomaticStatus.HOSTILE)
        diplomacy.set_status(faction.id, "neutral", DiplomaticStatus.NEUTRAL)

        intents = generator.generate_intents(faction, world, diplomacy)

        # Should generate multiple intents: EXPAND, DEFEND, possibly more
        assert len(intents) >= 2

    @pytest.mark.integration
    def test_intent_faction_id_matches(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that all intents have correct faction_id."""
        faction = Faction(
            id="faction-test-123",
            name="Test Faction",
            economic_power=10,
        )

        intents = generator.generate_intents(faction, world, diplomacy)

        for intent in intents:
            assert intent.faction_id == "faction-test-123"

    # === Properties Tests ===

    @pytest.mark.integration
    def test_attack_is_offensive(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that ATTACK intents are marked as offensive."""
        faction = Faction(
            id="faction-aggressive",
            name="Aggressive Faction",
            military_strength=70,
        )
        diplomacy.set_status(faction.id, "enemy", DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        attack_intents = [i for i in intents if i.intent_type == IntentType.ATTACK]
        if attack_intents:
            assert attack_intents[0].is_offensive is True
            assert attack_intents[0].is_defensive is False

    @pytest.mark.integration
    def test_defend_is_defensive(
        self, generator: FactionIntentGenerator, world: WorldState, diplomacy: DiplomacyMatrix
    ):
        """Test that DEFEND intents are marked as defensive."""
        faction = Faction(
            id="faction-defensive",
            name="Defensive Faction",
            military_strength=90,
        )
        diplomacy.set_status(faction.id, "enemy", DiplomaticStatus.HOSTILE)

        intents = generator.generate_intents(faction, world, diplomacy)

        defend_intents = [i for i in intents if i.intent_type == IntentType.DEFEND]
        if defend_intents:
            assert defend_intents[0].is_defensive is True
            assert defend_intents[0].is_offensive is False
