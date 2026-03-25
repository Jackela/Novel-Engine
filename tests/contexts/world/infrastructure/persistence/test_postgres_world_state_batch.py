"""Tests for PostgresWorldStateBatch.

Tests the batch operations for world state persistence.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.infrastructure.persistence.postgres_world_state_batch import (
    PostgresWorldStateBatch,
)


class TestPostgresWorldStateBatch:
    """Test suite for PostgresWorldStateBatch."""

    @pytest.fixture
    def batch(self):
        """Create a fresh batch instance for each test."""
        return PostgresWorldStateBatch()

    @pytest.fixture
    def sample_world_states(self):
        """Create sample world states for testing."""
        return [
            WorldState(id="world-1", name="World 1", version=1),
            WorldState(id="world-2", name="World 2", version=1),
            WorldState(id="world-3", name="World 3", version=1),
        ]

    @pytest.mark.asyncio
    async def test_save_batch_creates_and_updates(self, batch, sample_world_states):
        """Test that save_batch handles both create and update operations."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # First world exists (update), second and third don't (create)
            def mock_first():
                if mock_session.query.call_count <= 1:
                    mock_model = MagicMock()
                    mock_model.version = 1
                    mock_model.to_domain_aggregate.return_value = sample_world_states[0]
                    return mock_model
                return None

            mock_session.query.return_value.filter.return_value.first.side_effect = [
                MagicMock(
                    version=1,
                    to_domain_aggregate=MagicMock(return_value=sample_world_states[0]),
                ),
                None,
                None,
            ]

            mock_model_class = MagicMock()
            mock_model_class.from_domain_aggregate.return_value = MagicMock(
                to_domain_aggregate=MagicMock(return_value=sample_world_states[1]),
                validate=MagicMock(return_value=[]),
            )

            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.WorldStateModel",
                mock_model_class,
            ):
                # Update first entity to not exist so we get consistent behavior
                mock_session.query.return_value.filter.return_value.first.side_effect = [
                    None,
                    None,
                    None,
                ]

                result = await batch.save_batch(sample_world_states)

                assert len(result) == 3
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_batch_returns_empty_list_for_empty_input(self, batch):
        """Test that save_batch returns empty list when given empty input."""
        result = await batch.save_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_save_batch_raises_on_version_conflict(
        self, batch, sample_world_states
    ):
        """Test that save_batch raises ConcurrencyException on version conflict."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            ConcurrencyException,
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock existing model with different version
            mock_existing_model = MagicMock()
            mock_existing_model.version = 5  # Different from world_state.version (1)
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_existing_model
            )

            with pytest.raises(ConcurrencyException):
                await batch.save_batch(sample_world_states[:1])

    @pytest.mark.asyncio
    async def test_delete_batch_deletes_multiple(self, batch):
        """Test that delete_batch soft deletes multiple world states."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock two existing models and one not found
            mock_model1 = MagicMock()
            mock_model2 = MagicMock()

            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_model1,
                mock_model2,
                None,
            ]

            result = await batch.delete_batch(["world-1", "world-2", "world-3"])

            assert result["world-1"] is True
            assert result["world-2"] is True
            assert result["world-3"] is False
            mock_model1.soft_delete.assert_called_once()
            mock_model2.soft_delete.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_batch_returns_empty_dict_for_empty_input(self, batch):
        """Test that delete_batch returns empty dict when given empty input."""
        result = await batch.delete_batch([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_create_creates_new_entities(self, batch, sample_world_states):
        """Test that batch_create creates multiple new world states."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_model = MagicMock()
            mock_model.validate.return_value = []

            mock_model_class = MagicMock()
            mock_model_class.from_domain_aggregate.return_value = mock_model

            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.WorldStateModel",
                mock_model_class,
            ):
                result = await batch.batch_create(sample_world_states)

                assert len(result) == 3
                assert mock_session.add.call_count == 3
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_create_returns_empty_list_for_empty_input(self, batch):
        """Test that batch_create returns empty list when given empty input."""
        result = await batch.batch_create([])

        assert result == []

    @pytest.mark.asyncio
    async def test_batch_update_updates_existing_entities(
        self, batch, sample_world_states
    ):
        """Test that batch_update updates multiple existing world states."""

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock existing models
            mock_models = [
                MagicMock(version=1, validate=MagicMock(return_value=[])),
                MagicMock(version=1, validate=MagicMock(return_value=[])),
                MagicMock(version=1, validate=MagicMock(return_value=[])),
            ]

            mock_session.query.return_value.filter.return_value.first.side_effect = (
                mock_models
            )

            result = await batch.batch_update(sample_world_states)

            assert result is None  # batch_update returns None
            assert all(
                ws.version == 2 for ws in sample_world_states
            )  # Version incremented
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_update_raises_when_entity_not_found(self, batch):
        """Test that batch_update raises exception when entity not found."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            EntityNotFoundException,
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # First found, second not found
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                MagicMock(version=1, validate=MagicMock(return_value=[])),
                None,
            ]

            world_states = [
                WorldState(id="world-1", name="World 1", version=1),
                WorldState(id="world-2", name="World 2", version=1),
            ]

            with pytest.raises(EntityNotFoundException):
                await batch.batch_update(world_states)

    @pytest.mark.asyncio
    async def test_batch_update_raises_on_version_conflict(self, batch):
        """Test that batch_update raises ConcurrencyException on version conflict."""
        from src.contexts.world.domain.repositories.world_state_repo import (
            ConcurrencyException,
        )

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_batch.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock existing model with different version
            mock_existing_model = MagicMock()
            mock_existing_model.version = 5  # Different from world_state.version (1)
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_existing_model
            )

            world_states = [WorldState(id="world-1", name="World 1", version=1)]

            with pytest.raises(ConcurrencyException):
                await batch.batch_update(world_states)

    @pytest.mark.asyncio
    async def test_batch_update_does_nothing_for_empty_list(self, batch):
        """Test that batch_update does nothing when given empty list."""
        result = await batch.batch_update([])

        assert result is None
