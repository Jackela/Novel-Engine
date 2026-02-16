"""
IAccessControlService Port Interface

Domain service port for access control operations.

Constitution Compliance:
- Article II (Hexagonal): Application layer defines port, Domain layer provides service
- Article I (DDD): Domain service interface for cross-aggregate access control logic
- Article V (SOLID): SRP - Single responsibility for access control decisions
"""

from abc import ABC, abstractmethod
from typing import List

from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.knowledge_entry import KnowledgeEntry


class IAccessControlService(ABC):
    """
    Domain service port for access control operations.

    This service coordinates access control logic that spans multiple domain entities.
    While individual KnowledgeEntry.is_accessible_by checks single-entry access,
    this service handles batch filtering and complex access scenarios.

    Design Pattern:
    - Domain Service: Encapsulates business logic that doesn't naturally fit
      within a single aggregate (KnowledgeEntry or AgentIdentity)
    - Port Interface: Application layer defines contract, Domain layer implements

    Use Cases:
    - Filter large collections of entries for agent access
    - Apply complex access rules across multiple entries
    - Coordinate access checks with performance optimization

    Per Article I (DDD):
    - Domain service for multi-aggregate access control logic
    - Pure business logic with no infrastructure dependencies

    Per Article V (SOLID):
    - SRP: Single responsibility for access control decisions
    - OCP: Can be extended with new access patterns without modification

    Methods:
        filter_accessible_entries: Filter a collection for agent access
        can_access_entry: Check if agent can access a specific entry

    Constitution Compliance:
    - Article I (DDD): Domain service interface
    - Article II (Hexagonal): Port in application/domain boundary
    - Article V (SOLID): SRP, OCP, DIP
    """

    @abstractmethod
    def filter_accessible_entries(
        self,
        entries: List[KnowledgeEntry],
        agent: AgentIdentity,
    ) -> List[KnowledgeEntry]:
        """
        Filter a collection of entries to only those accessible by the agent.

        This method applies access control rules to a batch of entries,
        which is more efficient than checking each entry individually
        when performance matters.

        Args:
            entries: Collection of knowledge entries to filter
            agent: Agent identity (character_id and roles)

        Returns:
            Filtered list containing only entries accessible to the agent

        Access Control Rules:
        - PUBLIC: Always included
        - ROLE_BASED: Included if agent has any matching role
        - CHARACTER_SPECIFIC: Included if agent's character_id in allowed list

        Example:
            >>> all_entries = [public_entry, engineer_entry, private_entry]
            >>> agent = AgentIdentity(character_id="char-001", roles=("engineer",))
            >>> accessible = service.filter_accessible_entries(all_entries, agent)
            >>> # Returns [public_entry, engineer_entry]

        Performance:
        - O(n) where n is number of entries
        - Should complete in <10ms for 100 entries

        Constitution Compliance:
        - Article I (DDD): Business logic in domain service
        - FR-005: Access control filtering enforced
        """

    @abstractmethod
    def can_access_entry(
        self,
        entry: KnowledgeEntry,
        agent: AgentIdentity,
    ) -> bool:
        """
        Check if agent can access a specific knowledge entry.

        This is a convenience method that delegates to the entry's
        is_accessible_by method. Provided here for service completeness
        and to allow future extension with additional access logic.

        Args:
            entry: Knowledge entry to check access for
            agent: Agent identity (character_id and roles)

        Returns:
            True if agent has access, False otherwise

        Example:
            >>> entry = KnowledgeEntry(...)
            >>> agent = AgentIdentity(character_id="char-001", roles=("engineer",))
            >>> has_access = service.can_access_entry(entry, agent)

        Implementation Note:
        - Current implementation should delegate to entry.is_accessible_by(agent)
        - Future: Could add audit logging, metrics, or complex rules here

        Constitution Compliance:
        - Article I (DDD): Delegates to aggregate root business logic
        - Article V (SOLID): OCP - Open for extension with additional rules
        """
