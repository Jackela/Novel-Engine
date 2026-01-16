"""
SubjectiveBriefPhaseAdapter

Infrastructure adapter for integrating knowledge retrieval into SubjectiveBriefPhase.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article IV (SSOT): PostgreSQL as single source of truth (via use case)
- Article VII (Observability): OpenTelemetry tracing instrumentation
"""

from typing import List
from datetime import datetime, timezone

from opentelemetry import trace

from src.core.types.shared_types import CharacterId
from ...application.ports.i_context_assembler import IContextAssembler
from ...application.use_cases.retrieve_agent_context import RetrieveAgentContextUseCase
from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.agent_context import AgentContext
from ...domain.models.knowledge_entry import KnowledgeEntry

# Get tracer for knowledge context operations
tracer = trace.get_tracer(__name__)


class SubjectiveBriefPhaseAdapter(IContextAssembler):
    """
    Adapter for integrating knowledge retrieval into SubjectiveBriefPhase.

    Provides context assembly for agent simulation turns by retrieving
    knowledge from PostgreSQL instead of reading Markdown files.

    This adapter serves two purposes:
    1. Implements IContextAssembler for direct context assembly
    2. Provides get_agent_knowledge_context() for SubjectiveBriefPhase integration

    Constitution Compliance:
        - Article II (Hexagonal): Infrastructure adapter implementing port
        - Article IV (SSOT): PostgreSQL as single source of truth
        - Article VII (Observability): Metrics and tracing integration points
    """

    def __init__(self, retrieve_context_use_case: RetrieveAgentContextUseCase):
        """
        Initialize adapter with use case dependency.

        Args:
            retrieve_context_use_case: Use case for retrieving agent context

        Constitution Compliance:
            - Article V (SOLID): Dependency injection for testability
        """
        self._use_case = retrieve_context_use_case

    def assemble_context(
        self,
        agent: AgentIdentity,
        entries: List[KnowledgeEntry],
        turn_number: int | None = None,
    ) -> AgentContext:
        """
        Assemble knowledge entries into agent context.

        Implements IContextAssembler port for direct context assembly
        when entries are already retrieved.

        Args:
            agent: Agent identity
            entries: Knowledge entries (already filtered for access)
            turn_number: Optional simulation turn number

        Returns:
            AgentContext aggregate

        Constitution Compliance:
            - Article I (DDD): Creates domain aggregate
        """
        return AgentContext(
            agent=agent,
            knowledge_entries=entries,
            retrieved_at=datetime.now(timezone.utc),
            turn_number=turn_number,
        )

    async def get_agent_knowledge_context(
        self,
        character_id: CharacterId,
        roles: tuple[str, ...],
        turn_number: int,
    ) -> str:
        """
        Retrieve agent knowledge context for SubjectiveBriefPhase integration.

        This method is called by SubjectiveBriefPhase during simulation
        turns to get the agent's knowledge context as formatted text.

        Replaces Markdown file reads with PostgreSQL-backed knowledge retrieval.

        Args:
            character_id: Agent's character ID
            roles: Agent's roles
            turn_number: Current simulation turn number

        Returns:
            Formatted LLM prompt text with agent knowledge

        Performance Requirement:
            - SC-002: Must complete in <500ms for ≤100 entries

        Constitution Compliance:
            - Article IV (SSOT): PostgreSQL as single source of truth
            - Article VII (Observability): OpenTelemetry tracing instrumented
            - FR-006: Replaces Markdown file reads
        """
        # Create tracing span for knowledge retrieval operation (Article VII)
        with tracer.start_as_current_span(
            "knowledge.retrieve_agent_context",
            attributes={
                "agent.character_id": character_id,
                "agent.roles": ",".join(roles),
                "simulation.turn_number": turn_number,
                "operation": "subjective_brief_phase",
            },
        ) as span:
            try:
                # Construct agent identity
                agent = AgentIdentity(character_id=character_id, roles=roles)

                # Retrieve and assemble context via use case
                context = await self._use_case.execute(
                    agent=agent,
                    turn_number=turn_number,
                )

                # Add span attributes for observability
                span.set_attribute(
                    "knowledge.entries_retrieved", len(context.knowledge_entries)
                )
                span.set_attribute("knowledge.retrieval_source", "postgresql")
                span.set_attribute("success", True)

                # Return formatted LLM prompt text
                return context.to_llm_prompt_text()

            except Exception as e:
                # Record exception in span for debugging
                span.set_attribute("success", False)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise

