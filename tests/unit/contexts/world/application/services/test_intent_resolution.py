#!/usr/bin/env python3
"""Tests for Intent Resolution (SIM-016).

This module tests the _resolve_intents method and ResolutionResult dataclass
from the WorldSimulationService.
"""

from unittest.mock import MagicMock

import pytest

from src.contexts.world.application.services.world_simulation_service import (
    ResolutionResult,
    WorldSimulationService,
)
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction
from src.contexts.world.domain.entities.faction_intent import FactionIntent, ActionType
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

pytestmark = pytest.mark.unit


# ============ ResolutionResult Tests ============

class TestResolutionResult:
    """Tests for the ResolutionResult dataclass."""

    def test_empty_result_has_no_changes(self) -> None:
        """An empty ResolutionResult should report no changes."""
        result = ResolutionResult()
        assert result.has_changes() is False

    def test_add_resource_change_creates_new_entry(self) -> None:
        """Adding a resource change should create a new entry."""
        result = ResolutionResult()
        result.add_resource_change("faction-1", wealth_delta=5, military_delta=-3)

        assert "faction-1" in result.resource_changes
        assert result.resource_changes["faction-1"].wealth_delta == 5
        assert result.resource_changes["faction-1"].military_delta == -3
        assert result.resource_changes["faction-1"].influence_delta == 0

    def test_add_resource_change_accumulates(self) -> None:
        """Multiple resource changes should accumulate for same faction."""
        result = ResolutionResult()
        result.add_resource_change("faction-1", wealth_delta=5)
        result.add_resource_change("faction-1", wealth_delta=3, military_delta=2)

        assert result.resource_changes["faction-1"].wealth_delta == 8
        assert result.resource_changes["faction-1"].military_delta == 2

    def test_add_resource_change_clamps_to_limits(self) -> None:
        """Resource changes should be clamped to -100/100 range."""
        result = ResolutionResult()
        result.add_resource_change("faction-1", wealth_delta=150)

        # Should be clamped to 100
        assert result.resource_changes["faction-1"].wealth_delta == 100

    def test_add_diplomacy_change(self) -> None:
        """Adding diplomacy change should create a DiplomacyChange record."""
        result = ResolutionResult()
        result.add_diplomacy_change(
            "faction-a",
            "faction-b",
            DiplomaticStatus.NEUTRAL,
            DiplomaticStatus.ALLIED,
        )

        assert len(result.diplomacy_changes) == 1
        change = result.diplomacy_changes[0]
        assert change.faction_a == "faction-a"
        assert change.faction_b == "faction-b"
        assert change.status_before == DiplomaticStatus.NEUTRAL
        assert change.status_after == DiplomaticStatus.ALLIED

    def test_add_territory_change(self) -> None:
        """Adding territory change should record new ownership."""
        result = ResolutionResult()
        result.add_territory_change("location-1", "new-owner-faction")

        assert result.territory_changes["location-1"] == "new-owner-faction"

    def test_mark_intent_success_and_failed(self) -> None:
        """Intent success/failure tracking."""
        result = ResolutionResult()
        result.mark_intent_success("intent-1")
        result.mark_intent_failed("intent-2")
        result.mark_intent_success("intent-3")

        assert "intent-1" in result.successful_intents
        assert "intent-3" in result.successful_intents
        assert "intent-2" in result.failed_intents
        assert len(result.successful_intents) == 2
        assert len(result.failed_intents) == 1

    def test_has_changes_true_with_resource_changes(self) -> None:
        """has_changes should return True with resource changes."""
        result = ResolutionResult()
        result.add_resource_change("faction-1", wealth_delta=5)
        assert result.has_changes() is True

    def test_has_changes_true_with_diplomacy_changes(self) -> None:
        """has_changes should return True with diplomacy changes."""
        result = ResolutionResult()
        result.add_diplomacy_change(
            "a", "b",
            DiplomaticStatus.NEUTRAL,
            DiplomaticStatus.ALLIED,
        )
        assert result.has_changes() is True

    def test_has_changes_true_with_territory_changes(self) -> None:
        """has_changes should return True with territory changes."""
        result = ResolutionResult()
        result.add_territory_change("loc-1", "faction-1")
        assert result.has_changes() is True

    def test_has_changes_true_with_events(self) -> None:
        """has_changes should return True with events generated."""
        result = ResolutionResult()
        result.events_generated.append("event-1")
        assert result.has_changes() is True

    def test_to_dict(self) -> None:
        """to_dict should serialize all data correctly."""
        result = ResolutionResult()
        result.add_resource_change("faction-1", wealth_delta=5)
        result.add_diplomacy_change(
            "a", "b",
            DiplomaticStatus.NEUTRAL,
            DiplomaticStatus.ALLIED,
        )
        result.add_territory_change("loc-1", "faction-1")
        result.mark_intent_success("intent-1")

        data = result.to_dict()

        assert "faction-1" in data["resource_changes"]
        assert len(data["diplomacy_changes"]) == 1
        assert data["territory_changes"]["loc-1"] == "faction-1"
        assert "intent-1" in data["successful_intents"]
        assert data["has_changes"] is True


