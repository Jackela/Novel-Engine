"""Tests for PostgresWorldStateSnapshots.

Tests the snapshot operations for world state persistence.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots import (
    PostgresWorldStateSnapshots,
)


class TestPostgresWorldStateSnapshots:
    """Test suite for PostgresWorldStateSnapshots."""

    @pytest.fixture
    def snapshots(self):
        """Create a fresh snapshots instance for each test."""
        return PostgresWorldStateSnapshots()

    @pytest.fixture
    def sample_world_state(self):
        """Create a sample world state for testing."""
        world_state = WorldState(
            id="test-world-123",
            story_id="test-story-123",
            version=5,
        )
        world_state.entities = {}  # Empty entities dict
        return world_state

    @pytest.mark.asyncio
    async def test_create_snapshot_success(self, snapshots, sample_world_state):
        """Test successful snapshot creation."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.PostgresWorldStateCrud"
        ) as mock_crud_class:
            mock_crud = MagicMock()
            mock_crud.get_by_id_or_raise.return_value = sample_world_state
            mock_crud_class.return_value = mock_crud

            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
            ) as mock_get_session:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=False)
                mock_get_session.return_value = mock_session

                # Mock snapshot model
                mock_snapshot_model = MagicMock()
                mock_snapshot_model.id = "snapshot-456"
                mock_session.add.return_value = None

                with patch(
                    "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.WorldStateSnapshotModel"
                ) as mock_snapshot_class:
                    mock_snapshot_class.return_value = mock_snapshot_model

                    result = await snapshots.create_snapshot(
                        "test-world-123", "My Snapshot", metadata={"reason": "testing"}
                    )

                    assert result == "snapshot-456"
                    mock_session.add.assert_called_once()
                    mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_snapshot_raises_when_world_not_found(self, snapshots):
        """Test that create_snapshot raises exception when world state not found."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            EntityNotFoundException,
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.PostgresWorldStateCrud"
        ) as mock_crud_class:
            mock_crud = MagicMock()
            mock_crud.get_by_id_or_raise.side_effect = EntityNotFoundException(
                "World not found"
            )
            mock_crud_class.return_value = mock_crud

            with pytest.raises(EntityNotFoundException):
                await snapshots.create_snapshot("non-existent", "Test")

    @pytest.mark.asyncio
    async def test_restore_from_snapshot_success(self, snapshots, sample_world_state):
        """Test successful restoration from snapshot."""
        current_state = WorldState(
            id="test-world-123", story_id="test-story-123", version=10
        )
        restored_state = WorldState(
            id="test-world-123", story_id="test-story-123", version=11
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock snapshot model
            mock_snapshot_model = MagicMock()
            mock_snapshot_model.id = "snapshot-456"
            mock_snapshot_model.world_state_id = "test-world-123"
            mock_snapshot_model.snapshot_name = "Backup"
            mock_snapshot_model.snapshot_data = {
                "world_state": {
                    "id": "test-world-123",
                    "name": "Test World",
                    "version": 5,
                }
            }
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_snapshot_model
            )

            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.PostgresWorldStateVersioning"
            ) as mock_versioning_class:
                mock_versioning = MagicMock()
                mock_versioning._reconstruct_world_state_from_version_data.return_value = sample_world_state
                mock_versioning_class.return_value = mock_versioning

                with patch(
                    "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.PostgresWorldStateCrud"
                ) as mock_crud_class:
                    mock_crud = MagicMock()
                    mock_crud.get_by_id_or_raise.return_value = current_state
                    mock_crud.save.return_value = restored_state
                    mock_crud_class.return_value = mock_crud

                    with patch(
                        "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.WorldStateChanged"
                    ) as mock_event_class:
                        mock_event = MagicMock()
                        mock_event_class.snapshot_restored.return_value = mock_event

                        result = await snapshots.restore_from_snapshot(
                            "test-world-123", "snapshot-456"
                        )

                        assert result.id == "test-world-123"
                        assert result.version == 11
                        mock_crud.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_from_snapshot_raises_when_snapshot_not_found(
        self, snapshots
    ):
        """Test that restore raises exception when snapshot not found."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            EntityNotFoundException,
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            with pytest.raises(EntityNotFoundException):
                await snapshots.restore_from_snapshot("test-world-123", "non-existent")

    @pytest.mark.asyncio
    async def test_list_snapshots_returns_list(self, snapshots):
        """Test that list_snapshots returns a list of snapshot metadata."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock snapshot models
            mock_snapshot1 = MagicMock()
            mock_snapshot1.id = "snapshot-1"
            mock_snapshot1.snapshot_name = "Snapshot 1"
            mock_snapshot1.snapshot_reason = "Manual backup"
            mock_snapshot1.world_version_at_snapshot = 5
            mock_snapshot1.entity_count = 10
            mock_snapshot1.data_size_bytes = 1024
            mock_snapshot1.created_at = datetime(2024, 1, 1)

            mock_snapshot2 = MagicMock()
            mock_snapshot2.id = "snapshot-2"
            mock_snapshot2.snapshot_name = "Snapshot 2"
            mock_snapshot2.snapshot_reason = "Auto backup"
            mock_snapshot2.world_version_at_snapshot = 10
            mock_snapshot2.entity_count = 15
            mock_snapshot2.data_size_bytes = 2048
            mock_snapshot2.created_at = datetime(2024, 1, 2)

            mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
                mock_snapshot2,
                mock_snapshot1,
            ]

            result = await snapshots.list_snapshots("test-world-123")

            assert len(result) == 2
            assert result[0]["id"] == "snapshot-2"
            assert result[0]["name"] == "Snapshot 2"
            assert result[0]["entity_count"] == 15

    @pytest.mark.asyncio
    async def test_delete_snapshot_returns_true_when_deleted(self, snapshots):
        """Test that delete_snapshot returns True when snapshot is deleted."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_snapshot = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_snapshot
            )

            result = await snapshots.delete_snapshot("snapshot-123")

            assert result is True
            mock_session.delete.assert_called_once_with(mock_snapshot)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_snapshot_returns_false_when_not_found(self, snapshots):
        """Test that delete_snapshot returns False when snapshot not found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            result = await snapshots.delete_snapshot("non-existent")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_snapshot_by_id_returns_snapshot_details(self, snapshots):
        """Test that get_snapshot_by_id returns detailed snapshot information."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_snapshot = MagicMock()
            mock_snapshot.id = "snapshot-123"
            mock_snapshot.world_state_id = "world-123"
            mock_snapshot.snapshot_name = "Test Snapshot"
            mock_snapshot.snapshot_reason = "Testing"
            mock_snapshot.world_version_at_snapshot = 5
            mock_snapshot.entity_count = 10
            mock_snapshot.data_size_bytes = 1024
            mock_snapshot.snapshot_data = {"world_state": {"id": "world-123"}}
            mock_snapshot.created_at = datetime(2024, 1, 1)

            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_snapshot
            )

            result = await snapshots.get_snapshot_by_id("snapshot-123")

            assert result is not None
            assert result["id"] == "snapshot-123"
            assert result["name"] == "Test Snapshot"
            assert result["entity_count"] == 10
            assert "snapshot_data" in result

    @pytest.mark.asyncio
    async def test_get_snapshot_by_id_returns_none_when_not_found(self, snapshots):
        """Test that get_snapshot_by_id returns None when snapshot not found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_snapshots.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            result = await snapshots.get_snapshot_by_id("non-existent")

            assert result is None
