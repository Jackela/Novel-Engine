#!/usr/bin/env python3
"""Tests for SnapshotService.

This module tests the SnapshotService class for managing world state snapshots.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.contexts.world.application.services.snapshot_service import (
    MAX_SNAPSHOTS_PER_WORLD,
    SnapshotError,
    SnapshotService,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit
from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


@pytest.fixture
def service() -> SnapshotService:
    """Create a fresh SnapshotService for each test."""
    return SnapshotService()


@pytest.fixture
def calendar() -> WorldCalendar:
    """Create a sample WorldCalendar."""
    return WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")


@pytest.fixture
def sample_state_json() -> str:
    """Create sample state JSON."""
    return json.dumps({
        "id": "world-123",
        "factions": [],
        "locations": [],
    })


class TestCreateSnapshot:
    """Tests for create_snapshot method."""

    def test_create_snapshot_basic(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test creating a basic snapshot."""
        result = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )
        assert result.is_ok
        snapshot = result.value

        assert snapshot.world_id == "world-123"
        assert snapshot.tick_number == 5
        assert snapshot.calendar is not None
        assert snapshot.calendar.year == 1042
        assert snapshot.state_json == sample_state_json
        assert snapshot.snapshot_id  # Non-empty ID

    def test_create_snapshot_auto_description(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test that description is auto-generated when not provided."""
        result = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )
        assert result.is_ok
        snapshot = result.value

        # Auto-description should be "Tick {tick_number} - {calendar.format()}"
        assert "Tick 5" in snapshot.description
        assert "1042" in snapshot.description

    def test_create_snapshot_custom_description(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test creating snapshot with custom description."""
        result = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
            description="Before major battle",
        )
        assert result.is_ok
        snapshot = result.value

        assert snapshot.description == "Before major battle"

    def test_create_snapshot_fifo_eviction(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test FIFO eviction when max snapshots exceeded."""
        snapshot_ids = []

        # Create more than max snapshots
        for i in range(MAX_SNAPSHOTS_PER_WORLD + 5):
            result = service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )
            assert result.is_ok
            snapshot = result.value
            snapshot_ids.append(snapshot.snapshot_id)

        # Should have exactly max_per_world snapshots
        count_result = service.get_snapshot_count("world-123")
        assert count_result.is_ok
        assert count_result.value == MAX_SNAPSHOTS_PER_WORLD

        # First snapshots should be evicted
        list_result = service.list_snapshots("world-123")
        assert list_result.is_ok
        for i in range(5):
            assert snapshot_ids[i] not in [
                s.snapshot_id for s in list_result.value
            ]

    def test_create_snapshot_separate_worlds(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test that snapshots are isolated between worlds."""
        result_a = service.create_snapshot(
            world_id="world-a",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=1,
        )
        assert result_a.is_ok
        result_b = service.create_snapshot(
            world_id="world-b",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=2,
        )
        assert result_b.is_ok

        count_a = service.get_snapshot_count("world-a")
        count_b = service.get_snapshot_count("world-b")
        assert count_a.is_ok
        assert count_b.is_ok
        assert count_a.value == 1
        assert count_b.value == 1


class TestRestoreSnapshot:
    """Tests for restore_snapshot method."""

    def test_restore_snapshot_success(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test successful snapshot restoration."""
        create_result = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )
        assert create_result.is_ok
        snapshot = create_result.value

        result = service.restore_snapshot(snapshot.snapshot_id)

        assert result.is_ok
        restored = result.value
        assert restored.snapshot_id == snapshot.snapshot_id
        assert restored.world_id == "world-123"

    def test_restore_snapshot_not_found(self, service: SnapshotService) -> None:
        """Test restoring non-existent snapshot."""
        result = service.restore_snapshot("non-existent-id")

        assert result.is_error
        assert "not found" in str(result.error).lower()

    def test_restore_snapshot_invalid_json(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
    ) -> None:
        """Test restoring snapshot with invalid JSON."""
        # Create snapshot with invalid JSON
        snapshot = WorldSnapshot(
            world_id="world-123",
            calendar=calendar,
            state_json="not valid json {{{",
            tick_number=5,
        )

        # Manually add to storage
        service._storage["world-123"] = {snapshot.snapshot_id: snapshot}

        result = service.restore_snapshot(snapshot.snapshot_id)

        assert result.is_error
        assert "restore" in str(result.error).lower() or "json" in str(result.error).lower()


class TestListSnapshots:
    """Tests for list_snapshots method."""

    def test_list_snapshots_empty(self, service: SnapshotService) -> None:
        """Test listing snapshots for world with none."""
        result = service.list_snapshots("world-123")

        assert result.is_ok
        assert result.value == []

    def test_list_snapshots_ordered_by_newest(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test that snapshots are ordered newest first."""
        for i in range(5):
            result = service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )
            assert result.is_ok

        list_result = service.list_snapshots("world-123")
        assert list_result.is_ok
        snapshots = list_result.value

        # Should be ordered by tick descending (newest first)
        tick_numbers = [s.tick_number for s in snapshots]
        assert tick_numbers == [4, 3, 2, 1, 0]

    def test_list_snapshots_limit(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test limit parameter."""
        for i in range(10):
            result = service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )
            assert result.is_ok

        list_result = service.list_snapshots("world-123", limit=3)
        assert list_result.is_ok
        snapshots = list_result.value

        assert len(snapshots) == 3
        # Should get the 3 newest
        assert snapshots[0].tick_number == 9
        assert snapshots[1].tick_number == 8
        assert snapshots[2].tick_number == 7


class TestDeleteSnapshot:
    """Tests for delete_snapshot method."""

    def test_delete_snapshot_success(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test successful snapshot deletion."""
        create_result = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )
        assert create_result.is_ok
        snapshot = create_result.value

        delete_result = service.delete_snapshot(snapshot.snapshot_id)
        assert delete_result.is_ok
        deleted = delete_result.value

        assert deleted is True
        count_result = service.get_snapshot_count("world-123")
        assert count_result.is_ok
        assert count_result.value == 0

    def test_delete_snapshot_not_found(self, service: SnapshotService) -> None:
        """Test deleting non-existent snapshot."""
        result = service.delete_snapshot("non-existent-id")

        assert result.is_ok
        assert result.value is False


class TestGetLatestSnapshot:
    """Tests for get_latest_snapshot method."""

    def test_get_latest_no_snapshots(self, service: SnapshotService) -> None:
        """Test getting latest when no snapshots exist."""
        result = service.get_latest_snapshot("world-123")

        assert result.is_ok
        assert result.value is None

    def test_get_latest_single_snapshot(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test getting latest with single snapshot."""
        create_result = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )
        assert create_result.is_ok
        snapshot = create_result.value

        result = service.get_latest_snapshot("world-123")

        assert result.is_ok
        assert result.value is not None
        assert result.value.snapshot_id == snapshot.snapshot_id

    def test_get_latest_multiple_snapshots(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test getting latest with multiple snapshots."""
        for i in range(5):
            create_result = service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )
            assert create_result.is_ok

        result = service.get_latest_snapshot("world-123")

        assert result.is_ok
        assert result.value is not None
        assert result.value.tick_number == 4  # Latest tick


class TestClearStorage:
    """Tests for clear_storage method."""

    def test_clear_storage(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test clearing all storage."""
        result1 = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=1,
        )
        assert result1.is_ok
        result2 = service.create_snapshot(
            world_id="world-456",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=2,
        )
        assert result2.is_ok

        clear_result = service.clear_storage()
        assert clear_result.is_ok

        count1 = service.get_snapshot_count("world-123")
        count2 = service.get_snapshot_count("world-456")
        assert count1.is_ok
        assert count2.is_ok
        assert count1.value == 0
        assert count2.value == 0


class TestCustomMaxPerWorld:
    """Tests for custom max_per_world setting."""

    def test_custom_max_per_world(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test custom max_per_world setting."""
        service = SnapshotService(max_per_world=3)

        for i in range(5):
            result = service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )
            assert result.is_ok

        # Should only keep 3
        count_result = service.get_snapshot_count("world-123")
        assert count_result.is_ok
        assert count_result.value == 3