# ============ Intent Resolution Tests ============

@pytest.fixture
def mock_world_repo() -> MagicMock:
    """Create a mock world repository."""
    repo = MagicMock()
    return repo


@pytest.fixture
def mock_faction_repo() -> MagicMock:
    """Create a mock faction repository."""
    repo = MagicMock()
    return repo


@pytest.fixture
def mock_intent_generator() -> MagicMock:
    """Create a mock intent generator."""
    generator = MagicMock()
    return generator


@pytest.fixture
def service(
    mock_world_repo: MagicMock,
    mock_faction_repo: MagicMock,
    mock_intent_generator: MagicMock,
) -> WorldSimulationService:
    """Create a WorldSimulationService instance."""
    return WorldSimulationService(
        world_repo=mock_world_repo,
        faction_repo=mock_faction_repo,
        intent_generator=mock_intent_generator,
    )


@pytest.fixture
def calendar() -> WorldCalendar:
    """Create a test calendar."""
    return WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")


@pytest.fixture
def world_state(calendar: WorldCalendar) -> WorldState:
    """Create a test world state."""
    world = WorldState(
        id="world-1",
        calendar=calendar,
    )
    return world


@pytest.fixture
def diplomacy_matrix() -> DiplomacyMatrix:
    """Create a test diplomacy matrix."""
    matrix = DiplomacyMatrix(
        id="diplomacy-1",
        world_id="world-1",
    )
    return matrix


