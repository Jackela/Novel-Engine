"""
RetrieveAgentContextUseCase

Application use case for retrieving and assembling agent knowledge context.

Constitution Compliance:
- Article I (DDD): Orchestrates domain operations
- Article II (Hexagonal): Depends on ports, not concrete adapters
- Article V (SOLID): Single Responsibility - context retrieval orchestration
- Article VII (Observability): Prometheus metrics instrumentation
"""

import time
from typing import List

from src.shared_types import CharacterId
from ..ports.i_knowledge_retriever import IKnowledgeRetriever
from ..ports.i_context_assembler import IContextAssembler
from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.agent_context import AgentContext
from ...domain.models.knowledge_type import KnowledgeType
from ...infrastructure.metrics_config import record_knowledge_retrieval


class RetrieveAgentContextUseCase:
    """
    Use case for retrieving agent knowledge context.
    
    Coordinates knowledge retrieval and context assembly for agents
    during simulation turns. Delegates to:
    - IKnowledgeRetriever: Fetch accessible knowledge entries from persistence
    - IContextAssembler: Assemble entries into structured AgentContext
    
    Constitution Compliance:
        - Article I (DDD): Orchestrates domain operations without business logic
        - Article II (Hexagonal): Depends on application ports (abstractions)
        - Article V (SOLID): SRP - context retrieval orchestration only
    """
    
    def __init__(
        self,
        knowledge_retriever: IKnowledgeRetriever,
        context_assembler: IContextAssembler,
    ):
        """
        Initialize use case with dependencies.
        
        Args:
            knowledge_retriever: Port for retrieving knowledge entries
            context_assembler: Port for assembling agent context
        
        Constitution Compliance:
            - Article V (SOLID): Dependency Inversion - depend on abstractions
        """
        self._retriever = knowledge_retriever
        self._assembler = context_assembler
    
    async def execute(
        self,
        agent: AgentIdentity,
        knowledge_types: List[KnowledgeType] | None = None,
        owning_character_id: CharacterId | None = None,
        turn_number: int | None = None,
        semantic_query: str | None = None,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> AgentContext:
        """
        Retrieve and assemble agent knowledge context.
        
        Supports two retrieval modes:
        1. Standard retrieval: Timestamp-ordered retrieval (default)
        2. Semantic retrieval: Vector similarity search (if semantic_query provided)
        
        Workflow:
        1. Retrieve accessible knowledge entries via IKnowledgeRetriever
           - If semantic_query provided: Use semantic search with vector embeddings
           - Otherwise: Use standard timestamp-ordered retrieval
        2. Assemble context aggregate via IContextAssembler
        3. Return assembled AgentContext
        
        Args:
            agent: Agent identity (character_id and roles)
            knowledge_types: Optional filter by knowledge types
            owning_character_id: Optional filter by owning character
            turn_number: Optional simulation turn number
            semantic_query: Optional natural language query for semantic search (US4)
            top_k: Maximum results for semantic search (default: 5, only used if semantic_query provided)
            threshold: Minimum similarity score for semantic search (0.0-1.0, default: 0.0)
        
        Returns:
            Assembled AgentContext aggregate with formatted knowledge
        
        Performance Requirement:
            - SC-002: Must complete in <500ms for ≤100 entries
        
        Constitution Compliance:
            - Article II (Hexagonal): Coordinates ports without infrastructure knowledge
            - Article V (SOLID): SRP - orchestration only, no business logic
            - Article VII (Observability): Prometheus metrics instrumented
        
        User Story 4 (Semantic Retrieval):
            - FR-020: Semantic search enabled when semantic_query is provided
            - FR-021: Fallback to standard retrieval when semantic_query is None
        """
        # Start timing for performance metrics (SC-002, Article VII)
        start_time = time.time()
        
        try:
            # Step 1: Retrieve accessible knowledge entries
            # (Access control filtering happens in retriever via domain logic)
            
            # Semantic retrieval mode with automatic fallback (US4 - T084)
            if semantic_query is not None:
                try:
                    # Attempt semantic search with vector embeddings
                    entries = await self._retriever.retrieve_for_agent_semantic(
                        agent=agent,
                        semantic_query=semantic_query,
                        top_k=top_k,
                        threshold=threshold,
                        knowledge_types=knowledge_types,
                    )
                    
                    # Fallback to standard retrieval if no semantic results
                    # (This happens when embeddings not yet generated for entries)
                    if not entries:
                        # No semantic results, fallback to standard retrieval
                        entries = await self._retriever.retrieve_for_agent(
                            agent=agent,
                            knowledge_types=knowledge_types,
                            owning_character_id=owning_character_id,
                        )
                
                except (ValueError, AttributeError) as e:
                    # Fallback if semantic search fails (e.g., embedding service unavailable)
                    # ValueError: Empty query
                    # AttributeError: retrieve_for_agent_semantic not implemented
                    entries = await self._retriever.retrieve_for_agent(
                        agent=agent,
                        knowledge_types=knowledge_types,
                        owning_character_id=owning_character_id,
                    )
            else:
                # Standard retrieval mode (timestamp-ordered)
                entries = await self._retriever.retrieve_for_agent(
                    agent=agent,
                    knowledge_types=knowledge_types,
                    owning_character_id=owning_character_id,
                )
            
            # Step 2: Assemble context aggregate
            # (Context formatting happens in domain aggregate)
            context = self._assembler.assemble_context(
                agent=agent,
                entries=entries,
                turn_number=turn_number,
            )
            
            # Step 3: Record metrics (Article VII - Observability)
            duration_seconds = time.time() - start_time
            record_knowledge_retrieval(
                agent_character_id=agent.character_id,
                turn_number=turn_number if turn_number is not None else 0,
                entry_count=len(entries),
                duration_seconds=duration_seconds,
            )
            
            return context
        
        except Exception:
            # Record metrics even on failure for observability
            duration_seconds = time.time() - start_time
            record_knowledge_retrieval(
                agent_character_id=agent.character_id,
                turn_number=turn_number if turn_number is not None else 0,
                entry_count=0,
                duration_seconds=duration_seconds,
            )
            raise
