#!/usr/bin/env python3
"""Tests for SocialGraphService.

This module tests the social network analysis service, verifying correct
calculation of centrality metrics, identification of key characters,
and network property computations.

Test coverage:
- Empty graph handling
- Single relationship analysis
- Multiple character networks
- Centrality score calculation
- Finding most connected/hated/loved characters
- Network density calculation
- Individual character centrality lookup
"""

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
from src.contexts.world.infrastructure.persistence.in_memory_relationship_repository import (
    InMemoryRelationshipRepository,
)


@pytest.fixture
def repository() -> InMemoryRelationshipRepository:
    """Create a fresh repository for each test."""
    return InMemoryRelationshipRepository()


@pytest.fixture
def service(repository: InMemoryRelationshipRepository) -> SocialGraphService:
    """Create a service with the test repository."""
    return SocialGraphService(repository)


class TestEmptyGraph:
    """Tests for empty social graphs."""

    @pytest.mark.asyncio
    async def test_analyze_empty_graph_returns_empty_result(
        self, service: SocialGraphService
    ):
        """Empty graph should return an empty analysis result."""
        result = await service.analyze_social_network()

        assert result.character_centralities == {}
        assert result.most_connected is None
        assert result.most_hated is None
        assert result.most_loved is None
        assert result.total_relationships == 0
        assert result.total_characters == 0
        assert result.network_density == 0.0

    @pytest.mark.asyncio
    async def test_get_character_centrality_returns_none_for_unknown(
        self, service: SocialGraphService
    ):
        """Unknown character should return None."""
        result = await service.get_character_centrality("nonexistent-char")
        assert result is None


