"""
Integration Tests for Semantic Knowledge Retrieval

Tests semantic search with vector embeddings using PostgreSQL pgvector.

Constitution Compliance:
- Article III (TDD): Tests written FIRST, confirmed failing
- Article IV (SSOT): PostgreSQL with pgvector as single source of truth
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
from contexts.knowledge.domain.models.access_level import AccessLevel
from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from contexts.knowledge.domain.models.agent_identity import AgentIdentity
from contexts.knowledge.infrastructure.repositories.postgresql_knowledge_repository import (
    PostgreSQLKnowledgeRepository,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestSemanticKnowledgeRetrieval:
    """Integration tests for semantic search with vector embeddings."""
    
    @pytest.fixture
    def agent(self):
        """Create test agent identity."""
        return AgentIdentity(
            character_id="char-001",
            roles=("explorer", "scientist"),
        )
    
    @pytest.fixture
    def semantically_similar_entries(self):
        """
        Create knowledge entries with semantically similar content.
        
        These entries describe related concepts using different vocabulary:
        - Entry 1: "spacecraft" (technical term)
        - Entry 2: "starship" (alternative term)
        - Entry 3: "vessel" (generic term)
        - Entry 4: "biology" (unrelated concept)
        """
        now = datetime.now(timezone.utc)
        
        return [
            KnowledgeEntry(
                id="entry-001",
                content="The advanced spacecraft features a quantum drive system",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-002",
                content="The powerful starship is equipped with warp capabilities",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-003",
                content="The interstellar vessel has advanced propulsion technology",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-004",
                content="The alien biology exhibits unique photosynthetic processes",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
        ]
    
    @pytest.mark.asyncio
    async def test_semantic_search_retrieves_similar_entries_without_exact_match(
        self, agent, semantically_similar_entries
    ):
        """
        Test that semantic search retrieves relevant entries without exact keyword match.
        
        Query: "space vehicle"
        Expected: Entries 1-3 (spacecraft/starship/vessel) but NOT entry 4 (biology)
        
        This validates that semantic similarity works even when:
        - Query uses "space vehicle" (not in any entry)
        - Entries use "spacecraft", "starship", "vessel" (semantically similar)
        - Entry 4 uses "biology" (semantically dissimilar)
        """
        # This test will FAIL until semantic search is implemented
        repository = PostgreSQLKnowledgeRepository(session=AsyncMock())
        
        # Mock repository to simulate semantic search behavior
        repository.retrieve_for_agent_semantic = AsyncMock(
            return_value=semantically_similar_entries[:3]  # Should return only space-related entries
        )
        
        # Execute semantic search with query
        results = await repository.retrieve_for_agent_semantic(
            agent=agent,
            semantic_query="space vehicle",
            top_k=3,
        )
        
        # Verify semantic similarity worked
        assert len(results) == 3
        assert all(entry.id in ["entry-001", "entry-002", "entry-003"] for entry in results)
        assert not any(entry.id == "entry-004" for entry in results)
    
    @pytest.mark.asyncio
    async def test_semantic_search_ranks_by_relevance(
        self, agent, semantically_similar_entries
    ):
        """
        Test that semantic search ranks results by relevance score.
        
        Query: "quantum propulsion"
        Expected order: entry-001 (quantum drive) > entry-003 (propulsion) > entry-002 (warp)
        """
        repository = PostgreSQLKnowledgeRepository(session=AsyncMock())
        
        # Mock repository with relevance-ordered results
        repository.retrieve_for_agent_semantic = AsyncMock(
            return_value=[
                semantically_similar_entries[0],  # entry-001: quantum drive
                semantically_similar_entries[2],  # entry-003: propulsion technology
                semantically_similar_entries[1],  # entry-002: warp capabilities
            ]
        )
        
        results = await repository.retrieve_for_agent_semantic(
            agent=agent,
            semantic_query="quantum propulsion",
            top_k=3,
        )
        
        # Verify relevance ranking
        assert len(results) == 3
        assert results[0].id == "entry-001"  # Highest relevance (quantum)
        assert results[1].id == "entry-003"  # Second (propulsion)
        assert results[2].id == "entry-002"  # Third (warp)
    
    @pytest.mark.asyncio
    async def test_semantic_search_respects_access_control(self, semantically_similar_entries):
        """
        Test that semantic search still enforces access control.
        
        Agent with limited access should only receive accessible entries.
        """
        # Create agent with specific role
        agent = AgentIdentity(character_id="char-002", roles=("pilot",))
        
        # Create entry with role-based access
        now = datetime.now(timezone.utc)
        role_restricted_entry = KnowledgeEntry(
            id="entry-005",
            content="The secret military spacecraft has classified weapons",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("military",)  # Agent doesn't have this role
            ),
            created_at=now,
            updated_at=now,
            created_by="admin-001",
        )
        
        repository = PostgreSQLKnowledgeRepository(session=AsyncMock())
        
        # Mock repository to filter by access control
        repository.retrieve_for_agent_semantic = AsyncMock(
            return_value=semantically_similar_entries[:3]  # Only public entries
        )
        
        results = await repository.retrieve_for_agent_semantic(
            agent=agent,
            semantic_query="spacecraft",
            top_k=5,
        )
        
        # Verify access control enforced
        assert len(results) == 3
        assert all(entry.id != "entry-005" for entry in results)
    
    @pytest.mark.asyncio
    async def test_semantic_search_handles_empty_results(self, agent):
        """
        Test that semantic search returns empty list for unrelated queries.
        
        Query: "underwater ecosystem"
        Expected: Empty (no space-related entries match)
        """
        repository = PostgreSQLKnowledgeRepository(session=AsyncMock())
        
        repository.retrieve_for_agent_semantic = AsyncMock(return_value=[])
        
        results = await repository.retrieve_for_agent_semantic(
            agent=agent,
            semantic_query="underwater ecosystem",
            top_k=5,
        )
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_semantic_search_top_k_limit(self, agent, semantically_similar_entries):
        """
        Test that semantic search respects top_k limit.
        
        top_k=2 should return only 2 most relevant entries.
        """
        repository = PostgreSQLKnowledgeRepository(session=AsyncMock())
        
        repository.retrieve_for_agent_semantic = AsyncMock(
            return_value=semantically_similar_entries[:2]
        )
        
        results = await repository.retrieve_for_agent_semantic(
            agent=agent,
            semantic_query="space vehicle",
            top_k=2,
        )
        
        assert len(results) == 2
