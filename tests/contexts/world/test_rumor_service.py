#!/usr/bin/env python3
"""Comprehensive tests for RumorService.

This module provides test coverage for the RumorService including:
- Getting location rumors with sorting
- Getting world rumors with filtering
- Getting individual rumor details
- Sorting rumors by various criteria
- Veracity label calculation
- Propagation graph building

Total: 35 tests
"""


import pytest

from src.api.schemas.world_schemas import SortByEnum
from src.contexts.world.application.services.rumor_service import (
    RumorService,
)
from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.contexts.world.infrastructure.persistence.in_memory_rumor_repository import (
    InMemoryRumorRepository,
)

pytestmark = pytest.mark.unit



@pytest.fixture
def rumor_repo():
    """Create a fresh rumor repository for each test."""
    repo = InMemoryRumorRepository()
    yield repo


@pytest.fixture
def rumor_service(rumor_repo):
    """Create a fresh RumorService for each test."""
    return RumorService(rumor_repo=rumor_repo)


@pytest.fixture
def sample_rumor():
    """Create a sample rumor for testing."""
    return Rumor(
        rumor_id="rumor-1",
        content="A dragon has been sighted in the north.",
        truth_value=75,
        origin_type=RumorOrigin.EVENT,
        origin_location_id="loc-north",
        current_locations={"loc-north", "loc-capital"},
        created_date=WorldCalendar(year=1000, month=1, day=1, era_name="First Age"),
        spread_count=2,
    )


@pytest.fixture
def multiple_rumors():
    """Create multiple rumors for testing."""
    return [
        Rumor(
            rumor_id="rumor-1",
            content="Dragon sighted in the north",
            truth_value=90,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1", "loc-2"},
            created_date=WorldCalendar(year=1000, month=1, day=1, era_name="First Age"),
            spread_count=5,
        ),
        Rumor(
            rumor_id="rumor-2",
            content="War declared between kingdoms",
            truth_value=60,
            origin_type=RumorOrigin.NPC,
            origin_location_id="loc-2",
            current_locations={"loc-2", "loc-3"},
            created_date=WorldCalendar(year=1000, month=2, day=1, era_name="First Age"),
            spread_count=10,
        ),
        Rumor(
            rumor_id="rumor-3",
            content="Treasure hidden in the forest",
            truth_value=30,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-3",
            current_locations={"loc-3"},
            created_date=WorldCalendar(year=999, month=12, day=1, era_name="First Age"),
            spread_count=1,
        ),
    ]


# =============================================================================
# Test RumorService Initialization (3 tests)
# =============================================================================


class TestRumorServiceInitialization:
    """Tests for RumorService initialization."""

    def test_service_initialization_with_repository(self, rumor_repo):
        """Test that service initializes with valid repository."""
        service = RumorService(rumor_repo=rumor_repo)
        assert service._rumor_repo is rumor_repo

    def test_service_initialization_sets_repository_correctly(self, rumor_repo):
        """Test that repository is set correctly during initialization."""
        service = RumorService(rumor_repo=rumor_repo)
        assert isinstance(service._rumor_repo, InMemoryRumorRepository)


# =============================================================================
# Test get_location_rumors (8 tests)
# =============================================================================


class TestGetLocationRumors:
    """Tests for get_location_rumors method."""

    @pytest.mark.asyncio
    async def test_get_location_rumors_success(self, rumor_service, rumor_repo, sample_rumor):
        """Test successful retrieval of location rumors."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_location_rumors(
            location_id="loc-capital",
            world_id="world-1",
        )

        assert result.is_ok
        rumors = result.value
        assert len(rumors) == 1
        assert rumors[0].rumor_id == "rumor-1"

    @pytest.mark.asyncio
    async def test_get_location_rumors_empty(self, rumor_service):
        """Test getting rumors from location with none."""
        result = await rumor_service.get_location_rumors(
            location_id="loc-empty",
            world_id="world-1",
        )

        assert result.is_ok
        assert result.value == []

    @pytest.mark.asyncio
    async def test_get_location_rumors_sort_by_recent(self, rumor_service, rumor_repo, multiple_rumors):
        """Test sorting rumors by recent."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_location_rumors(
            location_id="loc-2",
            world_id="world-1",
            sort_by=SortByEnum.RECENT,
        )

        assert result.is_ok
        rumors = result.value
        # Most recent first
        assert rumors[0].rumor_id == "rumor-2"  # Feb 1

    @pytest.mark.asyncio
    async def test_get_location_rumors_sort_by_reliable(self, rumor_service, rumor_repo, multiple_rumors):
        """Test sorting rumors by reliability (truth value)."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_location_rumors(
            location_id="loc-1",
            world_id="world-1",
            sort_by=SortByEnum.RELIABLE,
        )

        assert result.is_ok
        rumors = result.value
        # Most reliable first
        assert rumors[0].truth_value == 90

    @pytest.mark.asyncio
    async def test_get_location_rumors_sort_by_spread(self, rumor_service, rumor_repo, multiple_rumors):
        """Test sorting rumors by spread count."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_location_rumors(
            location_id="loc-2",
            world_id="world-1",
            sort_by=SortByEnum.SPREAD,
        )

        assert result.is_ok
        rumors = result.value
        # Most spread first
        assert rumors[0].spread_count == 10

    @pytest.mark.asyncio
    async def test_get_location_rumors_with_limit(self, rumor_service, rumor_repo, multiple_rumors):
        """Test limiting number of returned rumors."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_location_rumors(
            location_id="loc-2",
            world_id="world-1",
            limit=1,
        )

        assert result.is_ok
        assert len(result.value) == 1

    @pytest.mark.asyncio
    async def test_get_location_rumors_not_at_location(self, rumor_service, rumor_repo, sample_rumor):
        """Test that rumors not at the location are not returned."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_location_rumors(
            location_id="loc-not-in-rumor",
            world_id="world-1",
        )

        assert result.is_ok
        assert len(result.value) == 0


