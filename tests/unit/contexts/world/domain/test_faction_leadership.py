#!/usr/bin/env python3
"""
Unit tests for Faction Leadership (CHAR-035)

Tests the leader_id field on Faction entity and the set_leader,
remove_leader, and related methods.
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Mock problematic dependencies

pytestmark = pytest.mark.unit

sys.modules["aioredis"] = MagicMock()


class MockEventPriority(Enum):
    """Mock EventPriority for testing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockEvent:
    """Mock Event class that supports dataclass functionality."""

    event_id: str | None = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    priority: MockEventPriority = MockEventPriority.NORMAL
    timestamp: datetime | None = None
    tags: set = field(default_factory=set)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
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

from src.contexts.world.domain.entities.faction import (
    Faction,
    FactionAlignment,
    FactionStatus,
    FactionType,
)

# Restore original module to avoid polluting other tests
if _original_event_bus is not None:
    sys.modules["src.events.event_bus"] = _original_event_bus
else:
    del sys.modules["src.events.event_bus"]


def _create_test_faction(
    leader_id: str | None = None, leader_name: str | None = None
) -> Faction:
    """Helper to create a valid faction for testing."""
    return Faction(
        name="Test Guild",
        description="A guild for testing purposes",
        faction_type=FactionType.GUILD,
        alignment=FactionAlignment.TRUE_NEUTRAL,
        status=FactionStatus.ACTIVE,
        influence=50,
        military_strength=30,
        economic_power=60,
        member_count=100,
        leader_id=leader_id,
        leader_name=leader_name,
    )


