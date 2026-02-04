"""
Graph Retrieval Service

Combines vector search with knowledge graph traversal for enhanced context retrieval.
For each retrieved chunk, fetches related entities and their relationships to provide
richer context for LLM generation.

Constitution Compliance:
- Article II (Hexagonal): Application service coordinating domain and infrastructure
- Article V (SOLID): SRP - graph-enhanced retrieval coordination

Warzone 4: AI Brain - BRAIN-032A, BRAIN-032B
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from datetime import datetime

import structlog

from ...application.ports.i_graph_store import (
    CentralityResult,
    CliqueResult,
    GraphEntity,
    GraphExportResult,
    GraphNeighbor,
    GraphRelationship,
    GraphStats,
    IGraphStore,
    PathResult,
)
from ..services.knowledge_ingestion_service import RetrievedChunk

if TYPE_CHECKING:
    pass


logger = structlog.get_logger()


# Cache TTL for graph queries (5 minutes)
GRAPH_CACHE_TTL = 300


@dataclass(frozen=True, slots=True)
class GraphExplanationStep:
    """
    A single step in the graph traversal reasoning path.

    Attributes:
        step_number: Order of this step in the reasoning chain
        step_type: Type of operation (entity_lookup, relationship_traversal, path_finding, etc.)
        description: Human-readable description of what was done
        entity_name: Primary entity involved in this step
        related_entities: Other entities discovered in this step
        relationships_traversed: Relationships that were followed
        relevance_score: Why this step was relevant (0-1)
        metadata: Additional context about this step
    """

    step_number: int
    step_type: str
    description: str
    entity_name: str
    related_entities: tuple[str, ...] = ()
    relationships_traversed: tuple[str, ...] = ()
    relevance_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphExplanation:
    """
    Complete explanation of graph traversal reasoning path.

    Provides visibility into why certain entities and relationships were included
    in the retrieval result, enabling debugging and transparency.

    Attributes:
        query: The original query or chunk content that triggered traversal
        steps: Ordered sequence of reasoning steps
        entities_examined: Total entities looked up during traversal
        relationships_examined: Total relationships examined
        total_traversal_depth: Maximum depth reached during traversal
        timestamp: When the explanation was generated
        summary_text: Human-readable summary of the reasoning path
    """

    query: str
    steps: tuple[GraphExplanationStep, ...]
    entities_examined: int
    relationships_examined: int
    total_traversal_depth: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    summary_text: str = ""


@dataclass(frozen=True, slots=True)
class GraphEntityContext:
    """
    Enhanced context for an entity including relationships and connected entities.

    Attributes:
        entity: The graph entity
        relationships: All relationships for this entity
        connected_entities: Entities directly connected to this entity
        degree: Number of direct connections
        metadata: Additional metadata
    """

    entity: GraphEntity
    relationships: tuple[GraphRelationship, ...]
    connected_entities: tuple[GraphEntity, ...]
    degree: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphEnhancedChunk:
    """
    A retrieved chunk enhanced with graph context.

    Attributes:
        original_chunk: The original retrieved chunk from vector store
        entity_contexts: Entities mentioned in or related to this chunk
        relationship_count: Total number of relationships found
        entity_descriptions: Combined entity descriptions
    """

    original_chunk: RetrievedChunk
    entity_contexts: tuple[GraphEntityContext, ...]
    relationship_count: int
    entity_descriptions: str


@dataclass(frozen=True, slots=True)
class GraphRetrievalConfig:
    """
    Configuration for graph retrieval behavior.

    Attributes:
        entity_expansion_depth: How many hops to explore for entities (default: 1)
        max_entities_per_chunk: Maximum entities to fetch per chunk (default: 5)
        include_relationship_types: Filter for specific relationship types
        include_entity_types: Filter for specific entity types
        min_relevance: Minimum relevance score for including entities
        cache_enabled: Enable LRU caching of graph queries (default: True)
        explain_mode: Enable reasoning path tracking for debugging (default: False)
    """

    entity_expansion_depth: int = 1
    max_entities_per_chunk: int = 5
    include_relationship_types: tuple[str, ...] = ()
    include_entity_types: tuple[str, ...] = ()
    min_relevance: float = 0.3
    cache_enabled: bool = True
    explain_mode: bool = False


@dataclass
class GraphRetrievalResult:
    """
    Result of a graph-enhanced retrieval operation.

    Attributes:
        enhanced_chunks: Chunks with graph context added
        entities_found: Total unique entities discovered
        relationships_found: Total unique relationships discovered
        cache_hits: Number of cache hits during retrieval
        cache_misses: Number of cache misses during retrieval
        explanation: Optional explanation of reasoning path (when explain_mode=True)
    """

    enhanced_chunks: list[GraphEnhancedChunk]
    entities_found: int
    relationships_found: int
    cache_hits: int = 0
    cache_misses: int = 0
    explanation: GraphExplanation | None = None


class GraphRetrievalService:
    """
    Service for combining vector retrieval with knowledge graph traversal.

    Why separate service:
        - Separates concerns between vector search and graph traversal
        - Allows independent testing and optimization
        - Can be used standalone or in combination with RetrievalService

    Usage:
        service = GraphRetrievalService(graph_store)
        result = await service.enrich_chunks_with_graph(chunks)

    Warzone 4: AI Brain - BRAIN-032A
    """

    def __init__(
        self,
        graph_store: IGraphStore,
        config: GraphRetrievalConfig | None = None,
    ) -> None:
        """
        Initialize the graph retrieval service.

        Args:
            graph_store: Graph store implementation (NetworkX or Neo4j)
            config: Optional configuration for retrieval behavior
        """
        self._graph_store = graph_store
        self._config = config or GraphRetrievalConfig()
        self._cache_hits = 0
        self._cache_misses = 0

    async def enrich_chunks_with_graph(
        self,
        chunks: list[RetrievedChunk],
    ) -> GraphRetrievalResult:
        """
        Enrich retrieved chunks with graph context.

        For each chunk:
        1. Extract entity names from chunk content
        2. Fetch related entities from graph
        3. Get relationships between entities
        4. Build enhanced chunk with graph context

        When explain_mode is enabled, tracks the reasoning path through the graph.

        Args:
            chunks: Retrieved chunks from vector store

        Returns:
            GraphRetrievalResult with enhanced chunks, statistics, and optional explanation
        """
        enhanced_chunks: list[GraphEnhancedChunk] = []
        all_entities: dict[str, GraphEntity] = {}
        all_relationships: set[tuple[str, str, str]] = set()

        # Explanation tracking
        explanation_steps: list[GraphExplanationStep] = []
        step_counter = 0
        max_depth_reached = 0
        relationships_examined = 0

        for chunk in chunks:
            # Extract potential entity names from chunk content
            entity_names = await self._extract_entity_names(chunk.content)

            if self._config.explain_mode:
                step_counter += 1
                explanation_steps.append(
                    GraphExplanationStep(
                        step_number=step_counter,
                        step_type="entity_extraction",
                        description=f"Extracted {len(entity_names)} potential entity names from chunk",
                        entity_name=chunk.chunk_id,
                        related_entities=tuple(entity_names),
                        relevance_score=1.0,
                        metadata={"chunk_content_preview": chunk.content[:100]}),
                )

            # Fetch graph context for each entity
            entity_contexts: list[GraphEntityContext] = []

            for entity_name in entity_names[:self._config.max_entities_per_chunk]:
                # Get entity from graph
                entity = await self._get_entity_cached(entity_name)
                if entity is None:
                    if self._config.explain_mode:
                        step_counter += 1
                        explanation_steps.append(
                            GraphExplanationStep(
                                step_number=step_counter,
                                step_type="entity_lookup",
                                description=f"Entity '{entity_name}' not found in graph",
                                entity_name=entity_name,
                                relevance_score=0.0,
                                metadata={"found": False}),
                        )
                    continue

                all_entities[entity.name] = entity

                if self._config.explain_mode:
                    step_counter += 1
                    explanation_steps.append(
                        GraphExplanationStep(
                            step_number=step_counter,
                            step_type="entity_lookup",
                            description=f"Found entity '{entity_name}' in graph (type: {entity.entity_type.value})",
                            entity_name=entity_name,
                            relevance_score=1.0,
                            metadata={"found": True, "entity_type": entity.entity_type.value}),
                    )

                # Get neighbors (connected entities)
                neighbors = await self._get_neighbors_cached(
                    entity_name,
                    max_depth=self._config.entity_expansion_depth,
                )

                # Get relationships for this entity
                relationships = await self._get_relationships_cached(entity_name)
                relationships_examined += len(relationships)

                if self._config.explain_mode and neighbors:
                    step_counter += 1
                    neighbor_names = tuple(n.entity.name for n in neighbors)
                    rel_types = tuple(str(n.relationship.relationship_type) for n in neighbors)
                    max_depth_reached = max(max_depth_reached, self._config.entity_expansion_depth)

                    explanation_steps.append(
                        GraphExplanationStep(
                            step_number=step_counter,
                            step_type="relationship_traversal",
                            description=f"Traversed {len(neighbors)} relationships from '{entity_name}'",
                            entity_name=entity_name,
                            related_entities=neighbor_names,
                            relationships_traversed=rel_types,
                            relevance_score=sum(n.relationship.strength or 1.0 for n in neighbors) / len(neighbors),
                            metadata={
                                "depth": self._config.entity_expansion_depth,
                                "neighbor_count": len(neighbors),
                            }),
                    )

                # Build connected entities list
                connected_entities: list[GraphEntity] = []
                for neighbor in neighbors:
                    if neighbor.entity.name not in all_entities:
                        all_entities[neighbor.entity.name] = neighbor.entity
                    connected_entities.append(neighbor.entity)

                    # Track unique relationships
                    all_relationships.add((
                        entity_name,
                        neighbor.entity.name,
                        str(neighbor.relationship.relationship_type),
                    ))

                entity_contexts.append(
                    GraphEntityContext(
                        entity=entity,
                        relationships=tuple(relationships),
                        connected_entities=tuple(connected_entities),
                        degree=len(connected_entities),
                    )
                )

            # Build entity descriptions
            entity_descriptions = self._build_entity_descriptions(tuple(entity_contexts))

            # Create enhanced chunk
            enhanced_chunks.append(
                GraphEnhancedChunk(
                    original_chunk=chunk,
                    entity_contexts=tuple(entity_contexts),
                    relationship_count=sum(len(ec.relationships) for ec in entity_contexts),
                    entity_descriptions=entity_descriptions,
                )
            )

        # Build explanation if enabled
        explanation: GraphExplanation | None = None
        if self._config.explain_mode:
            summary = self._build_explanation_summary(explanation_steps, len(all_entities), len(all_relationships))
            explanation = GraphExplanation(
                query=f"enriched_{len(chunks)}_chunks",
                steps=tuple(explanation_steps),
                entities_examined=len(all_entities),
                relationships_examined=relationships_examined,
                total_traversal_depth=max_depth_reached,
                summary_text=summary,
            )

        return GraphRetrievalResult(
            enhanced_chunks=enhanced_chunks,
            entities_found=len(all_entities),
            relationships_found=len(all_relationships),
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
            explanation=explanation,
        )

    async def get_entity_context(
        self,
        entity_name: str,
        max_depth: int = 1,
    ) -> GraphEntityContext | None:
        """
        Get complete graph context for a single entity.

        Args:
            entity_name: Name of the entity
            max_depth: How many hops to explore (default: 1)

        Returns:
            GraphEntityContext if entity found, None otherwise
        """
        # Get entity from graph
        entity = await self._get_entity_cached(entity_name)
        if entity is None:
            return None

        # Get neighbors
        neighbors = await self._get_neighbors_cached(entity_name, max_depth=max_depth)

        # Get relationships
        relationships = await self._get_relationships_cached(entity_name)

        # Build connected entities list
        connected_entities: list[GraphEntity] = []
        for neighbor in neighbors:
            connected_entities.append(neighbor.entity)

        return GraphEntityContext(
            entity=entity,
            relationships=tuple(relationships),
            connected_entities=tuple(connected_entities),
            degree=len(connected_entities),
        )

    async def find_related_entities(
        self,
        entity_name: str,
        relationship_type: str | None = None,
        max_depth: int = 2,
        limit: int | None = None,
    ) -> list[GraphEntity]:
        """
        Find entities related to the given entity via graph traversal.

        Args:
            entity_name: Starting entity name
            relationship_type: Optional filter by relationship type
            max_depth: Maximum traversal depth
            limit: Maximum number of entities to return

        Returns:
            List of related entities sorted by relevance
        """
        # Get neighbors at each depth level
        visited: set[str] = set()
        results: list[tuple[GraphEntity, int]] = []  # (entity, depth)

        # Use BFS to find related entities
        from collections import deque

        queue = deque([(entity_name, 0)])  # (entity_name, depth)

        while queue and (limit is None or len(results) < limit):
            current_name, depth = queue.popleft()

            if current_name in visited or depth > max_depth:
                continue

            visited.add(current_name)

            # Get neighbors
            neighbors = await self._get_neighbors_cached(current_name, max_depth=1)

            for neighbor in neighbors:
                neighbor_name = neighbor.entity.name

                if neighbor_name not in visited:
                    # Apply relationship type filter
                    if relationship_type is None or str(neighbor.relationship.relationship_type) == relationship_type:
                        results.append((neighbor.entity, depth + 1))
                        queue.append((neighbor_name, depth + 1))

        # Sort by depth then by connection strength
        results.sort(key=lambda x: (x[1], -x[0].metadata.get("strength", 1.0)))

        return [entity for entity, _ in results]

    async def get_entity_centrality(
        self,
        entity_name: str,
    ) -> CentralityResult | None:
        """
        Get centrality metrics for a specific entity.

        Args:
            entity_name: Name of the entity

        Returns:
            CentralityResult if entity found, None otherwise
        """
        results = await self._graph_store.get_centrality(entity_name=entity_name)
        return results[0] if results else None

    async def find_shortest_path(
        self,
        source: str,
        target: str,
    ) -> PathResult | None:
        """
        Find shortest path between two entities.

        Args:
            source: Source entity name
            target: Target entity name

        Returns:
            PathResult if path found, None otherwise
        """
        return await self._graph_store.find_path(source, target)

    async def get_graph_stats(self) -> GraphStats:
        """
        Get statistics about the knowledge graph.

        Returns:
            GraphStats with node/edge counts and type breakdowns
        """
        return await self._graph_store.get_stats()

    async def export_graph(
        self,
        format: str = "json",
        output_path: str | None = None,
    ) -> GraphExportResult:
        """
        Export the knowledge graph to file or string.

        Args:
            format: Export format ("json" or "graphml")
            output_path: Optional file path (if None, returns data in result.data)

        Returns:
            GraphExportResult with export statistics
        """
        if format == "json":
            return await self._graph_store.export_json(output_path)
        elif format == "graphml":
            if output_path is None:
                raise ValueError("output_path is required for GraphML export")
            return await self._graph_store.export_graphml(output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _build_entity_descriptions(
        self,
        entity_contexts: tuple[GraphEntityContext, ...],
    ) -> str:
        """
        Build a textual description of entities and their relationships.

        Args:
            entity_contexts: Entity contexts to describe

        Returns:
            Formatted text description
        """
        if not entity_contexts:
            return ""

        descriptions: list[str] = []

        for ctx in entity_contexts:
            entity = ctx.entity
            descriptions.append(f"- **{entity.name}** ({entity.entity_type.value})")
            if entity.description:
                descriptions.append(f"  {entity.description}")
            if entity.aliases:
                descriptions.append(f"  Aliases: {', '.join(entity.aliases)}")

            # Add relationships
            if ctx.relationships:
                rel_parts: list[str] = []
                for rel in ctx.relationships[:5]:  # Limit to 5 relationships
                    rel_parts.append(f"{rel.relationship_type.value} {rel.target}")
                if rel_parts:
                    descriptions.append(f"  Relationships: {', '.join(rel_parts)}")

        return "\n".join(descriptions)

    def _build_explanation_summary(
        self,
        steps: list[GraphExplanationStep],
        entities_found: int,
        relationships_found: int,
    ) -> str:
        """
        Build a human-readable summary of the graph traversal reasoning path.

        Args:
            steps: All explanation steps recorded during traversal
            entities_found: Total number of unique entities discovered
            relationships_found: Total number of unique relationships found

        Returns:
            Formatted summary text describing the reasoning path
        """
        if not steps:
            return "No graph traversal steps recorded."

        lines: list[str] = [
            "Graph Traversal Explanation",
            "=" * 40,
        ]

        # Count step types
        step_counts: dict[str, int] = {}
        for step in steps:
            step_counts[step.step_type] = step_counts.get(step.step_type, 0) + 1

        lines.append(f"Total Steps: {len(steps)}")
        lines.append(f"Entities Found: {entities_found}")
        lines.append(f"Relationships Found: {relationships_found}")
        lines.append(f"Traversal Depth: {max(s.metadata.get('depth', 0) for s in steps)}")
        lines.append("")

        # Summary by step type
        lines.append("Steps by Type:")
        for step_type, count in sorted(step_counts.items()):
            lines.append(f"  - {step_type}: {count}")

        lines.append("")

        # Entities examined
        entities_seen = set()
        for step in steps:
            if step.step_type == "entity_lookup" and step.metadata.get("found"):
                entities_seen.add(step.entity_name)

        if entities_seen:
            lines.append("Entities Examined:")
            for entity in sorted(entities_seen):
                lines.append(f"  - {entity}")

        return "\n".join(lines)

    async def _extract_entity_names(self, text: str) -> list[str]:
        """
        Extract potential entity names from text.

        This is a simple heuristic-based implementation. For production,
        consider using EntityExtractionService.

        Args:
            text: Text to extract entities from

        Returns:
            List of potential entity names
        """
        # Simple heuristic: capitalized words that might be names
        # In production, would use EntityExtractionService here
        import re

        # Look for patterns like "Alice", "the Dark Lord", etc.
        # This is a basic implementation
        words = text.split()

        potential_names: set[str] = set()

        # Find words starting with capital letter (likely proper nouns)
        for word in words:
            # Strip punctuation
            word = word.strip('.,!?;:"()[]{}')

            # Capitalized word (might be an entity name)
            if word and word[0].isupper() and len(word) > 1:
                potential_names.add(word)

        # Find quoted names (e.g., "The Dark Lord")
        quoted_pattern = re.compile(r'"([^"]+)"')
        for match in quoted_pattern.finditer(text):
            potential_names.add(match.group(1))

        # Find title case names (consecutive capitalized words)
        title_pattern = re.compile(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b')
        for match in title_pattern.finditer(text):
            potential_names.add(match.group(0))

        return list(potential_names)

    async def _get_entity_cached(self, name: str) -> GraphEntity | None:
        """Get entity with caching."""
        if self._config.cache_enabled:
            # Simple in-memory cache (for production, use proper caching)
            # For now, bypass cache for simplicity
            self._cache_misses += 1
        return await self._graph_store.get_entity(name)

    async def _get_neighbors_cached(
        self,
        entity_name: str,
        max_depth: int = 1,
    ) -> list[GraphNeighbor]:
        """Get neighbors with caching."""
        if self._config.cache_enabled:
            self._cache_misses += 1

        return await self._graph_store.get_neighbors(entity_name, max_depth=max_depth)

    async def _get_relationships_cached(self, entity_name: str) -> list[GraphRelationship]:
        """Get relationships with caching."""
        if self._config.cache_enabled:
            self._cache_misses += 1

        return await self._graph_store.get_relationships(entity_name)

    async def find_cliques(
        self,
        min_size: int = 3,
        entity_type: Any = None,
    ) -> CliqueResult:
        """
        Find cliques in the knowledge graph.

        Cliques are groups of entities where everyone is connected to everyone else.
        Useful for finding tight-knit groups (e.g., factions, families).

        Args:
            min_size: Minimum clique size (default: 3)
            entity_type: Optional entity type filter

        Returns:
            CliqueResult with all cliques found
        """
        return await self._graph_store.find_cliques(
            min_size=min_size,
            entity_type=entity_type,
        )

    def reset_cache_stats(self) -> None:
        """Reset cache hit/miss counters."""
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cache_stats(self) -> dict[str, float]:
        """Get cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "hits": float(self._cache_hits),
            "misses": float(self._cache_misses),
            "total": float(total),
            "hit_rate": hit_rate,
        }


__all__ = [
    "GraphEntityContext",
    "GraphEnhancedChunk",
    "GraphRetrievalConfig",
    "GraphRetrievalResult",
    "GraphRetrievalService",
    "GraphExplanationStep",
    "GraphExplanation",
]
