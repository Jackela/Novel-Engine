"""Tests for PostgresWorldStateQueries.

Tests the query operations for world state persistence.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.value_objects.coordinates import Coordinates
from src.contexts.world.infrastructure.persistence.postgres_world_state_queries import (
    PostgresWorldStateQueries,
)


class TestPostgresWorldStateQueries:
    """Test suite for PostgresWorldStateQueries."""

    @pytest.fixture
    def queries(self):
        """Create a fresh queries instance for each test."""
        return PostgresWorldStateQueries()

    @pytest.fixture
    def sample_world_states(self):
        """Create sample world states for testing."""
        return [
            WorldState(id="world-1", name="World 1", version=1),
            WorldState(id="world-2", name="World 2", version=1),
            WorldState(id="world-3", name="World 3", version=1),
        ]

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_results(
        self, queries, sample_world_states
    ):
        """Test that get_all returns paginated world states."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock models
            mock_models = [MagicMock() for _ in sample_world_states]
            for i, model in enumerate(mock_models):
                model.to_domain_aggregate.return_value = sample_world_states[i]

            mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_models

            result = await queries.get_all(offset=0, limit=10)

            assert len(result) == 3
            assert result[0].id == "world-1"

    @pytest.mark.asyncio
    async def test_find_by_name_returns_world_state(self, queries):
        """Test that find_by_name returns the world state when found."""
        world_state = WorldState(id="world-1", story_id="test-story-123", version=1)

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_model = MagicMock()
            mock_model.to_domain_aggregate.return_value = world_state
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_model
            )

            result = await queries.find_by_name("Test World")

            assert result is not None
            assert result.name == "Test World"

    @pytest.mark.asyncio
    async def test_find_by_name_returns_none_when_not_found(self, queries):
        """Test that find_by_name returns None when not found."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            result = await queries.find_by_name("Non Existent")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_by_criteria_with_name_filter(self, queries):
        """Test that find_by_criteria filters by name."""
        world_state = WorldState(id="world-1", story_id="test-story-123", version=1)

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_model = MagicMock()
            mock_model.to_domain_aggregate.return_value = world_state
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [mock_model]

            result = await queries.find_by_criteria(
                {"name": "Test"}, offset=0, limit=10
            )

            assert len(result) == 1
            mock_query.filter.assert_any_call(mock_query.filter.call_args[0][0])

    @pytest.mark.asyncio
    async def test_count_returns_total(self, queries):
        """Test that count returns the total number of world states."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_session.query.return_value.filter.return_value.count.return_value = 42

            result = await queries.count()

            assert result == 42

    @pytest.mark.asyncio
    async def test_count_with_criteria(self, queries):
        """Test that count returns filtered count."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 5

            result = await queries.count({"status": "active"})

            assert result == 5

    @pytest.mark.asyncio
    async def test_find_entities_by_type_returns_matching_entities(self, queries):
        """Test that find_entities_by_type returns entities of the specified type."""

        world_state = WorldState(id="world-1", story_id="test-story-123", version=1)

        # Create mock entities
        entity1 = MagicMock()
        entity1.entity_type = MagicMock()
        entity1.entity_type.value = "character"
        entity1.to_dict.return_value = {"id": "ent-1", "type": "character"}

        entity2 = MagicMock()
        entity2.entity_type = MagicMock()
        entity2.entity_type.value = "item"
        entity2.to_dict.return_value = {"id": "ent-2", "type": "item"}

        world_state.entities = {"ent-1": entity1, "ent-2": entity2}

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.PostgresWorldStateCrud"
        ) as mock_crud_class:
            mock_crud = MagicMock()
            mock_crud.get_by_id_or_raise.return_value = world_state
            mock_crud_class.return_value = mock_crud

            result = await queries.find_entities_by_type("world-1", "character")

            assert len(result) == 1
            assert result[0]["id"] == "ent-1"

    @pytest.mark.asyncio
    async def test_find_entities_in_area_returns_entities_within_radius(self, queries):
        """Test that find_entities_in_area returns entities within the specified radius."""
        world_state = WorldState(id="world-1", story_id="test-story-123", version=1)

        # Create mock entities with coordinates
        entity1 = MagicMock()
        entity1.entity_type = MagicMock()
        entity1.entity_type.value = "character"
        entity1.coordinates = MagicMock()
        entity1.coordinates.distance_to.return_value = 50.0  # Within radius
        entity1.to_dict.return_value = {"id": "ent-1", "type": "character"}

        entity2 = MagicMock()
        entity2.entity_type = MagicMock()
        entity2.entity_type.value = "character"
        entity2.coordinates = MagicMock()
        entity2.coordinates.distance_to.return_value = 150.0  # Outside radius
        entity2.to_dict.return_value = {"id": "ent-2", "type": "character"}

        world_state.entities = {"ent-1": entity1, "ent-2": entity2}

        center = Coordinates(x=0.0, y=0.0, z=0.0)

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.PostgresWorldStateCrud"
        ) as mock_crud_class:
            mock_crud = MagicMock()
            mock_crud.get_by_id_or_raise.return_value = world_state
            mock_crud_class.return_value = mock_crud

            result = await queries.find_entities_in_area("world-1", center, 100.0)

            assert len(result) == 1
            assert result[0]["id"] == "ent-1"

    @pytest.mark.asyncio
    async def test_find_entities_by_coordinates_returns_close_entities(self, queries):
        """Test that find_entities_by_coordinates returns entities near coordinates."""
        world_state = WorldState(id="world-1", story_id="test-story-123", version=1)

        entity1 = MagicMock()
        entity1.coordinates = MagicMock()
        entity1.coordinates.distance_to.return_value = 5.0  # Within tolerance
        entity1.to_dict.return_value = {"id": "ent-1"}

        entity2 = MagicMock()
        entity2.coordinates = MagicMock()
        entity2.coordinates.distance_to.return_value = 15.0  # Outside tolerance
        entity2.to_dict.return_value = {"id": "ent-2"}

        world_state.entities = {"ent-1": entity1, "ent-2": entity2}

        target = Coordinates(x=10.0, y=10.0, z=0.0)

        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.PostgresWorldStateCrud"
        ) as mock_crud_class:
            mock_crud = MagicMock()
            mock_crud.get_by_id_or_raise.return_value = world_state
            mock_crud_class.return_value = mock_crud

            result = await queries.find_entities_by_coordinates(
                "world-1", target, tolerance=10.0
            )

            assert len(result) == 1
            assert result[0]["id"] == "ent-1"

    @pytest.mark.asyncio
    async def test_get_statistics_for_specific_world(self, queries):
        """Test that get_statistics returns stats for a specific world state."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock world state model
            mock_model = MagicMock()
            mock_model.version = 5
            mock_model.status = "active"
            mock_model.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_model.updated_at.isoformat.return_value = "2024-01-02T00:00:00"
            mock_model.get_entity_count.return_value = 10
            mock_model.get_entity_types_summary.return_value = {
                "character": 5,
                "item": 5,
            }
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_model
            )

            # Mock version and snapshot counts
            mock_session.query.return_value.filter.return_value.count.side_effect = [
                10,
                3,
            ]

            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.WorldStateVersionModel"
            ):
                with patch(
                    "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.WorldStateSnapshotModel"
                ):
                    result = await queries.get_statistics("world-123")

                    assert result["world_state_id"] == "world-123"
                    assert result["entity_count"] == 10
                    assert result["current_version"] == 5

    @pytest.mark.asyncio
    async def test_get_global_statistics(self, queries):
        """Test that get_statistics returns global stats when no ID provided."""
        with patch(
            "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.get_db_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_session

            # Mock world states
            mock_world1 = MagicMock()
            mock_world1.get_entity_count.return_value = 10
            mock_world2 = MagicMock()
            mock_world2.get_entity_count.return_value = 20

            mock_session.query.return_value.filter.return_value.count.return_value = 5
            mock_session.query.return_value.filter.return_value.all.return_value = [
                mock_world1,
                mock_world2,
            ]

            with patch(
                "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.WorldStateVersionModel"
            ):
                with patch(
                    "src.contexts.world.infrastructure.persistence.postgres_world_state_queries.WorldStateSnapshotModel"
                ):
                    mock_session.query.return_value.count.side_effect = [100, 20]

                    result = await queries.get_statistics()

                    assert "total_world_states" in result
                    assert "total_entities" in result
                    assert "total_versions" in result