class TestFactionLeadership:
    """Test suite for faction leadership functionality."""

    # ==================== Initial State Tests ====================

    @pytest.mark.unit
    def test_faction_default_no_leader(self):
        """Test that a new faction has no leader by default."""
        faction = _create_test_faction()

        assert faction.leader_id is None
        assert faction.leader_name is None
        assert faction.get_leader_id() is None
        assert faction.has_leader() is False

    @pytest.mark.unit
    def test_faction_created_with_leader_id(self):
        """Test faction can be created with initial leader_id."""
        leader_id = "char-123"
        faction = _create_test_faction(leader_id=leader_id)

        assert faction.leader_id == leader_id
        assert faction.get_leader_id() == leader_id
        assert faction.has_leader() is True

    @pytest.mark.unit
    def test_faction_created_with_leader_id_and_name(self):
        """Test faction can be created with both leader_id and leader_name."""
        faction = _create_test_faction(
            leader_id="char-123", leader_name="Guild Master Theron"
        )

        assert faction.leader_id == "char-123"
        assert faction.leader_name == "Guild Master Theron"
        assert faction.has_leader() is True

    # ==================== set_leader Tests ====================

    @pytest.mark.unit
    def test_set_leader_success(self):
        """Test successfully setting a faction leader."""
        faction = _create_test_faction()
        old_updated_at = faction.updated_at

        import time

        time.sleep(0.01)

        faction.set_leader("new-leader-id", "Lord Commander")

        assert faction.leader_id == "new-leader-id"
        assert faction.leader_name == "Lord Commander"
        assert faction.has_leader() is True
        assert faction.updated_at > old_updated_at

    @pytest.mark.unit
    def test_set_leader_without_name(self):
        """Test setting a leader without specifying a name."""
        faction = _create_test_faction()

        faction.set_leader("leader-without-name")

        assert faction.leader_id == "leader-without-name"
        assert faction.leader_name is None

    @pytest.mark.unit
    def test_set_leader_replaces_previous(self):
        """Test that setting a new leader replaces the previous one."""
        faction = _create_test_faction(leader_id="old-leader", leader_name="Old Name")

        faction.set_leader("new-leader", "New Name")

        assert faction.leader_id == "new-leader"
        assert faction.leader_name == "New Name"

    @pytest.mark.unit
    def test_set_leader_empty_id_raises(self):
        """Test that setting leader with empty ID raises ValueError."""
        faction = _create_test_faction()

        with pytest.raises(ValueError, match="cannot be empty"):
            faction.set_leader("")

    @pytest.mark.unit
    def test_set_leader_whitespace_id_raises(self):
        """Test that setting leader with whitespace-only ID raises ValueError."""
        faction = _create_test_faction()

        with pytest.raises(ValueError, match="cannot be empty"):
            faction.set_leader("   ")

    @pytest.mark.unit
    def test_set_leader_updates_name_only(self):
        """Test that setting leader with same ID but new name updates the name."""
        faction = _create_test_faction(leader_id="same-leader", leader_name="Old Title")

        faction.set_leader("same-leader", "New Title")

        assert faction.leader_id == "same-leader"
        assert faction.leader_name == "New Title"

    # ==================== remove_leader Tests ====================

    @pytest.mark.unit
    def test_remove_leader_success(self):
        """Test successfully removing a faction leader."""
        faction = _create_test_faction(
            leader_id="current-leader", leader_name="The Boss"
        )
        old_updated_at = faction.updated_at

        import time

        time.sleep(0.01)

        result = faction.remove_leader()

        assert result is True
        assert faction.leader_id is None
        assert faction.leader_name is None
        assert faction.has_leader() is False
        assert faction.updated_at > old_updated_at

    @pytest.mark.unit
    def test_remove_leader_when_no_leader(self):
        """Test removing leader when there is none returns False."""
        faction = _create_test_faction()

        result = faction.remove_leader()

        assert result is False
        assert faction.leader_id is None

    @pytest.mark.unit
    def test_remove_leader_clears_both_id_and_name(self):
        """Test that removing leader clears both leader_id and leader_name."""
        faction = _create_test_faction(leader_id="leader-id", leader_name="Leader Name")

        faction.remove_leader()

        assert faction.leader_id is None
        assert faction.leader_name is None

    # ==================== has_leader Tests ====================

    @pytest.mark.unit
    def test_has_leader_true_when_set(self):
        """Test has_leader returns True when leader is set."""
        faction = _create_test_faction(leader_id="any-leader")

        assert faction.has_leader() is True

    @pytest.mark.unit
    def test_has_leader_false_when_not_set(self):
        """Test has_leader returns False when no leader."""
        faction = _create_test_faction()

        assert faction.has_leader() is False

    @pytest.mark.unit
    def test_has_leader_false_after_removal(self):
        """Test has_leader returns False after leader is removed."""
        faction = _create_test_faction(leader_id="temp-leader")
        faction.remove_leader()

        assert faction.has_leader() is False

    # ==================== to_dict Tests ====================

    @pytest.mark.unit
    def test_to_dict_includes_leader_id(self):
        """Test that to_dict includes leader_id field."""
        faction = _create_test_faction(leader_id="dict-leader")

        result = faction.to_dict()

        assert "leader_id" in result
        assert result["leader_id"] == "dict-leader"

    @pytest.mark.unit
    def test_to_dict_leader_id_none_when_no_leader(self):
        """Test that to_dict includes leader_id as None when no leader."""
        faction = _create_test_faction()

        result = faction.to_dict()

        assert "leader_id" in result
        assert result["leader_id"] is None

    @pytest.mark.unit
    def test_to_dict_includes_leader_name(self):
        """Test that to_dict includes leader_name field."""
        faction = _create_test_faction(leader_id="leader", leader_name="Boss")

        result = faction.to_dict()

        assert "leader_name" in result
        assert result["leader_name"] == "Boss"

    # ==================== Workflow Tests ====================

    @pytest.mark.unit
    def test_set_remove_set_workflow(self):
        """Test a complete set-remove-set leader workflow."""
        faction = _create_test_faction()

        # Set first leader
        faction.set_leader("leader-1", "First Leader")
        assert faction.has_leader() is True
        assert faction.leader_id == "leader-1"

        # Remove leader
        faction.remove_leader()
        assert faction.has_leader() is False

        # Set new leader
        faction.set_leader("leader-2", "Second Leader")
        assert faction.has_leader() is True
        assert faction.leader_id == "leader-2"
        assert faction.leader_name == "Second Leader"

    @pytest.mark.unit
    def test_multiple_leader_changes(self):
        """Test multiple leadership changes work correctly."""
        faction = _create_test_faction()

        # Series of leadership changes
        faction.set_leader("leader-a")
        faction.set_leader("leader-b", "Leader B")
        faction.set_leader("leader-c", "Leader C")
        faction.remove_leader()
        faction.set_leader("final-leader", "Final Leader")

        assert faction.leader_id == "final-leader"
        assert faction.leader_name == "Final Leader"


class TestFactionFactoryMethods:
    """Test that factory methods don't set a leader by default."""

    @pytest.mark.unit
    def test_create_kingdom_no_leader(self):
        """Test create_kingdom doesn't set a leader."""
        kingdom = Faction.create_kingdom("Test Kingdom")

        assert kingdom.leader_id is None
        assert kingdom.has_leader() is False

    @pytest.mark.unit
    def test_create_guild_no_leader(self):
        """Test create_guild doesn't set a leader."""
        guild = Faction.create_guild("Test Guild")

        assert guild.leader_id is None
        assert guild.has_leader() is False

    @pytest.mark.unit
    def test_create_cult_no_leader(self):
        """Test create_cult doesn't set a leader."""
        cult = Faction.create_cult("Test Cult")

        assert cult.leader_id is None
        assert cult.has_leader() is False
