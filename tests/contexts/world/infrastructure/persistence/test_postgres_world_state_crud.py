"""Tests for PostgresWorldStateCrud.

Tests the basic CRUD operations for world state persistence.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.infrastructure.persistence.postgres_world_state_crud import (
    PostgresWorldStateCrud,
)


class TestPostgresWorldStateCrud:
    """Test suite for PostgresWorldStateCrud."""

    @pytest.fixture
    def crud(self):
        """Create a fresh crud instance for each test."""
        return PostgresWorldStateCrud()

    @pytest.fixture
    def sample_world_state(self):
        """Create a sample world state for testing."""
        return WorldState(
            id="test-world-123",
            name="Test World",
            version=1,
        )

    @pytest.mark.asyncio
    async def test_save_creates_new_world_state(self, crud, sample_world_state):
        """Test that save creates a new world state when it doesn't exist."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock query to return None (not found)
            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            # Mock model creation
            mock_model = MagicMock()
            mock_model.to_domain_aggregate.return_value = sample_world_state
            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.WorldStateModel"
            ) as mock_model_class:
                mock_model_class.from_domain_aggregate.return_value = mock_model

                result = await crud.save(sample_world_state)

                assert result.id == sample_world_state.id
                assert result.version == 1
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_updates_existing_world_state(self, crud, sample_world_state):
        """Test that save updates an existing world state."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock existing model
            mock_existing_model = MagicMock()
            mock_existing_model.version = 1
            mock_existing_model.to_domain_aggregate.return_value = sample_world_state
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_existing_model
            )

            result = await crud.save(sample_world_state)

            assert result is not None
            mock_existing_model.update_from_domain_aggregate.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_raises_concurrency_exception_on_version_conflict(
        self, crud, sample_world_state
    ):
        """Test that save raises ConcurrencyException on version conflict."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            ConcurrencyException,
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock existing model with different version
            mock_existing_model = MagicMock()
            mock_existing_model.version = 5  # Different from world_state.version
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_existing_model
            )

            sample_world_state.version = 1  # Conflicts with existing version 5

            with pytest.raises(ConcurrencyException):
                await crud.save(sample_world_state)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_world_state(self, crud, sample_world_state):
        """Test that get_by_id returns the world state when found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock model
            mock_model = MagicMock()
            mock_model.to_domain_aggregate.return_value = sample_world_state
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_model
            )

            result = await crud.get_by_id("test-world-123")

            assert result is not None
            assert result.id == sample_world_state.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(self, crud):
        """Test that get_by_id returns None when world state not found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock query to return None
            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            result = await crud.get_by_id("non-existent-id")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_returns_world_state(
        self, crud, sample_world_state
    ):
        """Test that get_by_id_or_raise returns the world state when found."""
        with patch.object(crud, "get_by_id", return_value=sample_world_state):
            result = await crud.get_by_id_or_raise("test-world-123")

            assert result.id == sample_world_state.id

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_raises_when_not_found(self, crud):
        """Test that get_by_id_or_raise raises EntityNotFoundException when not found."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            EntityNotFoundException,
        )

        with patch.object(crud, "get_by_id", return_value=None):
            with pytest.raises(EntityNotFoundException):
                await crud.get_by_id_or_raise("non-existent-id")

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(self, crud):
        """Test that delete returns True when world state is deleted."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock existing model
            mock_model = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_model
            )

            result = await crud.delete("test-world-123")

            assert result is True
            mock_model.soft_delete.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self, crud):
        """Test that delete returns False when world state not found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock query to return None
            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            result = await crud.delete("non-existent-id")

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_found(self, crud):
        """Test that exists returns True when world state exists."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock count to return 1
            mock_session.query.return_value.filter.return_value.count.return_value = 1

            result = await crud.exists("test-world-123")

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(self, crud):
        """Test that exists returns False when world state doesn't exist."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_crud.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock count to return 0
            mock_session.query.return_value.filter.return_value.count.return_value = 0

            result = await crud.exists("non-existent-id")

            assert result is False
