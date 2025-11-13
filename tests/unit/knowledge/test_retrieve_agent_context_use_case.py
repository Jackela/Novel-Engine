"""
Unit tests for RetrieveAgentContextUseCase.

Tests the application use case for retrieving and assembling agent knowledge context.

Constitution Compliance:
- Article III (TDD): Tests written FIRST, ensuring they FAIL before implementation
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from contexts.knowledge.application.use_cases.retrieve_agent_context import (
    RetrieveAgentContextUseCase,
)
from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from contexts.knowledge.domain.models.access_level import AccessLevel
from contexts.knowledge.domain.models.agent_context import AgentContext
from contexts.knowledge.domain.models.agent_identity import AgentIdentity
from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from contexts.knowledge.domain.models.knowledge_type import KnowledgeType


class TestRetrieveAgentContextUseCase:
    """Test suite for RetrieveAgentContextUseCase."""

    @pytest.fixture
    def mock_retriever(self):
        """Create mock IKnowledgeRetriever."""
        return AsyncMock()

    @pytest.fixture
    def mock_assembler(self):
        """Create mock IContextAssembler."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_retriever, mock_assembler):
        """Create RetrieveAgentContextUseCase instance."""
        return RetrieveAgentContextUseCase(
            knowledge_retriever=mock_retriever,
            context_assembler=mock_assembler,
        )

    @pytest.fixture
    def sample_agent(self):
        """Create sample agent identity."""
        return AgentIdentity(
            character_id="char-001",
            roles=("player",),
        )

    @pytest.fixture
    def sample_entries(self):
        """Create sample knowledge entries."""
        now = datetime.now(timezone.utc)

        return [
            KnowledgeEntry(
                id="entry-001",
                content="Test profile content",
                knowledge_type=KnowledgeType.PROFILE,
                owning_character_id="char-001",
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=now,
                updated_at=now,
                created_by="admin-001",
            ),
            KnowledgeEntry(
                id="entry-002",
                content="Test objective content",
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
    async def test_retrieve_agent_context_returns_accessible_entries(
        self, use_case, mock_retriever, mock_assembler, sample_agent, sample_entries
    ):
        """Test that use case retrieves accessible entries and assembles context."""
        # Setup mocks
        mock_retriever.retrieve_for_agent.return_value = sample_entries
        expected_context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
        )
        mock_assembler.assemble_context.return_value = expected_context

        # Execute
        result = await use_case.execute(agent=sample_agent)

        # Verify retriever called
        mock_retriever.retrieve_for_agent.assert_called_once_with(
            agent=sample_agent,
            knowledge_types=None,
            owning_character_id=None,
        )

        # Verify assembler called
        mock_assembler.assemble_context.assert_called_once_with(
            agent=sample_agent,
            entries=sample_entries,
            turn_number=None,
        )

        # Verify result
        assert result == expected_context

    @pytest.mark.asyncio
    async def test_retrieve_agent_context_filters_by_knowledge_types(
        self, use_case, mock_retriever, mock_assembler, sample_agent, sample_entries
    ):
        """Test that knowledge type filter is passed to retriever."""
        # Setup
        knowledge_types = [KnowledgeType.PROFILE, KnowledgeType.OBJECTIVE]
        mock_retriever.retrieve_for_agent.return_value = sample_entries
        mock_assembler.assemble_context.return_value = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
        )

        # Execute
        await use_case.execute(
            agent=sample_agent,
            knowledge_types=knowledge_types,
        )

        # Verify filter passed to retriever
        mock_retriever.retrieve_for_agent.assert_called_once_with(
            agent=sample_agent,
            knowledge_types=knowledge_types,
            owning_character_id=None,
        )

    @pytest.mark.asyncio
    async def test_retrieve_agent_context_filters_by_owning_character(
        self, use_case, mock_retriever, mock_assembler, sample_agent, sample_entries
    ):
        """Test that owning character filter is passed to retriever."""
        # Setup
        owning_character_id = "char-001"
        mock_retriever.retrieve_for_agent.return_value = sample_entries
        mock_assembler.assemble_context.return_value = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
        )

        # Execute
        await use_case.execute(
            agent=sample_agent,
            owning_character_id=owning_character_id,
        )

        # Verify filter passed to retriever
        mock_retriever.retrieve_for_agent.assert_called_once_with(
            agent=sample_agent,
            knowledge_types=None,
            owning_character_id=owning_character_id,
        )

    @pytest.mark.asyncio
    async def test_retrieve_agent_context_returns_empty_for_no_access(
        self, use_case, mock_retriever, mock_assembler, sample_agent
    ):
        """Test that use case handles empty entry list gracefully."""
        # Setup - no accessible entries
        mock_retriever.retrieve_for_agent.return_value = []
        expected_context = AgentContext(
            agent=sample_agent,
            knowledge_entries=[],
            retrieved_at=datetime.now(timezone.utc),
        )
        mock_assembler.assemble_context.return_value = expected_context

        # Execute
        result = await use_case.execute(agent=sample_agent)

        # Verify empty list passed to assembler
        mock_assembler.assemble_context.assert_called_once_with(
            agent=sample_agent,
            entries=[],
            turn_number=None,
        )

        # Verify result has no entries
        assert len(result.knowledge_entries) == 0

    @pytest.mark.asyncio
    async def test_retrieve_agent_context_assembles_context_aggregate(
        self, use_case, mock_retriever, mock_assembler, sample_agent, sample_entries
    ):
        """Test that use case assembles AgentContext aggregate correctly."""
        # Setup
        turn_number = 42
        mock_retriever.retrieve_for_agent.return_value = sample_entries
        expected_context = AgentContext(
            agent=sample_agent,
            knowledge_entries=sample_entries,
            retrieved_at=datetime.now(timezone.utc),
            turn_number=turn_number,
        )
        mock_assembler.assemble_context.return_value = expected_context

        # Execute
        result = await use_case.execute(
            agent=sample_agent,
            turn_number=turn_number,
        )

        # Verify assembler called with turn number
        mock_assembler.assemble_context.assert_called_once_with(
            agent=sample_agent,
            entries=sample_entries,
            turn_number=turn_number,
        )

        # Verify result is AgentContext
        assert isinstance(result, AgentContext)
        assert result.agent == sample_agent
        assert result.turn_number == turn_number
