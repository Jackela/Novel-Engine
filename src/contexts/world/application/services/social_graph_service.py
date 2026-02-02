#!/usr/bin/env python3
"""Social Network Analysis Service.

This module provides graph analytics for the character relationship network,
calculating metrics like centrality to identify key characters in the narrative.

Why centrality matters: In narrative design, understanding which characters
are most connected helps writers identify protagonists, social hubs, and
potential dramatic focal points. A character with high centrality influences
more of the story's social dynamics.

Typical usage example:
    >>> from src.contexts.world.application.services import SocialGraphService
    >>> from src.contexts.world.infrastructure.persistence import InMemoryRelationshipRepository
    >>>
    >>> repo = InMemoryRelationshipRepository()
    >>> service = SocialGraphService(repo)
    >>> analysis = await service.analyze_social_network()
    >>> print(analysis.most_connected)  # Character with highest centrality
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.contexts.world.domain.entities.relationship import (
    EntityType,
    Relationship,
    RelationshipType,
)
from src.contexts.world.domain.repositories.relationship_repository import (
    IRelationshipRepository,
)


@dataclass
class CharacterCentrality:
    """Centrality metrics for a single character.

    Attributes:
        character_id: Unique identifier for the character.
        relationship_count: Total number of relationships (degree centrality).
        positive_count: Number of positive relationships (ally, family, romantic, mentor).
        negative_count: Number of negative relationships (enemy, rival).
        average_trust: Average trust level across all relationships.
        average_romance: Average romance level across all relationships.
        centrality_score: Normalized centrality score (0-100).
    """

    character_id: str
    relationship_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    average_trust: float = 0.0
    average_romance: float = 0.0
    centrality_score: float = 0.0


@dataclass
class SocialAnalysisResult:
    """Complete social network analysis result.

    Why include 'most_hated' and 'most_loved': These extremes are narratively
    interesting - the most hated character might be a villain or misunderstood
    antihero, while the most loved is often a beloved mentor or romantic interest.

    Attributes:
        character_centralities: Mapping of character_id to their centrality metrics.
        most_connected: Character ID with highest relationship count, or None.
        most_hated: Character ID with most negative relationships, or None.
        most_loved: Character ID with highest average trust/romance, or None.
        total_relationships: Total number of character-to-character relationships.
        total_characters: Number of unique characters in the social graph.
        network_density: Ratio of actual to possible relationships (0.0-1.0).
    """

    character_centralities: Dict[str, CharacterCentrality] = field(default_factory=dict)
    most_connected: Optional[str] = None
    most_hated: Optional[str] = None
    most_loved: Optional[str] = None
    total_relationships: int = 0
    total_characters: int = 0
    network_density: float = 0.0


class SocialGraphService:
    """Service for social network analysis on the relationship graph.

    Calculates centrality and other graph metrics to help writers understand
    the social dynamics of their character cast.

    Thread Safety:
        This service is stateless and thread-safe, assuming the underlying
        repository handles concurrency appropriately.
    """

    def __init__(self, relationship_repository: IRelationshipRepository) -> None:
        """Initialize the service with a relationship repository.

        Args:
            relationship_repository: Repository for accessing relationships.
        """
        self._repo = relationship_repository

    async def analyze_social_network(self) -> SocialAnalysisResult:
        """Perform complete social network analysis.

        Analyzes all character-to-character relationships to compute centrality
        metrics, identify key characters, and measure network properties.

        Why focus on CHARACTER-to-CHARACTER: Other relationship types
        (membership, location) are structural rather than social. Social
        network analysis is most meaningful for interpersonal dynamics.

        Returns:
            SocialAnalysisResult containing all computed metrics.
        """
        # Get all character-to-character relationships
        relationships = await self._repo.find_by_entity_types(
            source_type=EntityType.CHARACTER,
            target_type=EntityType.CHARACTER,
        )

        if not relationships:
            return SocialAnalysisResult()

        # Build character metrics
        character_metrics: Dict[str, CharacterCentrality] = {}
        character_trusts: Dict[str, List[int]] = {}
        character_romances: Dict[str, List[int]] = {}

        for rel in relationships:
            # Process source character
            self._update_character_metrics(
                character_metrics,
                character_trusts,
                character_romances,
                rel.source_id,
                rel,
            )
            # Process target character (relationships are counted for both parties)
            self._update_character_metrics(
                character_metrics,
                character_trusts,
                character_romances,
                rel.target_id,
                rel,
            )

        # Calculate averages and normalized scores
        max_relationships = max(
            (c.relationship_count for c in character_metrics.values()),
            default=0,
        )

        for char_id, metrics in character_metrics.items():
            # Calculate average trust
            trusts = character_trusts.get(char_id, [])
            if trusts:
                metrics.average_trust = sum(trusts) / len(trusts)

            # Calculate average romance
            romances = character_romances.get(char_id, [])
            if romances:
                metrics.average_romance = sum(romances) / len(romances)

            # Normalize centrality score (0-100 scale)
            if max_relationships > 0:
                metrics.centrality_score = (
                    metrics.relationship_count / max_relationships
                ) * 100

        # Find extremes
        most_connected = self._find_most_connected(character_metrics)
        most_hated = self._find_most_hated(character_metrics)
        most_loved = self._find_most_loved(character_metrics)

        # Calculate network density
        num_characters = len(character_metrics)
        total_relationships = len(relationships)
        # Maximum possible edges in undirected graph: n*(n-1)/2
        max_possible = (num_characters * (num_characters - 1)) / 2 if num_characters > 1 else 0
        density = total_relationships / max_possible if max_possible > 0 else 0.0

        return SocialAnalysisResult(
            character_centralities=character_metrics,
            most_connected=most_connected,
            most_hated=most_hated,
            most_loved=most_loved,
            total_relationships=total_relationships,
            total_characters=num_characters,
            network_density=min(density, 1.0),  # Cap at 1.0 for directed edge overcounting
        )

    async def get_character_centrality(self, character_id: str) -> Optional[CharacterCentrality]:
        """Get centrality metrics for a specific character.

        Args:
            character_id: ID of the character to analyze.

        Returns:
            CharacterCentrality metrics, or None if character has no relationships.
        """
        relationships = await self._repo.find_by_entity(
            entity_id=character_id,
            entity_type=EntityType.CHARACTER,
        )

        # Filter to only character-to-character relationships
        char_relationships = [
            r
            for r in relationships
            if r.source_type == EntityType.CHARACTER
            and r.target_type == EntityType.CHARACTER
        ]

        if not char_relationships:
            return None

        metrics = CharacterCentrality(character_id=character_id)
        trusts: List[int] = []
        romances: List[int] = []

        for rel in char_relationships:
            metrics.relationship_count += 1
            trusts.append(rel.trust)
            romances.append(rel.romance)

            if rel.is_positive():
                metrics.positive_count += 1
            elif rel.is_negative():
                metrics.negative_count += 1

        if trusts:
            metrics.average_trust = sum(trusts) / len(trusts)
        if romances:
            metrics.average_romance = sum(romances) / len(romances)

        # For single character, centrality_score is relative to their own count
        # Full network context needed for normalized score
        metrics.centrality_score = float(metrics.relationship_count)

        return metrics

    def _update_character_metrics(
        self,
        metrics: Dict[str, CharacterCentrality],
        trusts: Dict[str, List[int]],
        romances: Dict[str, List[int]],
        character_id: str,
        relationship: Relationship,
    ) -> None:
        """Update metrics for a character based on a relationship.

        Args:
            metrics: Dictionary of character metrics to update.
            trusts: Dictionary of trust values per character.
            romances: Dictionary of romance values per character.
            character_id: Character to update.
            relationship: The relationship to process.
        """
        if character_id not in metrics:
            metrics[character_id] = CharacterCentrality(character_id=character_id)
            trusts[character_id] = []
            romances[character_id] = []

        char_metrics = metrics[character_id]
        char_metrics.relationship_count += 1

        trusts[character_id].append(relationship.trust)
        romances[character_id].append(relationship.romance)

        if relationship.is_positive():
            char_metrics.positive_count += 1
        elif relationship.is_negative():
            char_metrics.negative_count += 1

    def _find_most_connected(
        self, metrics: Dict[str, CharacterCentrality]
    ) -> Optional[str]:
        """Find the character with the most relationships.

        Args:
            metrics: Character centrality metrics.

        Returns:
            Character ID with highest relationship_count, or None.
        """
        if not metrics:
            return None

        return max(metrics.keys(), key=lambda cid: metrics[cid].relationship_count)

    def _find_most_hated(
        self, metrics: Dict[str, CharacterCentrality]
    ) -> Optional[str]:
        """Find the character with the most negative relationships.

        Args:
            metrics: Character centrality metrics.

        Returns:
            Character ID with highest negative_count, or None if no negatives.
        """
        if not metrics:
            return None

        candidates = [
            (cid, m.negative_count)
            for cid, m in metrics.items()
            if m.negative_count > 0
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda x: x[1])[0]

    def _find_most_loved(
        self, metrics: Dict[str, CharacterCentrality]
    ) -> Optional[str]:
        """Find the character with highest combined trust/romance.

        Uses a weighted score: trust contributes 60%, romance 40%.
        This reflects that trust is more universal while romance is
        typically limited to specific relationships.

        Args:
            metrics: Character centrality metrics.

        Returns:
            Character ID with highest love score, or None.
        """
        if not metrics:
            return None

        def love_score(m: CharacterCentrality) -> float:
            return (m.average_trust * 0.6) + (m.average_romance * 0.4)

        return max(metrics.keys(), key=lambda cid: love_score(metrics[cid]))