# =============================================================================
# Test get_world_rumors (6 tests)
# =============================================================================


class TestGetWorldRumors:
    """Tests for get_world_rumors method."""

    @pytest.mark.asyncio
    async def test_get_world_rumors_success(self, rumor_service, rumor_repo, multiple_rumors):
        """Test successful retrieval of world rumors."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_world_rumors(world_id="world-1")

        assert result.is_ok
        assert len(result.value) == 3

    @pytest.mark.asyncio
    async def test_get_world_rumors_empty(self, rumor_service):
        """Test getting rumors from world with none."""
        result = await rumor_service.get_world_rumors(world_id="empty-world")

        assert result.is_ok
        assert result.value == []

    @pytest.mark.asyncio
    async def test_get_world_rumors_filtered_by_location(self, rumor_service, rumor_repo, multiple_rumors):
        """Test filtering world rumors by location."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_world_rumors(
            world_id="world-1",
            location_id="loc-1",
        )

        assert result.is_ok
        # Only rumors at loc-1
        assert len(result.value) == 1

    @pytest.mark.asyncio
    async def test_get_world_rumors_with_sorting(self, rumor_service, rumor_repo, multiple_rumors):
        """Test world rumors with sorting."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_world_rumors(
            world_id="world-1",
            sort_by=SortByEnum.RELIABLE,
        )

        assert result.is_ok
        rumors = result.value
        # Check sorted by truth value descending
        for i in range(len(rumors) - 1):
            assert rumors[i].truth_value >= rumors[i + 1].truth_value

    @pytest.mark.asyncio
    async def test_get_world_rumors_with_limit(self, rumor_service, rumor_repo, multiple_rumors):
        """Test limiting world rumors."""
        for rumor in multiple_rumors:
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(rumor.rumor_id, "world-1")

        result = await rumor_service.get_world_rumors(
            world_id="world-1",
            limit=2,
        )

        assert result.is_ok
        assert len(result.value) == 2


# =============================================================================
# Test get_rumor (6 tests)
# =============================================================================


class TestGetRumor:
    """Tests for get_rumor method."""

    @pytest.mark.asyncio
    async def test_get_rumor_found(self, rumor_service, rumor_repo, sample_rumor):
        """Test retrieving an existing rumor."""
        await rumor_repo.save(sample_rumor)

        result = await rumor_service.get_rumor(
            rumor_id="rumor-1",
            world_id="world-1",
        )

        assert result.is_ok
        assert result.value is not None
        assert result.value.rumor_id == "rumor-1"

    @pytest.mark.asyncio
    async def test_get_rumor_not_found(self, rumor_service):
        """Test retrieving a non-existent rumor."""
        result = await rumor_service.get_rumor(
            rumor_id="non-existent",
            world_id="world-1",
        )

        assert result.is_ok
        assert result.value is None

    @pytest.mark.asyncio
    async def test_get_rumor_returns_rumor_type(self, rumor_service, rumor_repo, sample_rumor):
        """Test that get_rumor returns Rumor type."""
        await rumor_repo.save(sample_rumor)

        result = await rumor_service.get_rumor(
            rumor_id="rumor-1",
            world_id="world-1",
        )

        assert result.is_ok
        assert isinstance(result.value, Rumor)

    @pytest.mark.asyncio
    async def test_get_rumor_correct_content(self, rumor_service, rumor_repo, sample_rumor):
        """Test that retrieved rumor has correct content."""
        await rumor_repo.save(sample_rumor)

        result = await rumor_service.get_rumor(
            rumor_id="rumor-1",
            world_id="world-1",
        )

        assert result.is_ok
        assert result.value.content == sample_rumor.content
        assert result.value.truth_value == sample_rumor.truth_value


# =============================================================================
# Test get_veracity_label (6 tests)
# =============================================================================


class TestGetVeracityLabel:
    """Tests for get_veracity_label static method."""

    def test_veracity_label_confirmed(self):
        """Test label for confirmed truth (>=80)."""
        assert RumorService.get_veracity_label(80) == "Confirmed"
        assert RumorService.get_veracity_label(90) == "Confirmed"
        assert RumorService.get_veracity_label(100) == "Confirmed"

    def test_veracity_label_likely_true(self):
        """Test label for likely true (60-79)."""
        assert RumorService.get_veracity_label(60) == "Likely True"
        assert RumorService.get_veracity_label(70) == "Likely True"
        assert RumorService.get_veracity_label(79) == "Likely True"

    def test_veracity_label_uncertain(self):
        """Test label for uncertain (40-59)."""
        assert RumorService.get_veracity_label(40) == "Uncertain"
        assert RumorService.get_veracity_label(50) == "Uncertain"
        assert RumorService.get_veracity_label(59) == "Uncertain"

    def test_veracity_label_likely_false(self):
        """Test label for likely false (20-39)."""
        assert RumorService.get_veracity_label(20) == "Likely False"
        assert RumorService.get_veracity_label(30) == "Likely False"
        assert RumorService.get_veracity_label(39) == "Likely False"

    def test_veracity_label_false(self):
        """Test label for false (<20)."""
        assert RumorService.get_veracity_label(0) == "False"
        assert RumorService.get_veracity_label(10) == "False"
        assert RumorService.get_veracity_label(19) == "False"


# =============================================================================
# Test get_propagation_graph (6 tests)
# =============================================================================


class TestGetPropagationGraph:
    """Tests for get_propagation_graph method."""

    @pytest.mark.asyncio
    async def test_get_propagation_graph_success(self, rumor_service, rumor_repo, sample_rumor):
        """Test successful graph generation."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_propagation_graph(world_id="world-1")

        assert result.is_ok
        data = result.value
        assert data["world_id"] == "world-1"
        assert "graph" in data
        assert "nodes" in data["graph"]
        assert "edges" in data["graph"]
        assert "metadata" in data

    @pytest.mark.asyncio
    async def test_get_propagation_graph_specific_rumor(self, rumor_service, rumor_repo, sample_rumor):
        """Test graph for specific rumor."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_propagation_graph(
            world_id="world-1",
            rumor_id="rumor-1",
        )

        assert result.is_ok
        assert result.value["world_id"] == "world-1"

    @pytest.mark.asyncio
    async def test_get_propagation_graph_empty_world(self, rumor_service):
        """Test graph for world with no rumors."""
        result = await rumor_service.get_propagation_graph(world_id="empty-world")

        assert result.is_ok
        data = result.value
        assert data["graph"]["nodes"] == []
        assert data["graph"]["edges"] == []
        assert data["metadata"]["total_nodes"] == 0

    @pytest.mark.asyncio
    async def test_get_propagation_graph_node_types(self, rumor_service, rumor_repo, sample_rumor):
        """Test that graph contains correct node types."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_propagation_graph(world_id="world-1")

        assert result.is_ok
        nodes = result.value["graph"]["nodes"]
        
        # Should have rumor node and location nodes
        node_types = {node["type"] for node in nodes}
        assert "rumor" in node_types
        assert "location" in node_types

    @pytest.mark.asyncio
    async def test_get_propagation_graph_edge_types(self, rumor_service, rumor_repo, sample_rumor):
        """Test that graph contains correct edge types."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_propagation_graph(world_id="world-1")

        assert result.is_ok
        edges = result.value["graph"]["edges"]
        
        # Should have origin and spread edges
        edge_types = {edge["type"] for edge in edges}
        assert "origin" in edge_types
        assert "spread" in edge_types

    @pytest.mark.asyncio
    async def test_get_propagation_graph_metadata(self, rumor_service, rumor_repo, sample_rumor):
        """Test graph metadata."""
        await rumor_repo.save(sample_rumor)
        rumor_repo.register_rumor_world(sample_rumor.rumor_id, "world-1")

        result = await rumor_service.get_propagation_graph(world_id="world-1")

        assert result.is_ok
        metadata = result.value["metadata"]
        assert "total_nodes" in metadata
        assert "total_edges" in metadata
        assert "max_hops" in metadata
        assert metadata["total_nodes"] > 0
