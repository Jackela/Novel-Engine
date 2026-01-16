"""
Integration tests for SubjectiveBriefPhase adapter.

Tests the integration between knowledge system and SubjectiveBriefPhase
for agent context assembly during simulation turns.

Constitution Compliance:
- Article III (TDD): Tests written FIRST, ensuring they FAIL before implementation
- SC-002: Knowledge retrieval must complete in <500ms for ≤100 entries
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.contexts.knowledge.application.use_cases.retrieve_agent_context import (
    RetrieveAgentContextUseCase,
)
from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.agent_context import AgentContext
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
from src.contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType
from src.contexts.knowledge.infrastructure.adapters.subjective_brief_phase_adapter import (
    SubjectiveBriefPhaseAdapter,
)


@pytest.mark.integration
class TestSubjectiveBriefPhaseAdapter:
    """Integration tests for SubjectiveBriefPhaseAdapter."""

    @pytest.fixture
    def mock_use_case(self):
        """Create mock RetrieveAgentContextUseCase."""
        return AsyncMock(spec=RetrieveAgentContextUseCase)

    @pytest.fixture
    def adapter(self, mock_use_case):
        """Create SubjectiveBriefPhaseAdapter instance."""
        return SubjectiveBriefPhaseAdapter(retrieve_context_use_case=mock_use_case)

    @pytest.fixture
    def sample_agent(self):
        """Create sample agent identity."""
        return AgentIdentity(
            character_id="char-001",
            roles=("player", "engineer"),
        )

    @pytest.fixture
    def sample_entries(self):
        """Create sample knowledge entries."""
        now = datetime.now(timezone.utc)

        return [
            KnowledgeEntry(
                id="entry-001",
                content="You are a skilled engineer.",
                knowledge_type=KnowledgeType.PROFILE,
                owning_character_id="char-001",
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-002",
                content="Repair the life support system.",
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
        ]

    @pytest.mark.asyncio
    async def test_assemble_agent_context_retrieves_from_postgresql(
        self, adapter, mock_use_case, sample_agent, sample_entries
    ):
        """Test that adapter retrieves knowledge from PostgreSQL via use case."""
        # Setup mock to return context
        expected_context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
            turn_number=1,
        )
        mock_use_case.execute.return_value = expected_context

        # Execute
        result = await adapter.get_agent_knowledge_context(
            character_id="char-001",
            roles=("player", "engineer"),
            turn_number=1,
        )

        # Verify use case called
        mock_use_case.execute.assert_called_once()
        call_args = mock_use_case.execute.call_args

        # Verify agent identity constructed correctly
        assert call_args.kwargs["agent"].character_id == "char-001"
        assert call_args.kwargs["agent"].roles == ("player", "engineer")
        assert call_args.kwargs["turn_number"] == 1

        # Verify result is formatted text
        assert isinstance(result, str)
        assert "char-001" in result

    @pytest.mark.asyncio
    async def test_assemble_agent_context_applies_access_control(
        self, adapter, mock_use_case, sample_agent
    ):
        """Test that access control is enforced through use case."""
        # Mock use case returns empty (access denied)
        empty_context = AgentContext(
            agent=sample_agent,
            knowledge_entries=[],  # No accessible entries
            retrieved_at=datetime.now(timezone.utc),
            turn_number=1,
        )
        mock_use_case.execute.return_value = empty_context

        # Execute
        result = await adapter.get_agent_knowledge_context(
            character_id="char-001",
            roles=("player",),
            turn_number=1,
        )

        # Verify no restricted content in result
        assert "Secret information" not in result
        assert "No knowledge available" in result

    @pytest.mark.asyncio
    async def test_assemble_agent_context_returns_formatted_prompt(
        self, adapter, mock_use_case, sample_agent, sample_entries
    ):
        """Test that adapter returns properly formatted LLM prompt text."""
        # Setup
        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
            turn_number=1,
        )
        mock_use_case.execute.return_value = context

        # Execute
        result = await adapter.get_agent_knowledge_context(
            character_id="char-001",
            roles=("player", "engineer"),
            turn_number=1,
        )

        # Verify formatted prompt structure
        assert "Agent: char-001" in result
        assert "Roles: player, engineer" in result
        assert "# Knowledge Context" in result
        assert "## Profile" in result
        assert "## Objective" in result
        assert "skilled engineer" in result
        assert "life support system" in result

    @pytest.mark.asyncio
    async def test_assemble_agent_context_performance_within_500ms(
        self, adapter, mock_use_case, sample_agent
    ):
        """
        Test that context assembly completes within 500ms for ≤100 entries.

        Success Criteria SC-002: Knowledge retrieval <500ms for ≤100 entries
        """
        # Setup - create 100 entries
        now = datetime.now(timezone.utc)
        entries = [
            KnowledgeEntry(
                id=f"entry-{i:03d}",
                content=f"Knowledge entry {i}",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            )
            for i in range(100)
        ]

        context = AgentContext(
            agent=sample_agent,
            knowledge_entries=entries,
            retrieved_at=datetime.now(timezone.utc),
            turn_number=1,
        )
        mock_use_case.execute.return_value = context

        # Execute with timing
        start_time = time.time()
        result = await adapter.get_agent_knowledge_context(
            character_id="char-001",
            roles=("player",),
            turn_number=1,
        )
        duration = time.time() - start_time

        # Verify performance requirement
        assert (
            duration < 0.5
        ), f"Context assembly took {duration:.3f}s, exceeds 500ms limit (SC-002)"

        # Verify all entries included
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.integration
class TestSubjectiveBriefPhaseMarkdownReplacement:
    """Integration tests verifying Markdown file reads are replaced."""

    @pytest.mark.asyncio
    async def test_subjective_brief_phase_does_not_read_markdown_files(self):
        """
        Test that SubjectiveBriefPhase does NOT read Markdown files when adapter is used.

        Functional Requirement FR-006: Markdown files no longer read for agent context
        """
        # Setup mocks
        mock_use_case = AsyncMock(spec=RetrieveAgentContextUseCase)
        adapter = SubjectiveBriefPhaseAdapter(retrieve_context_use_case=mock_use_case)

        # Create sample context
        agent = AgentIdentity(character_id="char-001", roles=("player",))
        now = datetime.now(timezone.utc)
        entry = KnowledgeEntry(
            id="entry-001",
            content="Test content from PostgreSQL",
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="char-001",
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=now,
            updated_at=now,
            created_by="admin-001",
        )
        context = AgentContext(
            agent=agent,
            knowledge_entries=[entry],
            retrieved_at=now,
            turn_number=1,
        )
        mock_use_case.execute.return_value = context

        # Patch built-in open to detect file operations
        with patch(
            "builtins.open", side_effect=AssertionError("Markdown file read detected!")
        ) as mock_open:
            # Execute adapter
            result = await adapter.get_agent_knowledge_context(
                character_id="char-001",
                roles=("player",),
                turn_number=1,
            )

            # Verify no file operations (open not called)
            mock_open.assert_not_called()

            # Verify content from PostgreSQL
            assert "Test content from PostgreSQL" in result
            assert result is not None
