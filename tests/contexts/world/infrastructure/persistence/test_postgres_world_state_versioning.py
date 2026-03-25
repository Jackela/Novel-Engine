"""Tests for PostgresWorldStateVersioning.

Tests the versioning operations for world state persistence.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.infrastructure.persistence.postgres_world_state_versioning import (
    PostgresWorldStateVersioning,
)


class TestPostgresWorldStateVersioning:
    """Test suite for PostgresWorldStateVersioning."""

    @pytest.fixture
    def versioning(self):
        """Create a fresh versioning instance for each test."""
        return PostgresWorldStateVersioning()

    @pytest.fixture
    def sample_world_state(self):
        """Create a sample world state for testing."""
        return WorldState(
            id="test-world-123",
            name="Test World",
            version=3,
        )

    @pytest.mark.asyncio
    async def test_get_version_returns_world_state_at_version(
        self, versioning, sample_world_state
    ):
        """Test that get_version returns the world state at the specified version."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock version model with serialized data
            mock_version_model = MagicMock()
            mock_version_model.version_data = {
                "id": "test-world-123",
                "name": "Test World",
                "version": 2,
            }
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_version_model
            )

            with patch.object(
                versioning,
                "_reconstruct_world_state_from_version_data",
                return_value=sample_world_state,
            ):
                result = await versioning.get_version("test-world-123", 2)

                assert result is not None
                assert result.id == "test-world-123"

    @pytest.mark.asyncio
    async def test_get_version_returns_none_when_not_found(self, versioning):
        """Test that get_version returns None when version not found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            result = await versioning.get_version("test-world-123", 999)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_version_history_returns_list(self, versioning):
        """Test that get_version_history returns a list of version entries."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock version models
            mock_version1 = MagicMock()
            mock_version1.version_number = 3
            mock_version1.previous_version = 2
            mock_version1.change_reason = "Update 3"
            mock_version1.change_summary = "Third update"
            mock_version1.changed_by = None
            mock_version1.created_at = datetime(2024, 1, 3)
            mock_version1.entities_added = 1
            mock_version1.entities_removed = 0
            mock_version1.entities_modified = 2
            mock_version1.environment_changed = False

            mock_version2 = MagicMock()
            mock_version2.version_number = 2
            mock_version2.previous_version = 1
            mock_version2.change_reason = "Update 2"
            mock_version2.change_summary = "Second update"
            mock_version2.changed_by = None
            mock_version2.created_at = datetime(2024, 1, 2)
            mock_version2.entities_added = 0
            mock_version2.entities_removed = 1
            mock_version2.entities_modified = 1
            mock_version2.environment_changed = True

            mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
                mock_version1,
                mock_version2,
            ]

            result = await versioning.get_version_history("test-world-123", limit=10)

            assert len(result) == 2
            assert result[0]["version"] == 3
            assert result[1]["version"] == 2
            assert result[0]["entities_added"] == 1

    @pytest.mark.asyncio
    async def test_rollback_to_version_success(self, versioning, sample_world_state):
        """Test successful rollback to a previous version."""
        target_version_state = WorldState(
            id="test-world-123", name="Test World", version=2
        )
        current_version_state = WorldState(
            id="test-world-123", name="Test World", version=5
        )

        with patch.object(versioning, "get_version", return_value=target_version_state):
            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.PostgresWorldStateCrud"
            ) as mock_crud_class:
                mock_crud = MagicMock()
                mock_crud.get_by_id_or_raise.return_value = current_version_state
                # Mock save to return the saved state
                saved_state = WorldState(
                    id="test-world-123", name="Test World", version=6
                )
                mock_crud.save.return_value = saved_state
                mock_crud_class.return_value = mock_crud

                with patch(
                    "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.WorldStateChanged"
                ) as mock_event_class:
                    mock_event = MagicMock()
                    mock_event_class.rollback_performed.return_value = mock_event

                    result = await versioning.rollback_to_version("test-world-123", 2)

                    assert result.id == "test-world-123"
                    mock_crud.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_to_version_raises_when_target_not_found(self, versioning):
        """Test that rollback raises exception when target version not found."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            EntityNotFoundException,
        )

        with patch.object(versioning, "get_version", return_value=None):
            with pytest.raises(EntityNotFoundException):
                await versioning.rollback_to_version("test-world-123", 999)

    @pytest.mark.asyncio
    async def test_get_events_since_returns_events(self, versioning):
        """Test that get_events_since returns events after the specified version."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock version models as events
            mock_version1 = MagicMock()
            mock_version1.version_number = 4
            mock_version1.change_reason = "Update 4"
            mock_version1.change_summary = "Fourth update"
            mock_version1.entities_added = 1
            mock_version1.entities_removed = 0
            mock_version1.entities_modified = 0
            mock_version1.environment_changed = False
            mock_version1.created_at = datetime(2024, 1, 4)
            mock_version1.changed_by = None

            mock_version2 = MagicMock()
            mock_version2.version_number = 5
            mock_version2.change_reason = "Update 5"
            mock_version2.change_summary = "Fifth update"
            mock_version2.entities_added = 0
            mock_version2.entities_removed = 1
            mock_version2.entities_modified = 2
            mock_version2.environment_changed = True
            mock_version2.created_at = datetime(2024, 1, 5)
            mock_version2.changed_by = "user-123"

            mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
                mock_version1,
                mock_version2,
            ]

            result = await versioning.get_events_since("test-world-123", 3)

            assert len(result) == 2
            assert result[0]["version"] == 4
            assert result[1]["version"] == 5
            assert result[1]["changed_by"] == "user-123"

    @pytest.mark.asyncio
    async def test_replay_events_to_specific_version(
        self, versioning, sample_world_state
    ):
        """Test replaying events to a specific version."""
        with patch.object(versioning, "get_version", return_value=sample_world_state):
            result = await versioning.replay_events("test-world-123", to_version=3)

            assert result.id == "test-world-123"

    @pytest.mark.asyncio
    async def test_replay_events_to_latest(self, versioning, sample_world_state):
        """Test replaying events to latest version."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.PostgresWorldStateCrud"
        ) as mock_crud_class:
            mock_crud = MagicMock()
            mock_crud.get_by_id_or_raise.return_value = sample_world_state
            mock_crud_class.return_value = mock_crud

            result = await versioning.replay_events("test-world-123", to_version=None)

            assert result.id == "test-world-123"

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_removes_old_entries(self, versioning):
        """Test that cleanup removes old version entries."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock count to indicate many versions
            mock_session.query.return_value.filter.return_value.count.return_value = 100

            # Mock old versions to delete
            mock_old_versions = [MagicMock() for _ in range(50)]
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.all.return_value = mock_old_versions

            result = await versioning.cleanup_old_versions(
                "test-world-123", keep_count=50
            )

            assert result == 50
            assert mock_session.delete.call_count == 50
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_versions_does_nothing_when_few_versions(
        self, versioning
    ):
        """Test that cleanup does nothing when version count is below threshold."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_versioning.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock count to indicate few versions
            mock_session.query.return_value.filter.return_value.count.return_value = 30

            result = await versioning.cleanup_old_versions(
                "test-world-123", keep_count=50
            )

            assert result == 0
            mock_session.delete.assert_not_called()
