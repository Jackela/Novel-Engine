"""
IKnowledgeRepository Port Interface

Hexagonal architecture port defining the contract for knowledge entry persistence.

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article I (DDD): Pure interface with no infrastructure coupling
"""

from abc import ABC, abstractmethod
from typing import List

from src.shared_types import KnowledgeEntryId, CharacterId

from ...domain.models.knowledge_entry import KnowledgeEntry
from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.knowledge_type import KnowledgeType


class IKnowledgeRepository(ABC):
    """
    Repository port for knowledge entry persistence.

    This interface defines the contract that infrastructure adapters must implement
    for persisting and retrieving KnowledgeEntry aggregates.

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides PostgreSQL adapter implementation
    - Application use cases depend ONLY on this abstraction, never on concrete adapters

    Per Article IV (SSOT):
    - Implementation MUST use PostgreSQL as authoritative source
    - No Redis caching for MVP (future enhancement)

    Methods:
        save: Persist a knowledge entry (create or update)
        get_by_id: Retrieve a knowledge entry by its unique ID
        retrieve_for_agent: Retrieve all entries accessible to an agent
        delete: Remove a knowledge entry (soft or hard delete)

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle (focused contract)
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
    async def save(self, entry: KnowledgeEntry) -> None:
        """
        Persist a knowledge entry (insert new or update existing).

        Args:
            entry: KnowledgeEntry aggregate to persist

        Raises:
            RepositoryError: If persistence operation fails

        Constitution Compliance:
        - Article IV (SSOT): Must persist to PostgreSQL as authoritative source
        """
        pass

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
        pass

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

        Constitution Compliance:
        - Article IV (SSOT): Retrieve from PostgreSQL with proper indexes
        - Article I (DDD): Business logic (access control) applied via domain model
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: KnowledgeEntryId) -> None:
        """
        Delete a knowledge entry by its unique identifier.

        Deletion strategy:
        - Hard delete from knowledge_entries table
        - PostgreSQL CASCADE will handle knowledge_audit_log cleanup

        Args:
            entry_id: Unique identifier of the entry to delete

        Raises:
            RepositoryError: If entry not found or deletion fails

        Constitution Compliance:
        - Article IV (SSOT): Delete from PostgreSQL (CASCADE on audit log)
        """
        pass
