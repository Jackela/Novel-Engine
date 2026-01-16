"""
AccessControlService Domain Service

Implements cross-aggregate access control logic for knowledge entries.

Constitution Compliance:
- Article I (DDD): Domain service for business logic spanning multiple aggregates
- Article V (SOLID): SRP - Single responsibility for access control coordination
"""

from typing import List

from ..models.knowledge_entry import KnowledgeEntry
from ..models.agent_identity import AgentIdentity


class AccessControlService:
    """
    Domain service for coordinating access control across knowledge entries.

    This service implements the IAccessControlService port interface,
    providing business logic for filtering and checking access permissions.

    Design Rationale:
    - While KnowledgeEntry.is_accessible_by handles single-entry checks,
      this service coordinates batch operations and future complex scenarios
    - Domain service pattern: Business logic that doesn't fit in a single aggregate
    - Pure domain logic with no infrastructure dependencies

    Use Cases:
    - Filter large collections of entries efficiently
    - Coordinate access checks across multiple entries
    - Centralize access control logic for consistency

    Constitution Compliance:
    - Article I (DDD): Pure domain service with business logic
    - Article V (SOLID): SRP, OCP (extensible for new access patterns)
    """

    def filter_accessible_entries(
        self,
        entries: List[KnowledgeEntry],
        agent: AgentIdentity,
    ) -> List[KnowledgeEntry]:
        """
        Filter entries to only those accessible by the agent.

        Applies access control rules by delegating to each entry's
        is_accessible_by method. This provides a centralized point
        for batch filtering while preserving domain logic in aggregates.

        Args:
            entries: Collection of knowledge entries to filter
            agent: Agent identity (character_id and roles)

        Returns:
            Filtered list of entries the agent can access

        Access Control Rules (delegated to KnowledgeEntry.is_accessible_by):
        - PUBLIC: Always accessible
        - ROLE_BASED: Accessible if agent has matching role
        - CHARACTER_SPECIFIC: Accessible if agent's character_id in allowed list

        Performance:
        - O(n) complexity where n = number of entries
        - Each entry check is O(1) average case
        - Should complete in <10ms for 100 entries

        Example:
            >>> service = AccessControlService()
            >>> all_entries = [public_entry, engineer_entry, private_entry]
            >>> agent = AgentIdentity(character_id="char-001", roles=("engineer",))
            >>>
            >>> accessible = service.filter_accessible_entries(all_entries, agent)
            >>> # Returns [public_entry, engineer_entry]
            >>> len(accessible)  # 2

        Constitution Compliance:
        - Article I (DDD): Domain logic coordinating aggregates
        - FR-005: Access control filtering enforced
        - FR-009: Agents only receive permitted knowledge
        """
        return [entry for entry in entries if entry.is_accessible_by(agent)]

    def can_access_entry(
        self,
        entry: KnowledgeEntry,
        agent: AgentIdentity,
    ) -> bool:
        """
        Check if agent can access a specific entry.

        Delegates to the entry's is_accessible_by method.
        Provided as a service method for API consistency and
        to allow future extension with audit logging or metrics.

        Args:
            entry: Knowledge entry to check
            agent: Agent identity

        Returns:
            True if agent has access, False otherwise

        Example:
            >>> service = AccessControlService()
            >>> entry = KnowledgeEntry(
            ...     access_control=AccessControlRule(
            ...         access_level=AccessLevel.ROLE_BASED,
            ...         allowed_roles=("engineer",)
            ...     ),
            ...     ...
            ... )
            >>> agent = AgentIdentity(character_id="char-001", roles=("engineer",))
            >>>
            >>> service.can_access_entry(entry, agent)  # True

        Future Extensions:
        - Add audit logging for access checks
        - Instrument Prometheus metrics (access_check_total)
        - Support dynamic access rules

        Constitution Compliance:
        - Article I (DDD): Delegates to aggregate root
        - Article V (SOLID): OCP - Open for extension
        """
        return entry.is_accessible_by(agent)
