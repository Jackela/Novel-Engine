#!/usr/bin/env python3
"""
Unit tests for SimulationTick Value Objects

Comprehensive test suite for SimulationTick, ResourceChanges, and DiplomacyChange
value objects covering validation, properties, and serialization.
"""

from datetime import datetime
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.simulation_tick import (
    DiplomacyChange,
    ResourceChanges,
    SimulationTick,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


class TestResourceChanges:
    """Test suite for ResourceChanges value object."""

    @pytest.mark.unit
    def test_create_with_all_values(self):
        """Test creating ResourceChanges with all values."""
        changes = ResourceChanges(
            wealth_delta=10,
            military_delta=-5,
            influence_delta=3,
        )

        assert changes.wealth_delta == 10
        assert changes.military_delta == -5
        assert changes.influence_delta == 3

    @pytest.mark.unit
    def test_create_with_defaults(self):
        """Test creating ResourceChanges with defaults."""
        changes = ResourceChanges()

        assert changes.wealth_delta == 0
        assert changes.military_delta == 0
        assert changes.influence_delta == 0

    @pytest.mark.unit
    def test_validation_wealth_delta_out_of_range(self):
        """Test validation fails for wealth delta out of range."""
        with pytest.raises(ValueError, match="Wealth delta must be -100 to 100"):
            ResourceChanges(wealth_delta=150)

        with pytest.raises(ValueError, match="Wealth delta must be -100 to 100"):
            ResourceChanges(wealth_delta=-150)

    @pytest.mark.unit
    def test_validation_military_delta_out_of_range(self):
        """Test validation fails for military delta out of range."""
        with pytest.raises(ValueError, match="Military delta must be -100 to 100"):
            ResourceChanges(military_delta=200)

    @pytest.mark.unit
    def test_validation_influence_delta_out_of_range(self):
        """Test validation fails for influence delta out of range."""
        with pytest.raises(ValueError, match="Influence delta must be -100 to 100"):
            ResourceChanges(influence_delta=-200)

    @pytest.mark.unit
    def test_has_changes_true(self):
        """Test has_changes returns True when any delta is non-zero."""
        assert ResourceChanges(wealth_delta=5).has_changes is True
        assert ResourceChanges(military_delta=-3).has_changes is True
        assert ResourceChanges(influence_delta=1).has_changes is True

    @pytest.mark.unit
    def test_has_changes_false(self):
        """Test has_changes returns False when all deltas are zero."""
        assert ResourceChanges().has_changes is False
        assert ResourceChanges(wealth_delta=0, military_delta=0, influence_delta=0).has_changes is False

    @pytest.mark.unit
    def test_total_change(self):
        """Test total_change returns sum of absolute values."""
        changes = ResourceChanges(wealth_delta=10, military_delta=-5, influence_delta=3)
        assert changes.total_change == 18  # |10| + |-5| + |3|

    @pytest.mark.unit
    def test_to_dict(self):
        """Test to_dict serialization."""
        changes = ResourceChanges(wealth_delta=5, military_delta=-2, influence_delta=0)
        result = changes.to_dict()

        assert result["wealth_delta"] == 5
        assert result["military_delta"] == -2
        assert result["influence_delta"] == 0
        assert result["has_changes"] is True

    @pytest.mark.unit
    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {"wealth_delta": 10, "military_delta": -5, "influence_delta": 3}
        changes = ResourceChanges.from_dict(data)

        assert changes.wealth_delta == 10
        assert changes.military_delta == -5
        assert changes.influence_delta == 3

    @pytest.mark.unit
    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing values."""
        changes = ResourceChanges.from_dict({})

        assert changes.wealth_delta == 0
        assert changes.military_delta == 0
        assert changes.influence_delta == 0

    @pytest.mark.unit
    def test_frozen_immutability(self):
        """Test that ResourceChanges is immutable."""
        changes = ResourceChanges(wealth_delta=5)

        with pytest.raises(AttributeError):
            changes.wealth_delta = 10  # type: ignore


class TestDiplomacyChange:
    """Test suite for DiplomacyChange value object."""

    @pytest.mark.unit
    def test_create_valid(self):
        """Test creating a valid DiplomacyChange."""
        change = DiplomacyChange(
            faction_a="faction-1",
            faction_b="faction-2",
            status_before=DiplomaticStatus.NEUTRAL,
            status_after=DiplomaticStatus.ALLIED,
        )

        assert change.faction_a == "faction-1"
        assert change.faction_b == "faction-2"
        assert change.status_before == DiplomaticStatus.NEUTRAL
        assert change.status_after == DiplomaticStatus.ALLIED

    @pytest.mark.unit
    def test_validation_empty_faction_a(self):
        """Test validation fails for empty faction_a."""
        with pytest.raises(ValueError, match="Faction A ID cannot be empty"):
            DiplomacyChange(
                faction_a="",
                faction_b="faction-2",
                status_before=DiplomaticStatus.NEUTRAL,
                status_after=DiplomaticStatus.ALLIED,
            )

    @pytest.mark.unit
    def test_validation_empty_faction_b(self):
        """Test validation fails for empty faction_b."""
        with pytest.raises(ValueError, match="Faction B ID cannot be empty"):
            DiplomacyChange(
                faction_a="faction-1",
                faction_b="",
                status_before=DiplomaticStatus.NEUTRAL,
                status_after=DiplomaticStatus.ALLIED,
            )

    @pytest.mark.unit
    def test_validation_same_faction(self):
        """Test validation fails for same faction."""
        with pytest.raises(ValueError, match="Faction A and B cannot be the same"):
            DiplomacyChange(
                faction_a="faction-1",
                faction_b="faction-1",
                status_before=DiplomaticStatus.NEUTRAL,
                status_after=DiplomaticStatus.ALLIED,
            )

    @pytest.mark.unit
    def test_is_significant_positive_to_negative(self):
        """Test is_significant for positive to negative change."""
        change = DiplomacyChange(
            faction_a="faction-1",
            faction_b="faction-2",
            status_before=DiplomaticStatus.ALLIED,
            status_after=DiplomaticStatus.HOSTILE,
        )

        assert change.is_significant is True

    @pytest.mark.unit
    def test_is_significant_negative_to_positive(self):
        """Test is_significant for negative to positive change."""
        change = DiplomacyChange(
            faction_a="faction-1",
            faction_b="faction-2",
            status_before=DiplomaticStatus.AT_WAR,
            status_after=DiplomaticStatus.FRIENDLY,
        )

        assert change.is_significant is True

    @pytest.mark.unit
    def test_is_significant_not_significant(self):
        """Test is_significant for minor changes."""
        change = DiplomacyChange(
            faction_a="faction-1",
            faction_b="faction-2",
            status_before=DiplomaticStatus.NEUTRAL,
            status_after=DiplomaticStatus.FRIENDLY,
        )

        assert change.is_significant is False

    @pytest.mark.unit
    def test_to_dict(self):
        """Test to_dict serialization."""
        change = DiplomacyChange(
            faction_a="faction-1",
            faction_b="faction-2",
            status_before=DiplomaticStatus.NEUTRAL,
            status_after=DiplomaticStatus.ALLIED,
        )
        result = change.to_dict()

        assert result["faction_a"] == "faction-1"
        assert result["faction_b"] == "faction-2"
        assert result["status_before"] == "neutral"
        assert result["status_after"] == "allied"

    @pytest.mark.unit
    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "faction_a": "faction-1",
            "faction_b": "faction-2",
            "status_before": "cold",
            "status_after": "friendly",
        }
        change = DiplomacyChange.from_dict(data)

        assert change.faction_a == "faction-1"
        assert change.faction_b == "faction-2"
        assert change.status_before == DiplomaticStatus.COLD
        assert change.status_after == DiplomaticStatus.FRIENDLY

    @pytest.mark.unit
    def test_frozen_immutability(self):
        """Test that DiplomacyChange is immutable."""
        change = DiplomacyChange(
            faction_a="faction-1",
            faction_b="faction-2",
            status_before=DiplomaticStatus.NEUTRAL,
            status_after=DiplomaticStatus.ALLIED,
        )

        with pytest.raises(AttributeError):
            change.faction_a = "other"  # type: ignore


class TestSimulationTick:
    """Test suite for SimulationTick value object."""

    @pytest.fixture
    def calendar_before(self) -> WorldCalendar:
        """Create a calendar for before state."""
        return WorldCalendar(year=100, month=1, day=1, era_name="Test Age")

    @pytest.fixture
    def calendar_after(self) -> WorldCalendar:
        """Create a calendar for after state."""
        return WorldCalendar(year=100, month=1, day=8, era_name="Test Age")

    @pytest.mark.unit
    def test_create_with_all_fields(
        self, calendar_before: WorldCalendar, calendar_after: WorldCalendar
    ):
        """Test creating SimulationTick with all fields."""
        tick = SimulationTick(
            tick_id="tick-1",
            world_id="world-1",
            calendar_before=calendar_before,
            calendar_after=calendar_after,
            days_advanced=7,
            events_generated=["event-1", "event-2"],
            resource_changes={"faction-1": ResourceChanges(wealth_delta=5)},
            diplomacy_changes=[
                DiplomacyChange(
                    faction_a="f1",
                    faction_b="f2",
                    status_before=DiplomaticStatus.NEUTRAL,
                    status_after=DiplomaticStatus.ALLIED,
                )
            ],
            character_reactions=["char-1"],
            rumors_created=3,
        )

        assert tick.tick_id == "tick-1"
        assert tick.world_id == "world-1"
        assert tick.days_advanced == 7
        assert len(tick.events_generated) == 2
        assert len(tick.resource_changes) == 1
        assert len(tick.diplomacy_changes) == 1
        assert len(tick.character_reactions) == 1
        assert tick.rumors_created == 3

    @pytest.mark.unit
    def test_create_with_defaults(self):
        """Test creating SimulationTick with defaults."""
        tick = SimulationTick(world_id="world-1")

        assert tick.tick_id is not None
        assert tick.world_id == "world-1"
        assert tick.calendar_before is None
        assert tick.calendar_after is None
        assert tick.days_advanced == 0
        assert tick.events_generated == []
        assert tick.resource_changes == {}
        assert tick.diplomacy_changes == []
        assert tick.character_reactions == []
        assert tick.rumors_created == 0
        assert tick.created_at is not None

    @pytest.mark.unit
    def test_auto_generated_tick_id(self):
        """Test that tick_id is auto-generated as UUID."""
        tick = SimulationTick(world_id="world-1")

        assert isinstance(tick.tick_id, str)
        assert len(tick.tick_id) == 36  # UUID format

    @pytest.mark.unit
    def test_validation_empty_world_id(self):
        """Test validation fails for empty world_id."""
        with pytest.raises(ValueError, match="World ID cannot be empty"):
            SimulationTick(world_id="")

    @pytest.mark.unit
    def test_validation_negative_days_advanced(self):
        """Test validation fails for negative days_advanced."""
        with pytest.raises(ValueError, match="Days advanced must be >= 0"):
            SimulationTick(world_id="world-1", days_advanced=-1)

    @pytest.mark.unit
    def test_validation_negative_rumors_created(self):
        """Test validation fails for negative rumors_created."""
        with pytest.raises(ValueError, match="Rumors created must be >= 0"):
            SimulationTick(world_id="world-1", rumors_created=-5)

    @pytest.mark.unit
    def test_has_changes_true_with_events(self):
        """Test has_changes is True with events."""
        tick = SimulationTick(
            world_id="world-1",
            events_generated=["event-1"],
        )
        assert tick.has_changes is True

    @pytest.mark.unit
    def test_has_changes_true_with_resource_changes(self):
        """Test has_changes is True with resource changes."""
        tick = SimulationTick(
            world_id="world-1",
            resource_changes={"faction-1": ResourceChanges(wealth_delta=5)},
        )
        assert tick.has_changes is True

    @pytest.mark.unit
    def test_has_changes_true_with_diplomacy_changes(self):
        """Test has_changes is True with diplomacy changes."""
        tick = SimulationTick(
            world_id="world-1",
            diplomacy_changes=[
                DiplomacyChange(
                    faction_a="f1",
                    faction_b="f2",
                    status_before=DiplomaticStatus.NEUTRAL,
                    status_after=DiplomaticStatus.ALLIED,
                )
            ],
        )
        assert tick.has_changes is True

    @pytest.mark.unit
    def test_has_changes_true_with_days_advanced(self):
        """Test has_changes is True when days were advanced."""
        tick = SimulationTick(world_id="world-1", days_advanced=7)
        assert tick.has_changes is True

    @pytest.mark.unit
    def test_has_changes_false(self):
        """Test has_changes is False with no changes."""
        tick = SimulationTick(world_id="world-1")
        assert tick.has_changes is False

    @pytest.mark.unit
    def test_total_resource_changes(self):
        """Test total_resource_changes property."""
        tick = SimulationTick(
            world_id="world-1",
            resource_changes={
                "faction-1": ResourceChanges(wealth_delta=5),
                "faction-2": ResourceChanges(military_delta=-3),
                "faction-3": ResourceChanges(),  # No changes
            },
        )

        assert tick.total_resource_changes == 2  # Only faction-1 and faction-2 have changes

    @pytest.mark.unit
    def test_total_diplomacy_changes(self):
        """Test total_diplomacy_changes property."""
        tick = SimulationTick(
            world_id="world-1",
            diplomacy_changes=[
                DiplomacyChange(
                    faction_a="f1",
                    faction_b="f2",
                    status_before=DiplomaticStatus.NEUTRAL,
                    status_after=DiplomaticStatus.ALLIED,
                ),
                DiplomacyChange(
                    faction_a="f1",
                    faction_b="f3",
                    status_before=DiplomaticStatus.FRIENDLY,
                    status_after=DiplomaticStatus.HOSTILE,
                ),
            ],
        )

        assert tick.total_diplomacy_changes == 2

    @pytest.mark.unit
    def test_to_dict(
        self, calendar_before: WorldCalendar, calendar_after: WorldCalendar
    ):
        """Test to_dict serialization."""
        created_at = datetime(2026, 2, 17, 14, 0, 0)
        tick = SimulationTick(
            tick_id="tick-1",
            world_id="world-1",
            calendar_before=calendar_before,
            calendar_after=calendar_after,
            days_advanced=7,
            events_generated=["event-1"],
            resource_changes={"faction-1": ResourceChanges(wealth_delta=5)},
            diplomacy_changes=[
                DiplomacyChange(
                    faction_a="f1",
                    faction_b="f2",
                    status_before=DiplomaticStatus.NEUTRAL,
                    status_after=DiplomaticStatus.ALLIED,
                )
            ],
            character_reactions=["char-1"],
            rumors_created=2,
            created_at=created_at,
        )

        result = tick.to_dict()

        assert result["tick_id"] == "tick-1"
        assert result["world_id"] == "world-1"
        assert result["calendar_before"]["year"] == 100
        assert result["calendar_after"]["year"] == 100
        assert result["days_advanced"] == 7
        assert result["events_generated"] == ["event-1"]
        assert "faction-1" in result["resource_changes"]
        assert len(result["diplomacy_changes"]) == 1
        assert result["character_reactions"] == ["char-1"]
        assert result["rumors_created"] == 2
        assert result["created_at"] == "2026-02-17T14:00:00"
        assert result["has_changes"] is True

    @pytest.mark.unit
    def test_to_dict_with_none_calendars(self):
        """Test to_dict handles None calendars."""
        tick = SimulationTick(
            world_id="world-1",
            calendar_before=None,
            calendar_after=None,
        )

        result = tick.to_dict()

        assert result["calendar_before"] is None
        assert result["calendar_after"] is None

    @pytest.mark.unit
    def test_from_dict(
        self, calendar_before: WorldCalendar, calendar_after: WorldCalendar
    ):
        """Test from_dict deserialization."""
        data = {
            "tick_id": "tick-1",
            "world_id": "world-1",
            "calendar_before": calendar_before.to_dict(),
            "calendar_after": calendar_after.to_dict(),
            "days_advanced": 7,
            "events_generated": ["event-1"],
            "resource_changes": {
                "faction-1": {"wealth_delta": 5, "military_delta": 0, "influence_delta": 0}
            },
            "diplomacy_changes": [
                {
                    "faction_a": "f1",
                    "faction_b": "f2",
                    "status_before": "neutral",
                    "status_after": "allied",
                }
            ],
            "character_reactions": ["char-1"],
            "rumors_created": 2,
            "created_at": "2026-02-17T14:00:00",
        }

        tick = SimulationTick.from_dict(data)

        assert tick.tick_id == "tick-1"
        assert tick.world_id == "world-1"
        assert tick.calendar_before is not None
        assert tick.calendar_after is not None
        assert tick.days_advanced == 7
        assert tick.events_generated == ["event-1"]
        assert "faction-1" in tick.resource_changes
        assert tick.resource_changes["faction-1"].wealth_delta == 5
        assert len(tick.diplomacy_changes) == 1
        assert tick.character_reactions == ["char-1"]
        assert tick.rumors_created == 2
        assert tick.created_at == datetime(2026, 2, 17, 14, 0, 0)

    @pytest.mark.unit
    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing values."""
        data = {"world_id": "world-1"}

        tick = SimulationTick.from_dict(data)

        assert tick.world_id == "world-1"
        assert tick.calendar_before is None
        assert tick.calendar_after is None
        assert tick.days_advanced == 0
        assert tick.events_generated == []
        assert tick.resource_changes == {}
        assert tick.diplomacy_changes == []
        assert tick.character_reactions == []
        assert tick.rumors_created == 0

    @pytest.mark.unit
    def test_roundtrip_serialization(
        self, calendar_before: WorldCalendar, calendar_after: WorldCalendar
    ):
        """Test that to_dict -> from_dict preserves all data."""
        original = SimulationTick(
            tick_id="tick-1",
            world_id="world-1",
            calendar_before=calendar_before,
            calendar_after=calendar_after,
            days_advanced=7,
            events_generated=["event-1", "event-2"],
            resource_changes={"faction-1": ResourceChanges(wealth_delta=5, military_delta=-2)},
            diplomacy_changes=[
                DiplomacyChange(
                    faction_a="f1",
                    faction_b="f2",
                    status_before=DiplomaticStatus.NEUTRAL,
                    status_after=DiplomaticStatus.ALLIED,
                )
            ],
            character_reactions=["char-1", "char-2"],
            rumors_created=3,
        )

        data = original.to_dict()
        restored = SimulationTick.from_dict(data)

        assert restored.tick_id == original.tick_id
        assert restored.world_id == original.world_id
        assert restored.calendar_before == original.calendar_before
        assert restored.calendar_after == original.calendar_after
        assert restored.days_advanced == original.days_advanced
        assert restored.events_generated == original.events_generated
        assert restored.rumors_created == original.rumors_created
        assert restored.character_reactions == original.character_reactions

    @pytest.mark.unit
    def test_frozen_immutability(self):
        """Test that SimulationTick is immutable."""
        tick = SimulationTick(world_id="world-1")

        with pytest.raises(AttributeError):
            tick.days_advanced = 10  # type: ignore

        with pytest.raises(AttributeError):
            tick.rumors_created = 5  # type: ignore


class TestSimulationTickEquality:
    """Test suite for SimulationTick equality (frozen dataclass)."""

    @pytest.mark.unit
    def test_equality_same_values(self):
        """Test SimulationTicks with same values are equal."""
        created_at = datetime(2026, 2, 17, 14, 0, 0)

        tick1 = SimulationTick(
            tick_id="tick-1",
            world_id="world-1",
            days_advanced=7,
            created_at=created_at,
        )

        tick2 = SimulationTick(
            tick_id="tick-1",
            world_id="world-1",
            days_advanced=7,
            created_at=created_at,
        )

        assert tick1 == tick2

    @pytest.mark.unit
    def test_inequality_different_values(self):
        """Test SimulationTicks with different values are not equal."""
        tick1 = SimulationTick(tick_id="tick-1", world_id="world-1")
        tick2 = SimulationTick(tick_id="tick-2", world_id="world-1")

        assert tick1 != tick2

    @pytest.mark.unit
    def test_frozen_immutability_lists(self):
        """Test that list fields on SimulationTick are immutable."""
        tick = SimulationTick(
            world_id="world-1",
            events_generated=["event-1"],
        )

        # The list itself should be immutable (frozen dataclass blocks assignment)
        with pytest.raises(AttributeError):
            tick.events_generated = ["event-2"]  # type: ignore

        # Note: The list contents CAN be modified since it's a mutable list.
        # This is a known limitation of frozen dataclasses with mutable fields.
        # For true immutability, tuples would be needed, but lists are more
        # convenient for serialization purposes.
