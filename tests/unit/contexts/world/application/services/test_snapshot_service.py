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
        snapshot = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

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
        snapshot = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

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
        snapshot = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
            description="Before major battle",
        )

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
            snapshot = service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )
            snapshot_ids.append(snapshot.snapshot_id)

        # Should have exactly max_per_world snapshots
        assert service.get_snapshot_count("world-123") == MAX_SNAPSHOTS_PER_WORLD

        # First snapshots should be evicted
        for i in range(5):
            assert snapshot_ids[i] not in [
                s.snapshot_id for s in service.list_snapshots("world-123")
            ]

    def test_create_snapshot_separate_worlds(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test that snapshots are isolated between worlds."""
        service.create_snapshot(
            world_id="world-a",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=1,
        )
        service.create_snapshot(
            world_id="world-b",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=2,
        )

        assert service.get_snapshot_count("world-a") == 1
        assert service.get_snapshot_count("world-b") == 1


class TestRestoreSnapshot:
    """Tests for restore_snapshot method."""

    def test_restore_snapshot_success(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test successful snapshot restoration."""
        snapshot = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        result = service.restore_snapshot(snapshot.snapshot_id)

        assert result.is_ok
        restored = result.value
        assert restored.snapshot_id == snapshot.snapshot_id
        assert restored.world_id == "world-123"

    def test_restore_snapshot_not_found(self, service: SnapshotService) -> None:
        """Test restoring non-existent snapshot."""
        result = service.restore_snapshot("non-existent-id")

        assert result.is_error
        assert result.error == SnapshotError.NOT_FOUND

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
        assert result.error == SnapshotError.RESTORE_FAILED


class TestListSnapshots:
    """Tests for list_snapshots method."""

    def test_list_snapshots_empty(self, service: SnapshotService) -> None:
        """Test listing snapshots for world with none."""
        snapshots = service.list_snapshots("world-123")

        assert snapshots == []

    def test_list_snapshots_ordered_by_newest(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test that snapshots are ordered newest first."""
        for i in range(5):
            service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )

        snapshots = service.list_snapshots("world-123")

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
            service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )

        snapshots = service.list_snapshots("world-123", limit=3)

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
        snapshot = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        deleted = service.delete_snapshot(snapshot.snapshot_id)

        assert deleted is True
        assert service.get_snapshot_count("world-123") == 0

    def test_delete_snapshot_not_found(self, service: SnapshotService) -> None:
        """Test deleting non-existent snapshot."""
        deleted = service.delete_snapshot("non-existent-id")

        assert deleted is False


class TestGetLatestSnapshot:
    """Tests for get_latest_snapshot method."""

    def test_get_latest_no_snapshots(self, service: SnapshotService) -> None:
        """Test getting latest when no snapshots exist."""
        result = service.get_latest_snapshot("world-123")

        assert result is None

    def test_get_latest_single_snapshot(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test getting latest with single snapshot."""
        snapshot = service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        result = service.get_latest_snapshot("world-123")

        assert result is not None
        assert result.snapshot_id == snapshot.snapshot_id

    def test_get_latest_multiple_snapshots(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test getting latest with multiple snapshots."""
        for i in range(5):
            service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )

        result = service.get_latest_snapshot("world-123")

        assert result is not None
        assert result.tick_number == 4  # Latest tick


class TestClearStorage:
    """Tests for clear_storage method."""

    def test_clear_storage(
        self,
        service: SnapshotService,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Test clearing all storage."""
        service.create_snapshot(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=1,
        )
        service.create_snapshot(
            world_id="world-456",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=2,
        )

        service.clear_storage()

        assert service.get_snapshot_count("world-123") == 0
        assert service.get_snapshot_count("world-456") == 0


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
            service.create_snapshot(
                world_id="world-123",
                calendar=calendar,
                state_json=sample_state_json,
                tick_number=i,
            )

        # Should only keep 3
        assert service.get_snapshot_count("world-123") == 3