class TestSingleRelationship:
    """Tests for graphs with a single relationship."""

    @pytest.mark.asyncio
    async def test_single_ally_relationship(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Single ally relationship should be counted for both characters."""
        rel = Relationship.create_character_relationship(
            source_id="alice",
            target_id="bob",
            relationship_type=RelationshipType.ALLY,
            strength=80,
        )
        rel.update_trust(75)
        await repository.save(rel)

        result = await service.analyze_social_network()

        assert result.total_relationships == 1
        assert result.total_characters == 2
        assert "alice" in result.character_centralities
        assert "bob" in result.character_centralities

        alice = result.character_centralities["alice"]
        assert alice.relationship_count == 1
        assert alice.positive_count == 1
        assert alice.negative_count == 0
        assert alice.average_trust == 75.0

    @pytest.mark.asyncio
    async def test_single_enemy_relationship(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Single enemy relationship should count as negative."""
        rel = Relationship.create_character_relationship(
            source_id="hero",
            target_id="villain",
            relationship_type=RelationshipType.ENEMY,
            strength=90,
        )
        rel.update_trust(10)
        await repository.save(rel)

        result = await service.analyze_social_network()

        hero = result.character_centralities["hero"]
        assert hero.negative_count == 1
        assert hero.positive_count == 0
        assert result.most_hated in ("hero", "villain")


class TestCentralityCalculation:
    """Tests for centrality score calculations."""

    @pytest.mark.asyncio
    async def test_centrality_normalized_to_max_relationships(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Centrality should be normalized against the most connected character."""
        # Create a star topology: center connected to 4 others
        for i in range(4):
            rel = Relationship.create_character_relationship(
                source_id="center",
                target_id=f"satellite-{i}",
                relationship_type=RelationshipType.ALLY,
            )
            await repository.save(rel)

        result = await service.analyze_social_network()

        # Center should have centrality_score of 100 (most connected)
        center = result.character_centralities["center"]
        assert center.relationship_count == 4
        assert center.centrality_score == 100.0

        # Satellites each have 1 relationship = 25% of max
        satellite = result.character_centralities["satellite-0"]
        assert satellite.relationship_count == 1
        assert satellite.centrality_score == 25.0

    @pytest.mark.asyncio
    async def test_equal_relationships_equal_centrality(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Characters with equal relationships should have equal centrality."""
        # Triangle: each character has 2 relationships
        rel1 = Relationship.create_character_relationship(
            source_id="a", target_id="b", relationship_type=RelationshipType.ALLY
        )
        rel2 = Relationship.create_character_relationship(
            source_id="b", target_id="c", relationship_type=RelationshipType.ALLY
        )
        rel3 = Relationship.create_character_relationship(
            source_id="c", target_id="a", relationship_type=RelationshipType.ALLY
        )
        await repository.save(rel1)
        await repository.save(rel2)
        await repository.save(rel3)

        result = await service.analyze_social_network()

        # All should have centrality_score of 100 (2 relationships each = max)
        assert result.character_centralities["a"].relationship_count == 2
        assert result.character_centralities["b"].relationship_count == 2
        assert result.character_centralities["c"].relationship_count == 2


class TestFindExtremes:
    """Tests for finding most connected, hated, and loved characters."""

    @pytest.mark.asyncio
    async def test_most_connected_with_clear_winner(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Character with most relationships should be most_connected."""
        # popular has 3 relationships, others have 1
        for char in ["a", "b", "c"]:
            rel = Relationship.create_character_relationship(
                source_id="popular",
                target_id=char,
                relationship_type=RelationshipType.ALLY,
            )
            await repository.save(rel)

        result = await service.analyze_social_network()

        assert result.most_connected == "popular"

    @pytest.mark.asyncio
    async def test_most_hated_requires_negative_relationships(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """most_hated should be None if no negative relationships exist."""
        rel = Relationship.create_character_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.ALLY,
        )
        await repository.save(rel)

        result = await service.analyze_social_network()

        assert result.most_hated is None

    @pytest.mark.asyncio
    async def test_most_hated_with_mixed_relationships(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Character with most enemies should be most_hated."""
        # villain has enemies with 3 characters
        for char in ["hero1", "hero2", "hero3"]:
            rel = Relationship.create_character_relationship(
                source_id="villain",
                target_id=char,
                relationship_type=RelationshipType.ENEMY,
            )
            await repository.save(rel)

        # hero1 has one ally
        ally_rel = Relationship.create_character_relationship(
            source_id="hero1",
            target_id="sidekick",
            relationship_type=RelationshipType.ALLY,
        )
        await repository.save(ally_rel)

        result = await service.analyze_social_network()

        # villain has 3 negative, heroes have 1 each
        assert result.most_hated == "villain"

    @pytest.mark.asyncio
    async def test_most_loved_uses_weighted_score(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """most_loved should use weighted trust (60%) + romance (40%)."""
        # beloved has high trust and romance
        rel1 = Relationship.create_character_relationship(
            source_id="beloved",
            target_id="friend",
            relationship_type=RelationshipType.ALLY,
        )
        rel1.update_trust(90)
        rel1.update_romance(80)
        await repository.save(rel1)

        # popular has moderate trust, no romance
        rel2 = Relationship.create_character_relationship(
            source_id="popular",
            target_id="acquaintance",
            relationship_type=RelationshipType.NEUTRAL,
        )
        rel2.update_trust(70)
        rel2.update_romance(0)
        await repository.save(rel2)

        result = await service.analyze_social_network()

        # beloved: 90*0.6 + 80*0.4 = 54 + 32 = 86
        # popular: 70*0.6 + 0*0.4 = 42
        assert result.most_loved == "beloved"


class TestNetworkDensity:
    """Tests for network density calculation."""

    @pytest.mark.asyncio
    async def test_density_for_complete_triangle(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Complete triangle (all possible connections) should have density close to 1."""
        # 3 characters, 3 relationships = complete graph
        rel1 = Relationship.create_character_relationship(
            source_id="a", target_id="b", relationship_type=RelationshipType.ALLY
        )
        rel2 = Relationship.create_character_relationship(
            source_id="b", target_id="c", relationship_type=RelationshipType.ALLY
        )
        rel3 = Relationship.create_character_relationship(
            source_id="c", target_id="a", relationship_type=RelationshipType.ALLY
        )
        await repository.save(rel1)
        await repository.save(rel2)
        await repository.save(rel3)

        result = await service.analyze_social_network()

        # Max possible for 3 nodes = 3*(3-1)/2 = 3
        # Actual = 3, density = 1.0
        assert result.network_density == 1.0

    @pytest.mark.asyncio
    async def test_density_for_star_topology(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Star topology should have low density for many satellites."""
        # Center connected to 4 satellites
        for i in range(4):
            rel = Relationship.create_character_relationship(
                source_id="center",
                target_id=f"satellite-{i}",
                relationship_type=RelationshipType.ALLY,
            )
            await repository.save(rel)

        result = await service.analyze_social_network()

        # 5 characters, max possible = 5*4/2 = 10
        # Actual = 4, density = 0.4
        assert result.network_density == pytest.approx(0.4, rel=0.01)


class TestIndividualCharacterCentrality:
    """Tests for get_character_centrality method."""

    @pytest.mark.asyncio
    async def test_get_centrality_for_existing_character(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Should return centrality for a character with relationships."""
        rel1 = Relationship.create_character_relationship(
            source_id="alice",
            target_id="bob",
            relationship_type=RelationshipType.ALLY,
        )
        rel1.update_trust(80)
        rel2 = Relationship.create_character_relationship(
            source_id="alice",
            target_id="carol",
            relationship_type=RelationshipType.ROMANTIC,
        )
        rel2.update_trust(95)
        rel2.update_romance(90)

        await repository.save(rel1)
        await repository.save(rel2)

        result = await service.get_character_centrality("alice")

        assert result is not None
        assert result.character_id == "alice"
        assert result.relationship_count == 2
        assert result.positive_count == 2
        assert result.negative_count == 0
        assert result.average_trust == pytest.approx((80 + 95) / 2, rel=0.01)
        assert result.average_romance == pytest.approx((0 + 90) / 2, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_centrality_ignores_non_character_relationships(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Centrality should only count character-to-character relationships."""
        # Character-to-character
        char_rel = Relationship.create_character_relationship(
            source_id="alice",
            target_id="bob",
            relationship_type=RelationshipType.ALLY,
        )
        await repository.save(char_rel)

        # Character-to-faction (should be ignored)
        faction_rel = Relationship.create_membership(
            member_id="alice",
            member_type=EntityType.CHARACTER,
            faction_id="guild-001",
        )
        await repository.save(faction_rel)

        result = await service.get_character_centrality("alice")

        # Only the character-to-character relationship should be counted
        assert result.relationship_count == 1


class TestRelationshipTypeClassification:
    """Tests for positive/negative relationship classification."""

    @pytest.mark.asyncio
    async def test_family_counted_as_positive(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """FAMILY relationships should be counted as positive."""
        rel = Relationship.create_character_relationship(
            source_id="parent",
            target_id="child",
            relationship_type=RelationshipType.FAMILY,
        )
        await repository.save(rel)

        result = await service.analyze_social_network()

        assert result.character_centralities["parent"].positive_count == 1

    @pytest.mark.asyncio
    async def test_mentor_counted_as_positive(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """MENTOR relationships should be counted as positive."""
        rel = Relationship.create_character_relationship(
            source_id="master",
            target_id="apprentice",
            relationship_type=RelationshipType.MENTOR,
        )
        await repository.save(rel)

        result = await service.analyze_social_network()

        assert result.character_centralities["master"].positive_count == 1

    @pytest.mark.asyncio
    async def test_rival_counted_as_negative(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """RIVAL relationships should be counted as negative."""
        rel = Relationship.create_character_relationship(
            source_id="athlete1",
            target_id="athlete2",
            relationship_type=RelationshipType.RIVAL,
        )
        await repository.save(rel)

        result = await service.analyze_social_network()

        assert result.character_centralities["athlete1"].negative_count == 1

    @pytest.mark.asyncio
    async def test_neutral_counted_as_neither(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """NEUTRAL relationships should not be positive or negative."""
        rel = Relationship.create_character_relationship(
            source_id="stranger1",
            target_id="stranger2",
            relationship_type=RelationshipType.NEUTRAL,
        )
        await repository.save(rel)

        result = await service.analyze_social_network()

        char = result.character_centralities["stranger1"]
        assert char.positive_count == 0
        assert char.negative_count == 0
        assert char.relationship_count == 1


class TestAverageMetrics:
    """Tests for average trust and romance calculations."""

    @pytest.mark.asyncio
    async def test_average_trust_across_multiple_relationships(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Average trust should be correctly calculated across all relationships."""
        # Create 3 relationships with trust: 60, 80, 100
        for i, trust in enumerate([60, 80, 100]):
            rel = Relationship.create_character_relationship(
                source_id="alice",
                target_id=f"friend-{i}",
                relationship_type=RelationshipType.ALLY,
            )
            rel.update_trust(trust)
            await repository.save(rel)

        result = await service.analyze_social_network()

        alice = result.character_centralities["alice"]
        # Alice has 3 relationships, average trust = (60+80+100)/3 = 80
        assert alice.average_trust == pytest.approx(80.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_average_romance_with_mixed_values(
        self,
        repository: InMemoryRelationshipRepository,
        service: SocialGraphService,
    ):
        """Average romance should handle mixed values correctly."""
        # Non-romantic relationship
        rel1 = Relationship.create_character_relationship(
            source_id="alice",
            target_id="friend",
            relationship_type=RelationshipType.ALLY,
        )
        rel1.update_romance(0)
        await repository.save(rel1)

        # Romantic relationship
        rel2 = Relationship.create_character_relationship(
            source_id="alice",
            target_id="partner",
            relationship_type=RelationshipType.ROMANTIC,
        )
        rel2.update_romance(90)
        await repository.save(rel2)

        result = await service.analyze_social_network()

        alice = result.character_centralities["alice"]
        # Average romance = (0 + 90) / 2 = 45
        assert alice.average_romance == pytest.approx(45.0, rel=0.01)


class TestDataclassIntegrity:
    """Tests for dataclass behavior and defaults."""

    def test_character_centrality_defaults(self):
        """CharacterCentrality should have sensible defaults."""
        centrality = CharacterCentrality(character_id="test")

        assert centrality.relationship_count == 0
        assert centrality.positive_count == 0
        assert centrality.negative_count == 0
        assert centrality.average_trust == 0.0
        assert centrality.average_romance == 0.0
        assert centrality.centrality_score == 0.0

    def test_social_analysis_result_defaults(self):
        """SocialAnalysisResult should have sensible defaults."""
        result = SocialAnalysisResult()

        assert result.character_centralities == {}
        assert result.most_connected is None
        assert result.most_hated is None
        assert result.most_loved is None
        assert result.total_relationships == 0
        assert result.total_characters == 0
        assert result.network_density == 0.0