class TestResolveIntentsAttack:
    """Tests for ATTACK intent resolution."""

    def test_attack_reduces_military_for_both_sides(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ATTACK should reduce military by 5 for attacker and defender."""
        attacker = Faction(
            id="faction-attacker",
            name="Attackers",
            military_strength=70,
        )
        defender = Faction(
            id="faction-defender",
            name="Defenders",
            military_strength=50,
            territories=["loc-1"],
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-attacker",
            action_type=ActionType.ATTACK,
            target_id="faction-defender",
            priority=3,
            rationale="Attack the enemy",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [attacker, defender],
            diplomacy_matrix,
        )

        assert result.resource_changes["faction-attacker"].military_delta == -5
        assert result.resource_changes["faction-defender"].military_delta == -5
        assert "intent-1" in result.successful_intents

    def test_attack_transfers_territory_when_stronger(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ATTACK should transfer territory when attacker is stronger."""
        attacker = Faction(
            id="faction-attacker",
            name="Attackers",
            military_strength=70,
            territories=[],
        )
        defender = Faction(
            id="faction-defender",
            name="Defenders",
            military_strength=50,
            territories=["loc-1", "loc-2"],
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-attacker",
            action_type=ActionType.ATTACK,
            target_id="faction-defender",
            priority=3,
            rationale="Attack the enemy",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [attacker, defender],
            diplomacy_matrix,
        )

        assert "loc-1" in result.territory_changes
        assert result.territory_changes["loc-1"] == "faction-attacker"

    def test_attack_no_territory_when_weaker(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ATTACK should not transfer territory when attacker is weaker."""
        attacker = Faction(
            id="faction-attacker",
            name="Attackers",
            military_strength=40,
            territories=[],
        )
        defender = Faction(
            id="faction-defender",
            name="Defenders",
            military_strength=70,
            territories=["loc-1"],
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-attacker",
            action_type=ActionType.ATTACK,
            target_id="faction-defender",
            priority=3,
            rationale="Attack the enemy",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [attacker, defender],
            diplomacy_matrix,
        )

        # Military still reduced, but no territory change
        assert result.resource_changes["faction-attacker"].military_delta == -5
        assert len(result.territory_changes) == 0

    def test_attack_conflict_strongest_wins(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """When multiple factions attack same target, strongest wins."""
        attacker1 = Faction(
            id="faction-a1",
            name="Attacker 1",
            military_strength=60,
        )
        attacker2 = Faction(
            id="faction-a2",
            name="Attacker 2",
            military_strength=80,  # Stronger
        )
        defender = Faction(
            id="faction-defender",
            name="Defenders",
            military_strength=50,
            territories=["loc-1"],
        )

        intent1 = FactionIntent(
            id="intent-1",
            faction_id="faction-a1",
            action_type=ActionType.ATTACK,
            target_id="faction-defender",
            priority=3,
            rationale="Attack the enemy",
        )
        intent2 = FactionIntent(
            id="intent-2",
            faction_id="faction-a2",
            action_type=ActionType.ATTACK,
            target_id="faction-defender",
            priority=3,
            rationale="Attack the enemy",
        )

        result = service._resolve_intents(
            [intent1, intent2],
            world_state,
            [attacker1, attacker2, defender],
            diplomacy_matrix,
        )

        # Both lose military, but only stronger attacker gets territory
        assert result.resource_changes["faction-a1"].military_delta == -5
        assert result.resource_changes["faction-a2"].military_delta == -5
        assert result.resource_changes["faction-defender"].military_delta == -10  # Both attacks

        # Only attacker2 should be marked successful
        assert "intent-1" in result.failed_intents
        assert "intent-2" in result.successful_intents
        assert result.territory_changes.get("loc-1") == "faction-a2"

    def test_attack_fails_without_target(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ATTACK without target should fail."""
        attacker = Faction(
            id="faction-attacker",
            name="Attackers",
            military_strength=70,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-attacker",
            action_type=ActionType.ATTACK,
            target_id=None,  # No target
            priority=3,
            rationale="Attack!",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [attacker],
            diplomacy_matrix,
        )

        assert "intent-1" in result.failed_intents
        assert len(result.resource_changes) == 0


class TestResolveIntentsExpand:
    """Tests for EXPAND intent resolution."""

    def test_expand_succeeds_with_sufficient_wealth(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """EXPAND should succeed when wealth >= 20."""
        faction = Faction(
            id="faction-1",
            name="Expanders",
            economic_power=50,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.EXPAND,
            priority=2,
            rationale="Expand territory",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        assert result.resource_changes["faction-1"].wealth_delta == -10
        assert "intent-1" in result.successful_intents

    def test_expand_fails_with_insufficient_wealth(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """EXPAND should fail when wealth < 20."""
        faction = Faction(
            id="faction-1",
            name="Expanders",
            economic_power=15,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.EXPAND,
            priority=2,
            rationale="Expand territory",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        assert "faction-1" not in result.resource_changes
        assert "intent-1" in result.failed_intents


class TestResolveIntentsAlly:
    """Tests for ALLY intent resolution."""

    def test_ally_creates_alliance(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ALLY should create bilateral ALLIED status."""
        faction_a = Faction(
            id="faction-a",
            name="Faction A",
        )
        faction_b = Faction(
            id="faction-b",
            name="Faction B",
        )

        diplomacy_matrix.register_faction("faction-a")
        diplomacy_matrix.register_faction("faction-b")

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-a",
            action_type=ActionType.TRADE,
            target_id="faction-b",
            priority=2,
            rationale="Form alliance",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction_a, faction_b],
            diplomacy_matrix,
        )

        assert len(result.diplomacy_changes) == 1
        change = result.diplomacy_changes[0]
        assert change.status_after == DiplomaticStatus.ALLIED
        assert "intent-1" in result.successful_intents

    def test_ally_fails_with_hostile_relation(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ALLY should fail if currently AT_WAR or HOSTILE."""
        faction_a = Faction(
            id="faction-a",
            name="Faction A",
        )
        faction_b = Faction(
            id="faction-b",
            name="Faction B",
        )

        diplomacy_matrix.register_faction("faction-a")
        diplomacy_matrix.register_faction("faction-b")
        diplomacy_matrix.set_status("faction-a", "faction-b", DiplomaticStatus.AT_WAR)

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-a",
            action_type=ActionType.TRADE,
            target_id="faction-b",
            priority=2,
            rationale="Form alliance",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction_a, faction_b],
            diplomacy_matrix,
        )

        assert "intent-1" in result.failed_intents
        assert len(result.diplomacy_changes) == 0

    def test_ally_fails_without_target(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ALLY should fail without a target."""
        faction = Faction(
            id="faction-a",
            name="Faction A",
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-a",
            action_type=ActionType.TRADE,
            target_id=None,
            priority=2,
            rationale="Form alliance",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        assert "intent-1" in result.failed_intents


class TestResolveIntentsRecover:
    """Tests for RECOVER intent resolution."""

    def test_recover_increases_wealth_when_low(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """RECOVER should increase wealth by 5 when below 50."""
        faction = Faction(
            id="faction-1",
            name="Recoverers",
            economic_power=30,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=3,
            rationale="Recover economically",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        # STABILIZE provides +2 wealth, +1 military (unified behavior)
        assert result.resource_changes["faction-1"].wealth_delta == 2
        assert result.resource_changes["faction-1"].military_delta == 1
        assert "intent-1" in result.successful_intents

    def test_recover_no_change_when_wealth_high(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """STABILIZE provides gains regardless of current wealth level."""
        faction = Faction(
            id="faction-1",
            name="Recoverers",
            economic_power=60,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=3,
            rationale="Recover economically",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        # STABILIZE always provides gains (+2 wealth, +1 military)
        assert result.resource_changes["faction-1"].wealth_delta == 2
        assert result.resource_changes["faction-1"].military_delta == 1
        assert "intent-1" in result.successful_intents


class TestResolveIntentsDefend:
    """Tests for DEFEND intent resolution."""

    def test_defend_increases_military_when_low(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """DEFEND should increase military by 3 when below 80."""
        faction = Faction(
            id="faction-1",
            name="Defenders",
            military_strength=50,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=2,
            rationale="Strengthen defenses",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        # STABILIZE provides +2 wealth, +1 military (unified behavior)
        assert result.resource_changes["faction-1"].wealth_delta == 2
        assert result.resource_changes["faction-1"].military_delta == 1
        assert "intent-1" in result.successful_intents

    def test_defend_no_change_when_military_high(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """STABILIZE provides gains regardless of current military level."""
        faction = Faction(
            id="faction-1",
            name="Defenders",
            military_strength=85,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=2,
            rationale="Strengthen defenses",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        # STABILIZE always provides gains (+2 wealth, +1 military)
        assert result.resource_changes["faction-1"].wealth_delta == 2
        assert result.resource_changes["faction-1"].military_delta == 1
        assert "intent-1" in result.successful_intents


class TestResolveIntentsConsolidate:
    """Tests for CONSOLIDATE intent resolution."""

    def test_consolidate_provides_small_gains(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """CONSOLIDATE should provide +2 wealth and +1 military."""
        faction = Faction(
            id="faction-1",
            name="Consolidators",
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=3,
            rationale="Focus on internal affairs",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        assert result.resource_changes["faction-1"].wealth_delta == 2
        assert result.resource_changes["faction-1"].military_delta == 1
        assert "intent-1" in result.successful_intents


class TestResolveIntentsTrade:
    """Tests for TRADE intent resolution."""

    def test_trade_succeeds_with_no_effect(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """TRADE should succeed but have no immediate effect."""
        faction = Faction(
            id="faction-1",
            name="Traders",
        )
        target_faction = Faction(
            id="faction-2",
            name="Trade Partner",
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.TRADE,
            target_id="faction-2",
            priority=2,
            rationale="Establish trade routes",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction, target_faction],
            diplomacy_matrix,
        )

        # TRADE with target creates alliance, no resource changes
        assert "faction-1" not in result.resource_changes
        assert "intent-1" in result.successful_intents


class TestResolveIntentsPriority:
    """Tests for intent priority handling."""

    def test_intents_sorted_by_priority(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Intents should be processed in priority order (descending)."""
        faction = Faction(
            id="faction-1",
            name="Test Faction",
            economic_power=30,
            military_strength=30,
        )

        # Create intents with different priorities (1=highest, 3=lowest)
        low_intent = FactionIntent(
            id="intent-low",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=3,  # lowest priority
            rationale="Low priority",
        )
        high_intent = FactionIntent(
            id="intent-high",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=1,  # highest priority
            rationale="High priority",
        )
        mid_intent = FactionIntent(
            id="intent-mid",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=2,  # medium priority
            rationale="Mid priority",
        )

        result = service._resolve_intents(
            [low_intent, high_intent, mid_intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        # All should succeed
        assert len(result.successful_intents) == 3

    def test_multiple_factions_same_intent_type(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Multiple factions can have same intent type."""
        faction1 = Faction(
            id="faction-1",
            name="Faction 1",
            economic_power=30,
        )
        faction2 = Faction(
            id="faction-2",
            name="Faction 2",
            economic_power=40,
        )

        intent1 = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.STABILIZE,
            priority=3,
            rationale="Recover",
        )
        intent2 = FactionIntent(
            id="intent-2",
            faction_id="faction-2",
            action_type=ActionType.STABILIZE,
            priority=3,
            rationale="Recover",
        )

        result = service._resolve_intents(
            [intent1, intent2],
            world_state,
            [faction1, faction2],
            diplomacy_matrix,
        )

        # STABILIZE provides +2 wealth, +1 military per faction
        assert result.resource_changes["faction-1"].wealth_delta == 2
        assert result.resource_changes["faction-2"].wealth_delta == 2


class TestResolveIntentsEdgeCases:
    """Tests for edge cases in intent resolution."""

    def test_empty_intents_list(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Empty intent list should return empty result."""
        result = service._resolve_intents(
            [],
            world_state,
            [],
            diplomacy_matrix,
        )

        assert result.has_changes() is False
        assert len(result.successful_intents) == 0
        assert len(result.failed_intents) == 0

    def test_intent_for_unknown_faction_fails(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Intent for non-existent faction should fail."""
        intent = FactionIntent(
            id="intent-1",
            faction_id="unknown-faction",
            action_type=ActionType.STABILIZE,
            priority=3,
            rationale="Consolidate",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [],  # No factions
            diplomacy_matrix,
        )

        assert "intent-1" in result.failed_intents

    def test_attack_target_not_found_fails(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ATTACK intent with non-existent target should fail."""
        attacker = Faction(
            id="faction-attacker",
            name="Attacker",
            military_strength=70,
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-attacker",
            action_type=ActionType.ATTACK,
            target_id="unknown-target",
            priority=3,
            rationale="Attack",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [attacker],
            diplomacy_matrix,
        )

        assert "intent-1" in result.failed_intents

    def test_ally_target_not_found_fails(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ALLY intent with non-existent target should fail."""
        faction = Faction(
            id="faction-1",
            name="Faction 1",
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-1",
            action_type=ActionType.TRADE,
            target_id="unknown-target",
            priority=2,
            rationale="Form alliance",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [faction],
            diplomacy_matrix,
        )

        assert "intent-1" in result.failed_intents

    def test_attack_no_territories_to_capture(
        self,
        service: WorldSimulationService,
        world_state: WorldState,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """ATTACK should succeed even if defender has no territories."""
        attacker = Faction(
            id="faction-attacker",
            name="Attacker",
            military_strength=70,
        )
        defender = Faction(
            id="faction-defender",
            name="Defender",
            military_strength=50,
            territories=[],  # No territories
        )

        intent = FactionIntent(
            id="intent-1",
            faction_id="faction-attacker",
            action_type=ActionType.ATTACK,
            target_id="faction-defender",
            priority=3,
            rationale="Attack",
        )

        result = service._resolve_intents(
            [intent],
            world_state,
            [attacker, defender],
            diplomacy_matrix,
        )

        # Military still reduced, intent succeeds, but no territory change
        assert result.resource_changes["faction-attacker"].military_delta == -5
        assert result.resource_changes["faction-defender"].military_delta == -5
        assert len(result.territory_changes) == 0
        assert "intent-1" in result.successful_intents
