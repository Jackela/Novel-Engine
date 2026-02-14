"""
IKnowledgeRetriever Port Interface

Read-only query interface for knowledge retrieval.

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article V (SOLID): ISP - Separate read (IKnowledgeRetriever) from write (IKnowledgeRepository)
- Article I (DDD): Pure interface with no infrastructure coupling
"""

from abc import ABC, abstractmethod
from typing import List

from src.core.types.shared_types import CharacterId, KnowledgeEntryId

from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.knowledge_entry import KnowledgeEntry
from ...domain.models.knowledge_type import KnowledgeType


class IKnowledgeRetriever(ABC):
    """
    Read-only query port for knowledge retrieval.

    This interface provides read-only access to knowledge entries,
    separated from write operations per ISP (Interface Segregation Principle).

    Use Cases:
    - SubjectiveBriefPhase needs to retrieve knowledge but should not modify it
    - Agent context assembly needs read-only access
    - Query services that should not have write permissions

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides adapter implementation (PostgreSQL)
    - Use cases depend ONLY on this abstraction for read operations

    Per Article V (SOLID - ISP):
    - Clients that only need read access should not depend on write operations
    - Separates query concerns from command concerns (CQRS-lite)

    Methods:
        get_by_id: Retrieve a single knowledge entry by ID
        retrieve_for_agent: Retrieve all entries accessible to an agent

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
    async def get_by_id(self, entry_id: KnowledgeEntryId) -> KnowledgeEntry | None:
        """
        Retrieve a knowledge entry by its unique identifier.

        Args:
            entry_id: Unique identifier of the knowledge entry

        Returns:
            KnowledgeEntry if found, None otherwise

        Raises:
            RepositoryError: If retrieval operation fails

        Constitution Compliance:
        - Article IV (SSOT): Must retrieve from PostgreSQL (no cache layer for MVP)
        """

    @abstractmethod
    async def retrieve_for_agent(
        self,
        agent: AgentIdentity,
        knowledge_types: List[KnowledgeType] | None = None,
        owning_character_id: CharacterId | None = None,
    ) -> List[KnowledgeEntry]:
        """
        Retrieve all knowledge entries accessible to an agent.

        Applies access control filtering based on:
        - Agent's character ID
        - Agent's roles
        - Access level (PUBLIC, ROLE_BASED, CHARACTER_SPECIFIC)

        Args:
            agent: Agent identity (character_id and roles)
            knowledge_types: Optional filter by knowledge types (None = all types)
            owning_character_id: Optional filter by owning character (None = all owners)

        Returns:
            List of KnowledgeEntry aggregates accessible to the agent

        Raises:
            RepositoryError: If retrieval operation fails

        Performance Requirement:
        - SC-002: Must complete in <500ms for ≤100 entries

        Access Control:
        - PUBLIC: Always accessible to all agents
        - ROLE_BASED: Accessible if agent has any matching role
        - CHARACTER_SPECIFIC: Accessible if agent's character_id matches allowed list

        Example:
            >>> agent = AgentIdentity(character_id="char-001", roles=("engineer",))
            >>> entries = await retriever.retrieve_for_agent(
            ...     agent=agent,
            ...     knowledge_types=[KnowledgeType.LORE, KnowledgeType.RULES],
            ... )

        Constitution Compliance:
        - Article IV (SSOT): Retrieve from PostgreSQL with proper indexes
        - Article I (DDD): Access control logic delegated to domain models
        - FR-005: Access control filtering enforced
        - FR-009: Agents only retrieve permitted knowledge
        """

    @abstractmethod
    async def retrieve_for_agent_semantic(
        self,
        agent: AgentIdentity,
        semantic_query: str,
        top_k: int = 5,
        threshold: float = 0.0,
        knowledge_types: List[KnowledgeType] | None = None,
    ) -> List[KnowledgeEntry]:
        """
        Retrieve knowledge entries using semantic similarity search (User Story 4).

        Uses vector embeddings and cosine similarity to find entries semantically
        similar to the query, even without exact keyword matches.

        Args:
            agent: Agent identity (character_id and roles) for access control
            semantic_query: Natural language query for semantic search
            top_k: Maximum number of results to return (default: 5)
            threshold: Minimum similarity score (0.0-1.0, default: 0.0)
            knowledge_types: Optional filter by knowledge types (None = all types)

        Returns:
            List of KnowledgeEntry aggregates ordered by semantic relevance (highest first)

        Raises:
            ValueError: If semantic_query is empty
            RepositoryError: If retrieval operation fails

        Performance:
            - Uses HNSW index for fast approximate nearest neighbor search
            - Targets <500ms for ≤100 entries (same as standard retrieval)

        Access Control:
            - Same access control rules as retrieve_for_agent
            - PUBLIC: Always accessible
            - ROLE_BASED: Agent must have matching role
            - CHARACTER_SPECIFIC: Agent's character_id must match

        Example:
            >>> agent = AgentIdentity(character_id="char-001", roles=("engineer",))
            >>> entries = await retriever.retrieve_for_agent_semantic(
            ...     agent=agent,
            ...     semantic_query="quantum propulsion systems",
            ...     top_k=3,
            ...     threshold=0.7,
            ... )

        Constitution Compliance:
            - Article IV (SSOT): PostgreSQL pgvector as single source for embeddings
            - Article I (DDD): Access control logic delegated to domain models
            - FR-020: Semantic search with vector similarity
            - FR-021: Fallback available when embeddings not present
        """
