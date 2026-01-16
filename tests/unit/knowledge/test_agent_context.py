"""
Unit tests for AgentContext aggregate.

Tests the AgentContext domain aggregate and its to_llm_prompt_text method
for formatting knowledge entries into LLM prompts.

Constitution Compliance:
- Article III (TDD): Tests written FIRST, ensuring they FAIL before implementation
"""

from datetime import datetime, timezone

import pytest

from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.agent_context import AgentContext
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
from src.contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType


class TestAgentContext:
    """Test suite for AgentContext aggregate."""

    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent identity."""
        return AgentIdentity(
            character_id="char-001",
            roles=("player", "engineer"),
        )

    @pytest.fixture
    def sample_entries(self):
        """Create sample knowledge entries for testing."""
        now = datetime.now(timezone.utc)

        return [
            KnowledgeEntry(
                id="entry-001",
                content="You are a skilled engineer with expertise in robotics.",
                knowledge_type=KnowledgeType.PROFILE,
                owning_character_id="char-001",
                access_control=AccessControlRule(
                    access_level=AccessLevel.PUBLIC,
                ),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-002",
                content="Your primary objective is to repair the station's life support system.",
                knowledge_type=KnowledgeType.OBJECTIVE,
                owning_character_id="char-001",
                access_control=AccessControlRule(
                    access_level=AccessLevel.CHARACTER_SPECIFIC,
                    allowed_character_ids=("char-001",),
                ),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-003",
                content="The station is located in the Andromeda sector.",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(
                    access_level=AccessLevel.PUBLIC,
                ),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
        ]

    @pytest.mark.unit
    def test_to_llm_prompt_text_formats_knowledge_entries_correctly(
        self, sample_agent, sample_entries
    ):
        """Test that to_llm_prompt_text formats entries with proper structure."""
        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
            turn_number=1,
        )

        prompt = context.to_llm_prompt_text()

        # Should include agent identity
        assert "Agent: char-001" in prompt
        assert "Roles: player, engineer" in prompt

        # Should include knowledge context header
        assert "# Knowledge Context" in prompt

        # Should include all entry contents
        assert "skilled engineer with expertise in robotics" in prompt
        assert "repair the station's life support system" in prompt
        assert "Andromeda sector" in prompt

    @pytest.mark.unit
    def test_to_llm_prompt_text_groups_by_knowledge_type(
        self, sample_agent, sample_entries
    ):
        """Test that entries are grouped by knowledge type."""
        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
        )

        prompt = context.to_llm_prompt_text()

        # Should have type headers
        assert "## Profile" in prompt
        assert "## Objective" in prompt
        assert "## Lore" in prompt

        # Profile should come before Objective, Objective before Lore
        profile_index = prompt.index("## Profile")
        objective_index = prompt.index("## Objective")
        lore_index = prompt.index("## Lore")

        assert profile_index < objective_index < lore_index

    @pytest.mark.unit
    def test_to_llm_prompt_text_empty_context_returns_minimal_prompt(
        self, sample_agent
    ):
        """Test that empty context returns minimal prompt with agent info."""
        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=[],
            retrieved_at=datetime.now(timezone.utc),
        )

        prompt = context.to_llm_prompt_text()

        # Should still include agent identity
        assert "Agent: char-001" in prompt
        assert "No knowledge available" in prompt

    @pytest.mark.unit
    def test_to_llm_prompt_text_includes_agent_identity(
        self, sample_agent, sample_entries
    ):
        """Test that agent identity is included in prompt."""
        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
        )

        prompt = context.to_llm_prompt_text()

        # Should include character ID
        assert sample_agent.character_id in prompt

        # Should include roles
        for role in sample_agent.roles:
            assert role in prompt

    @pytest.mark.unit
    def test_to_llm_prompt_text_preserves_entry_order_within_type(self, sample_agent):
        """Test that entries maintain order within their knowledge type group."""
        now = datetime.now(timezone.utc)

        # Create multiple entries of same type
        entries = [
            KnowledgeEntry(
                id=f"entry-{i}",
                content=f"Memory {i}: Event description",
                knowledge_type=KnowledgeType.MEMORY,
                owning_character_id="char-001",
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            )
            for i in range(1, 4)
        ]

        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=entries,
            retrieved_at=datetime.now(timezone.utc),
        )

        prompt = context.to_llm_prompt_text()

        # Find positions of each memory
        memory_1_index = prompt.index("Memory 1:")
        memory_2_index = prompt.index("Memory 2:")
        memory_3_index = prompt.index("Memory 3:")

        # Should maintain input order
        assert memory_1_index < memory_2_index < memory_3_index
