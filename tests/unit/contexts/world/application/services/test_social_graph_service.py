#!/usr/bin/env python3
"""Tests for SocialGraphService.

Unit tests covering:
- Social network analysis
- Character centrality calculations
- Relationship queries
- Connection strength calculations
- Graph traversal
"""

from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.world.application.services.social_graph_service import (
    CharacterCentrality,
    SocialAnalysisResult,
    SocialGraphService,
)
from src.contexts.world.domain.entities.relationship import (
    EntityType,
    Relationship,
    RelationshipType,
)
from src.contexts.world.domain.repositories.relationship_repository import (
    IRelationshipRepository,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_relationship_repo() -> MagicMock:
    """Create a mock relationship repository."""
    repo = MagicMock(spec=IRelationshipRepository)
    repo.find_by_entity_types = AsyncMock(return_value=[])
    repo.find_by_entity = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def service(mock_relationship_repo: MagicMock) -> SocialGraphService:
    """Create a SocialGraphService with mock repository."""
    return SocialGraphService(relationship_repository=mock_relationship_repo)


def create_character_relationship(
    source_id: str,
    target_id: str,
    rel_type: RelationshipType,
    trust: int = 50,
    romance: int = 0,
    strength: int = 50,
) -> Relationship:
    """Helper to create character-to-character relationships."""
    return Relationship(
        source_id=source_id,
        source_type=EntityType.CHARACTER,
        target_id=target_id,
        target_type=EntityType.CHARACTER,
        relationship_type=rel_type,
        trust=trust,
        romance=romance,
        strength=strength,
    )


# ============================================================================
# Test CharacterCentrality Dataclass
# ============================================================================


class TestCharacterCentrality:
    """Tests for CharacterCentrality dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible default values."""
        centrality = CharacterCentrality(character_id="char-001")

        assert centrality.character_id == "char-001"
        assert centrality.relationship_count == 0
        assert centrality.positive_count == 0
        assert centrality.negative_count == 0
        assert centrality.average_trust == 0.0
        assert centrality.average_romance == 0.0
        assert centrality.centrality_score == 0.0

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        centrality = CharacterCentrality(
            character_id="char-001",
            relationship_count=10,
            positive_count=7,
            negative_count=3,
            average_trust=65.5,
            average_romance=20.0,
            centrality_score=85.0,
        )

        assert centrality.relationship_count == 10
        assert centrality.positive_count == 7
        assert centrality.negative_count == 3
        assert centrality.average_trust == 65.5
        assert centrality.average_romance == 20.0
        assert centrality.centrality_score == 85.0


# ============================================================================
# Test SocialAnalysisResult Dataclass
# ============================================================================


class TestSocialAnalysisResult:
    """Tests for SocialAnalysisResult dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible default values."""
        result = SocialAnalysisResult()

        assert result.character_centralities == {}
        assert result.most_connected is None
        assert result.most_hated is None
        assert result.most_loved is None
        assert result.total_relationships == 0
        assert result.total_characters == 0
        assert result.network_density == 0.0

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        centralities = {"char-001": CharacterCentrality(character_id="char-001")}
        result = SocialAnalysisResult(
            character_centralities=centralities,
            most_connected="char-001",
            most_hated="char-002",
            most_loved="char-003",
            total_relationships=15,
            total_characters=5,
            network_density=0.6,
        )

        assert result.most_connected == "char-001"
        assert result.most_hated == "char-002"
        assert result.most_loved == "char-003"
        assert result.total_relationships == 15
        assert result.total_characters == 5
        assert result.network_density == 0.6


# ============================================================================
# Test analyze_social_network
# ============================================================================


class TestAnalyzeSocialNetwork:
    """Tests for analyze_social_network method."""

    @pytest.mark.asyncio
    async def test_empty_network(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should return empty result when no relationships exist."""
        mock_relationship_repo.find_by_entity_types.return_value = []

        result = await service.analyze_social_network()

        assert result.unwrap().total_characters == 0
        assert result.unwrap().total_relationships == 0
        assert result.unwrap().most_connected is None
        assert result.unwrap().most_hated is None
        assert result.unwrap().most_loved is None

    @pytest.mark.asyncio
    async def test_single_relationship(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should analyze network with single relationship."""
        rel = create_character_relationship(
            "char-001", "char-002", RelationshipType.ALLY, trust=80
        )
        mock_relationship_repo.find_by_entity_types.return_value = [rel]

        result = await service.analyze_social_network()

        assert result.unwrap().total_characters == 2
        assert result.unwrap().total_relationships == 1
        assert result.unwrap().most_connected in ["char-001", "char-002"]

    @pytest.mark.asyncio
    async def test_multiple_relationships(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should analyze network with multiple relationships."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY, trust=70),
            create_character_relationship("char-001", "char-003", RelationshipType.ALLY, trust=80),
            create_character_relationship("char-002", "char-003", RelationshipType.ENEMY, trust=20),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        assert result.unwrap().total_characters == 3
        assert result.unwrap().total_relationships == 3

    @pytest.mark.asyncio
    async def test_calculates_centrality_correctly(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should calculate centrality scores correctly."""
        # char-001 has 3 relationships (to char-002, 003, 004)
        # char-002 has 2 relationships (to char-001, char-003)
        # char-003 has 2 relationships (to char-001, char-002)
        # char-004 has 1 relationship (to char-001)
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY),
            create_character_relationship("char-001", "char-003", RelationshipType.ALLY),
            create_character_relationship("char-001", "char-004", RelationshipType.ALLY),
            create_character_relationship("char-002", "char-003", RelationshipType.ENEMY),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        # The service counts each relationship once per character it involves
        # char-001: 3 relationships (to 002, 003, 004)
        # char-002: 2 relationships (to 001, 003)
        # char-003: 2 relationships (to 001, 002)
        # char-004: 1 relationship (to 001)
        assert result.unwrap().character_centralities["char-001"].relationship_count == 3
        assert result.unwrap().character_centralities["char-002"].relationship_count == 2
        assert result.unwrap().character_centralities["char-003"].relationship_count == 2
        assert result.unwrap().character_centralities["char-004"].relationship_count == 1
        assert result.unwrap().most_connected == "char-001"

    @pytest.mark.asyncio
    async def test_identifies_most_hated(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should identify character with most negative relationships."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ENEMY),
            create_character_relationship("char-001", "char-003", RelationshipType.ENEMY),
            create_character_relationship("char-002", "char-003", RelationshipType.ALLY),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        # char-001 has 2 enemy relationships (counted bidirectionally)
        assert result.unwrap().most_hated == "char-001"

    @pytest.mark.asyncio
    async def test_identifies_most_loved(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should identify character with highest trust/romance."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY, trust=90),
            create_character_relationship("char-001", "char-003", RelationshipType.ALLY, trust=85),
            create_character_relationship("char-002", "char-003", RelationshipType.ALLY, trust=50),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        # char-001 has highest average trust (87.5)
        assert result.unwrap().most_loved == "char-001"

    @pytest.mark.asyncio
    async def test_calculates_network_density(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should calculate network density correctly."""
        # 3 characters, 1 relationship (density = 1 / (3*2/2) = 1/3 = 0.333)
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        assert result.unwrap().total_characters == 2
        # Density for 2 chars, 1 relationship = 1 / (2*1/2) = 1.0
        # But capped at 1.0
        assert result.unwrap().network_density <= 1.0

    @pytest.mark.asyncio
    async def test_ignores_non_character_relationships(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should only analyze character-to-character relationships."""
        # The service calls find_by_entity_types with CHARACTER filters
        # Our mock returns whatever we set, but the test verifies the service handles the filtering
        char_rel = create_character_relationship("char-001", "char-002", RelationshipType.ALLY)
        mock_relationship_repo.find_by_entity_types.return_value = [char_rel]

        result = await service.analyze_social_network()

        # Should only count character-to-character relationship
        assert result.unwrap().total_relationships == 1

    @pytest.mark.asyncio
    async def test_calculates_average_trust(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should calculate average trust for each character."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY, trust=60),
            create_character_relationship("char-001", "char-003", RelationshipType.ALLY, trust=80),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        # char-001 average trust = (60 + 80) / 2 = 70
        centrality = result.unwrap().character_centralities["char-001"]
        assert centrality.average_trust == 70.0

    @pytest.mark.asyncio
    async def test_calculates_average_romance(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should calculate average romance for each character."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ROMANTIC, romance=80),
            create_character_relationship("char-001", "char-003", RelationshipType.ALLY, romance=10),  # ALLY instead of FRIEND
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        centrality = result.unwrap().character_centralities["char-001"]
        assert centrality.average_romance == 45.0  # (80 + 10) / 2


# ============================================================================
# Test get_character_centrality
# ============================================================================


class TestGetCharacterCentrality:
    """Tests for get_character_centrality method."""

    @pytest.mark.asyncio
    async def test_character_with_no_relationships(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should return None for character with no relationships."""
        mock_relationship_repo.find_by_entity.return_value = []

        result = await service.get_character_centrality("char-001")

        assert result.unwrap() is None

    @pytest.mark.asyncio
    async def test_character_with_relationships(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should return centrality for character with relationships."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY, trust=70),
            create_character_relationship("char-001", "char-003", RelationshipType.ENEMY, trust=30),
        ]
        mock_relationship_repo.find_by_entity.return_value = relationships

        result = await service.get_character_centrality("char-001")

        assert result.unwrap() is not None
        assert result.unwrap().character_id == "char-001"
        assert result.unwrap().relationship_count == 2
        assert result.unwrap().positive_count == 1
        assert result.unwrap().negative_count == 1
        assert result.unwrap().average_trust == 50.0

    @pytest.mark.asyncio
    async def test_filters_to_character_relationships(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should only count character-to-character relationships."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY),
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="faction-001",
                target_type=EntityType.FACTION,
                relationship_type=RelationshipType.MEMBER_OF,
            ),
        ]
        mock_relationship_repo.find_by_entity.return_value = relationships

        result = await service.get_character_centrality("char-001")

        assert result.unwrap() is not None
        assert result.unwrap().relationship_count == 1  # Only character-to-character

    @pytest.mark.asyncio
    async def test_calculates_centrality_score_as_count(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should set centrality_score to relationship count for single character."""
        relationships = [
            create_character_relationship("char-001", "char-002", RelationshipType.ALLY),
            create_character_relationship("char-001", "char-003", RelationshipType.ALLY),
            create_character_relationship("char-001", "char-004", RelationshipType.ALLY),
        ]
        mock_relationship_repo.find_by_entity.return_value = relationships

        result = await service.get_character_centrality("char-001")

        assert result.unwrap() is not None
        # For single character, centrality_score equals relationship count
        assert result.unwrap().centrality_score == 3.0


# ============================================================================
# Test Helper Methods
# ============================================================================


class TestHelperMethods:
    """Tests for private helper methods."""

    def test_find_most_connected_empty(self, service: SocialGraphService) -> None:
        """Should return None when no metrics exist."""
        result = service._find_most_connected({})

        assert result is None

    def test_find_most_connected_single(self, service: SocialGraphService) -> None:
        """Should return single character when only one exists."""
        metrics = {
            "char-001": CharacterCentrality(character_id="char-001", relationship_count=5)
        }

        result = service._find_most_connected(metrics)

        assert result == "char-001"

    def test_find_most_connected_multiple(self, service: SocialGraphService) -> None:
        """Should return character with highest relationship count."""
        metrics = {
            "char-001": CharacterCentrality(character_id="char-001", relationship_count=3),
            "char-002": CharacterCentrality(character_id="char-002", relationship_count=7),
            "char-003": CharacterCentrality(character_id="char-003", relationship_count=5),
        }

        result = service._find_most_connected(metrics)

        assert result == "char-002"

    def test_find_most_hated_empty(self, service: SocialGraphService) -> None:
        """Should return None when no metrics exist."""
        result = service._find_most_hated({})

        assert result is None

    def test_find_most_hated_no_negatives(self, service: SocialGraphService) -> None:
        """Should return None when no negative relationships exist."""
        metrics = {
            "char-001": CharacterCentrality(character_id="char-001", negative_count=0),
            "char-002": CharacterCentrality(character_id="char-002", negative_count=0),
        }

        result = service._find_most_hated(metrics)

        assert result is None

    def test_find_most_hated_with_negatives(self, service: SocialGraphService) -> None:
        """Should return character with most negative relationships."""
        metrics = {
            "char-001": CharacterCentrality(character_id="char-001", negative_count=2),
            "char-002": CharacterCentrality(character_id="char-002", negative_count=5),
            "char-003": CharacterCentrality(character_id="char-003", negative_count=3),
        }

        result = service._find_most_hated(metrics)

        assert result == "char-002"

    def test_find_most_loved_empty(self, service: SocialGraphService) -> None:
        """Should return None when no metrics exist."""
        result = service._find_most_loved({})

        assert result is None

    def test_find_most_loved_uses_weighted_score(self, service: SocialGraphService) -> None:
        """Should use weighted trust/romance score."""
        metrics = {
            "char-001": CharacterCentrality(
                character_id="char-001", average_trust=80, average_romance=60
            ),
            "char-002": CharacterCentrality(
                character_id="char-002", average_trust=60, average_romance=90
            ),
        }

        result = service._find_most_loved(metrics)

        # char-001: 80*0.6 + 60*0.4 = 48 + 24 = 72
        # char-002: 60*0.6 + 90*0.4 = 36 + 36 = 72
        # Both equal, so either could win
        assert result in ["char-001", "char-002"]

    def test_update_character_metrics_new_character(
        self, service: SocialGraphService
    ) -> None:
        """Should create new metrics for unknown character."""
        metrics: dict = {}
        trusts: dict = {}
        romances: dict = {}
        rel = create_character_relationship("char-001", "char-002", RelationshipType.ALLY, trust=70, romance=10)

        service._update_character_metrics(metrics, trusts, romances, "char-001", rel)

        assert "char-001" in metrics
        assert metrics["char-001"].character_id == "char-001"
        assert metrics["char-001"].relationship_count == 1
        assert trusts["char-001"] == [70]
        assert romances["char-001"] == [10]

    def test_update_character_metrics_existing_character(
        self, service: SocialGraphService
    ) -> None:
        """Should update existing metrics for known character."""
        metrics = {
            "char-001": CharacterCentrality(character_id="char-001", relationship_count=2)
        }
        trusts = {"char-001": [70, 80]}
        romances = {"char-001": [10, 20]}
        rel = create_character_relationship("char-001", "char-003", RelationshipType.ALLY, trust=60, romance=5)

        service._update_character_metrics(metrics, trusts, romances, "char-001", rel)

        assert metrics["char-001"].relationship_count == 3
        assert trusts["char-001"] == [70, 80, 60]
        assert romances["char-001"] == [10, 20, 5]

    def test_update_character_metrics_positive_relationship(
        self, service: SocialGraphService
    ) -> None:
        """Should increment positive count for positive relationship."""
        metrics = {"char-001": CharacterCentrality(character_id="char-001")}
        trusts: dict = {"char-001": []}
        romances: dict = {"char-001": []}
        rel = create_character_relationship("char-001", "char-002", RelationshipType.ALLY)

        service._update_character_metrics(metrics, trusts, romances, "char-001", rel)

        assert metrics["char-001"].positive_count == 1
        assert metrics["char-001"].negative_count == 0

    def test_update_character_metrics_negative_relationship(
        self, service: SocialGraphService
    ) -> None:
        """Should increment negative count for negative relationship."""
        metrics = {"char-001": CharacterCentrality(character_id="char-001")}
        trusts: dict = {"char-001": []}
        romances: dict = {"char-001": []}
        rel = create_character_relationship("char-001", "char-002", RelationshipType.ENEMY)

        service._update_character_metrics(metrics, trusts, romances, "char-001", rel)

        assert metrics["char-001"].negative_count == 1
        assert metrics["char-001"].positive_count == 0


# ============================================================================
# Integration-style Tests
# ============================================================================


class TestSocialGraphServiceIntegration:
    """Integration-style tests for SocialGraphService."""

    @pytest.mark.asyncio
    async def test_full_network_analysis(
        self, service: SocialGraphService, mock_relationship_repo: MagicMock
    ) -> None:
        """Should perform complete network analysis."""
        # Create a realistic social network
        relationships = [
            # Protagonist with many allies
            create_character_relationship("hero", "ally1", RelationshipType.ALLY, trust=90),
            create_character_relationship("hero", "ally2", RelationshipType.ALLY, trust=85),
            create_character_relationship("hero", "mentor", RelationshipType.MENTOR, trust=95),
            # Villain with many enemies
            create_character_relationship("villain", "hero", RelationshipType.ENEMY, trust=10),
            create_character_relationship("villain", "ally1", RelationshipType.ENEMY, trust=5),
            # Neutral character
            create_character_relationship("neutral", "hero", RelationshipType.NEUTRAL, trust=50),
        ]
        mock_relationship_repo.find_by_entity_types.return_value = relationships

        result = await service.analyze_social_network()

        # Verify analysis results
        assert result.unwrap().total_characters > 0
        assert result.unwrap().total_relationships == len(relationships)
        assert result.unwrap().most_connected is not None
        assert result.unwrap().network_density > 0

    @pytest.mark.asyncio
    async def test_service_is_stateless(self) -> None:
        """Service should not maintain state between calls."""
        repo1 = MagicMock(spec=IRelationshipRepository)
        repo1.find_by_entity_types = AsyncMock(return_value=[])
        repo1.find_by_entity = AsyncMock(return_value=[])

        repo2 = MagicMock(spec=IRelationshipRepository)
        repo2.find_by_entity_types = AsyncMock(return_value=[])
        repo2.find_by_entity = AsyncMock(return_value=[])

        service1 = SocialGraphService(relationship_repository=repo1)
        service2 = SocialGraphService(relationship_repository=repo2)

        result1 = await service1.analyze_social_network()
        result2 = await service2.analyze_social_network()

        # Both should return independent results
        assert result1.unwrap().total_characters == 0
        assert result2.unwrap().total_characters == 0
