"""
IContextAssembler Port

Application port interface for assembling agent knowledge context.

Constitution Compliance:
- Article II (Hexagonal): Application port defining contract for context assembly
- Article V (SOLID): Interface Segregation Principle - focused interface
"""

from abc import ABC, abstractmethod
from typing import List

from ...domain.models.agent_context import AgentContext
from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.knowledge_entry import KnowledgeEntry


class IContextAssembler(ABC):
    """
    Port for assembling agent knowledge context.

    Defines interface for creating AgentContext aggregates from
    knowledge entries. Implementations provide the assembly logic
    for converting filtered knowledge entries into structured context.

    Constitution Compliance:
        - Article II (Hexagonal): Application port defining contract
        - Article V (SOLID): ISP - focused interface for context assembly only
    """

    @abstractmethod
    def assemble_context(
        self,
        agent: AgentIdentity,
        entries: List[KnowledgeEntry],
        turn_number: int | None = None,
    ) -> AgentContext:
        """
        Assemble knowledge entries into agent context.

        Args:
            agent: Agent identity (character_id and roles)
            entries: Knowledge entries (already filtered for access control)
            turn_number: Optional simulation turn number

        Returns:
            AgentContext aggregate with assembled knowledge

        Raises:
            ValueError: If agent is invalid or entries are inaccessible
        """
        pass
