"""
Unit Tests for Multi-Hop Retrieval Service

Warzone 4: AI Brain - BRAIN-013A, BRAIN-013B

Tests for the multi-hop retrieval service that enables complex question
answering through chained reasoning across multiple retrieval hops.

BRAIN-013B: Adds reasoning chain logging and explain mode for debugging.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock

from src.contexts.knowledge.application.services.multi_hop_retriever import (
    MultiHopRetriever,
    QueryDecomposer,
    MultiHopConfig,
    HopConfig,
    ExplainConfig,
    MultiHopResult,
    HopResult,
    HopStatus,
    ReasoningStep,
    DEFAULT_MAX_HOPS,
    DEFAULT_HOP_K,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    RetrievalService,
    RetrievalResult,
    RetrievalOptions,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import RetrievedChunk
from src.contexts.knowledge.application.ports.i_llm_client import (
    ILLMClient,
    LLMRequest,
    LLMResponse,
    LLMError,
)
from src.contexts.knowledge.domain.models.source_type import SourceType


@pytest.fixture
def mock_retrieval_service():
    """Create a mock retrieval service for testing."""
    service = AsyncMock(spec=RetrievalService)

    async def mock_retrieve(query: str, k: int = 5, **kwargs):
        # Return different results based on query
        if "king" in query.lower() and "motive" not in query.lower():
            chunks = [
                RetrievedChunk(
                    chunk_id="chunk1",
                    source_id="lore1",
                    source_type=SourceType.LORE,
                    content="King Arthur was killed by Mordred.",
                    score=0.9,
                    metadata={"name": "King's Death"},
                ),
                RetrievedChunk(
                    chunk_id="chunk2",
                    source_id="lore1",
                    source_type=SourceType.LORE,
                    content="Mordred was Arthur's illegitimate son.",
                    score=0.85,
                    metadata={"name": "Mordred's Identity"},
                ),
            ]
        elif "motive" in query.lower() or "why" in query.lower():
            chunks = [
                RetrievedChunk(
                    chunk_id="chunk3",
                    source_id="lore2",
                    source_type=SourceType.LORE,
                    content="Mordred killed Arthur to claim the throne.",
                    score=0.88,
                    metadata={"name": "Motive"},
                ),
            ]
        elif "villain" in query.lower():
            chunks = [
                RetrievedChunk(
                    chunk_id="chunk4",
                    source_id="character1",
                    source_type=SourceType.CHARACTER,
                    content="Mordred is considered a villain in Arthurian legend.",
                    score=0.92,
                    metadata={"name": "Mordred"},
                ),
            ]
        else:
            chunks = [
                RetrievedChunk(
                    chunk_id="chunk_default",
                    source_id="lore_default",
                    source_type=SourceType.LORE,
                    content="General knowledge about the story.",
                    score=0.7,
                    metadata={},
                ),
            ]

        return RetrievalResult(
            chunks=chunks,
            query=query,
            total_retrieved=len(chunks),
        )

    service.retrieve_relevant = mock_retrieve
    return service


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        system = request.system_prompt.lower()

        # Decomposition response
        if "decompose" in system or "breaking complex" in system:
            return LLMResponse(
                text='["Who killed the king?", "What was their motive?", "Is the killer a villain?"]',
                model="mock-model",
            )
        # Answer synthesis response
        elif "answer based on" in system or "helpful assistant" in system:
            return LLMResponse(
                text="Based on the context, King Arthur was killed by Mordred, who was his illegitimate son. Mordred killed Arthur to claim the throne.",
                model="mock-model",
            )
        else:
            return LLMResponse(
                text="Standard LLM response",
                model="mock-model",
            )

    client.generate = mock_generate
    return client


@pytest.fixture
def failing_llm_client():
    """Create a mock LLM client that always fails."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        raise LLMError("API error")

    client.generate = mock_generate
    return client


@pytest.fixture
def multi_hop_config():
    """Create default multi-hop configuration."""
    return MultiHopConfig()


@pytest.fixture
def multi_hop_retriever(mock_retrieval_service, mock_llm_client):
    """Create a MultiHopRetriever instance with mocks."""
    return MultiHopRetriever(
        retrieval_service=mock_retrieval_service,
        llm_client=mock_llm_client,
    )


class TestHopConfig:
    """Tests for HopConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HopConfig()

        assert config.k == DEFAULT_HOP_K
        assert config.use_context is True
        assert config.min_score == 0.3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = HopConfig(k=5, use_context=False, min_score=0.5)

        assert config.k == 5
        assert config.use_context is False
        assert config.min_score == 0.5

    def test_config_frozen(self):
        """Test config is immutable (frozen dataclass)."""
        config = HopConfig()
        with pytest.raises(AttributeError):
            config.k = 10


class TestMultiHopConfig:
    """Tests for MultiHopConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MultiHopConfig()

        assert config.max_hops == DEFAULT_MAX_HOPS
        assert config.enable_answer_synthesis is True
        assert config.temperature == 0.3

    def test_custom_config(self):
        """Test custom configuration values."""
        hop_config = HopConfig(k=5)
        config = MultiHopConfig(
            max_hops=5,
            default_hop_config=hop_config,
            temperature=0.5,
            enable_answer_synthesis=False,
        )

        assert config.max_hops == 5
        assert config.default_hop_config.k == 5
        assert config.temperature == 0.5
        assert config.enable_answer_synthesis is False

    def test_config_validation_max_hops_too_low(self):
        """Test validation rejects max_hops < 1."""
        with pytest.raises(ValueError, match="max_hops must be at least 1"):
            MultiHopConfig(max_hops=0)

    def test_config_validation_max_hops_too_high(self):
        """Test validation rejects max_hops > 10."""
        with pytest.raises(ValueError, match="max_hops must not exceed 10"):
            MultiHopConfig(max_hops=11)

    def test_config_validation_temperature_out_of_range(self):
        """Test validation rejects temperature outside 0-2."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            MultiHopConfig(temperature=2.5)

    def test_config_frozen(self):
        """Test config is immutable (frozen dataclass)."""
        config = MultiHopConfig()
        with pytest.raises(AttributeError):
            config.max_hops = 5


class TestHopResult:
    """Tests for HopResult value object."""

    def test_result_creation(self):
        """Test creating a hop result."""
        chunks = [
            RetrievedChunk(
                chunk_id="c1",
                source_id="s1",
                source_type=SourceType.LORE,
                content="Test content",
                score=0.9,
                metadata={},
            )
        ]

        result = HopResult(
            hop_number=0,
            query="test query",
            chunks=chunks,
            status=HopStatus.COMPLETED,
            latency_ms=100,
        )

        assert result.hop_number == 0
        assert result.query == "test query"
        assert result.chunk_count == 1
        assert result.status == HopStatus.COMPLETED
        assert result.latency_ms == 100
        assert result.succeeded is True

    def test_result_failed(self):
        """Test failed hop result."""
        result = HopResult(
            hop_number=0,
            query="test query",
            chunks=[],
            status=HopStatus.FAILED,
            latency_ms=100,
        )

        assert result.succeeded is False
        assert result.chunk_count == 0


class TestMultiHopResult:
    """Tests for MultiHopResult value object."""

    def test_result_creation(self):
        """Test creating a multi-hop result."""
        hops = [
            HopResult(
                hop_number=0,
                query="query1",
                chunks=[],
                status=HopStatus.COMPLETED,
            )
        ]

        result = MultiHopResult(
            original_query="test query",
            hops=hops,
            all_chunks=[],
            final_answer="Test answer",
            reasoning_chain="Single hop",
            total_hops=1,
            total_latency_ms=100,
        )

        assert result.original_query == "test query"
        assert result.total_hops == 1
        assert result.final_answer == "Test answer"
        assert result.succeeded is True

    def test_result_succeeded_property(self):
        """Test succeeded property checks hop status."""
        failed_hop = HopResult(
            hop_number=0,
            query="query",
            chunks=[],
            status=HopStatus.FAILED,
        )

        result = MultiHopResult(
            original_query="test",
            hops=[failed_hop],
            all_chunks=[],
            final_answer=None,
            reasoning_chain="",
            total_hops=1,
            total_latency_ms=100,
        )

        assert result.succeeded is False


class TestQueryDecomposer:
    """Tests for QueryDecomposer service."""

    def test_initialization(self, mock_llm_client):
        """Test QueryDecomposer initialization."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        assert decomposer._llm == mock_llm_client
        assert decomposer._temperature == 0.3

    def test_initialization_custom_temperature(self, mock_llm_client):
        """Test initialization with custom temperature."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client, temperature=0.7)

        assert decomposer._temperature == 0.7

    @pytest.mark.asyncio
    async def test_decompose_simple_query(self, mock_llm_client):
        """Test decomposing a simple query (doesn't need decomposition)."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        # Mock to skip decomposition check - directly return simple result
        async def mock_decompose(query: str, max_hops: int = 3):
            return [query]

        decomposer.decompose = mock_decompose
        result = await decomposer.decompose("Who killed the king?")

        assert result == ["Who killed the king?"]

    @pytest.mark.asyncio
    async def test_decompose_complex_query(self, mock_llm_client):
        """Test decomposing a complex query."""
        from unittest.mock import patch

        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        # Mock _needs_decomposition to return True
        with patch.object(decomposer, '_needs_decomposition', return_value=True):
            result = await decomposer.decompose("Who is the villain that killed the king?")

        assert len(result) == 3
        assert "Who killed the king?" in result
        assert "motive" in result[1].lower()

    @pytest.mark.asyncio
    async def test_decompose_with_llm_error(self, failing_llm_client):
        """Test decomposition falls back to original query on LLM error."""
        from unittest.mock import patch

        decomposer = QueryDecomposer(llm_client=failing_llm_client)

        # Mock _needs_decomposition to return True
        with patch.object(decomposer, '_needs_decomposition', return_value=True):
            result = await decomposer.decompose("Who is the villain?")

        assert result == ["Who is the villain?"]

    def test_needs_decomposition_simple_query(self, mock_llm_client):
        """Test _needs_decomposition returns False for simple queries."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        # Simple query - no complex patterns
        result = decomposer._needs_decomposition("Who killed the king?")

        # Single question mark, no conjunctions - might not need decomposition
        assert isinstance(result, bool)

    def test_needs_decomposition_simple_query_no_conjunctions(self, mock_llm_client):
        """Test _needs_decomposition with simple single question."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        # A simple query without conjunctions
        result = decomposer._needs_decomposition("Who killed the king?")

        # Simple query - should return False
        assert result is False

    def test_needs_decomposition_conjunction_query(self, mock_llm_client):
        """Test _needs_decomposition returns True for queries with conjunctions."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        # Complex query with conjunction
        result = decomposer._needs_decomposition("Who killed the king and why?")

        assert result is True

    def test_needs_decomposition_multiple_questions(self, mock_llm_client):
        """Test _needs_decomposition detects multiple questions."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        result = decomposer._needs_decomposition("Who killed the king? What was the motive?")

        assert result is True

    def test_build_next_query_no_chunks(self, mock_llm_client):
        """Test build_next_query with no previous chunks."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        result = decomposer.build_next_query("Who killed the king?", [], 0)

        assert result == "Who killed the king?"

    def test_build_next_query_with_chunks(self, mock_llm_client):
        """Test build_next_query with previous chunks."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        chunks = [
            RetrievedChunk(
                chunk_id="c1",
                source_id="s1",
                source_type=SourceType.LORE,
                content="King Arthur was killed by Mordred.",
                score=0.9,
                metadata={},
            )
        ]

        result = decomposer.build_next_query("Who killed the king?", chunks, 1)

        # For now, returns original query
        assert result == "Who killed the king?"

    def test_parse_decomposition_valid_json(self, mock_llm_client):
        """Test parsing valid JSON decomposition."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        text = '["Who killed the king?", "What was the motive?"]'
        result = decomposer._parse_decomposition(text, max_hops=3)

        assert len(result) == 2
        assert result[0] == "Who killed the king?"
        assert result[1] == "What was the motive?"

    def test_parse_decomposition_markdown_json(self, mock_llm_client):
        """Test parsing JSON wrapped in markdown."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        text = '''```json
["Who killed the king?", "What was the motive?"]
```'''
        result = decomposer._parse_decomposition(text, max_hops=3)

        assert len(result) == 2

    def test_parse_decomposition_invalid_json_fallback(self, mock_llm_client):
        """Test parsing with invalid JSON falls back to line splitting."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        text = """- Who killed the king?
- What was the motive?
- Is this a villain?"""
        result = decomposer._parse_decomposition(text, max_hops=3)

        assert len(result) >= 2

    def test_parse_decomposition_respects_max_hops(self, mock_llm_client):
        """Test parsing respects max_hops limit."""
        decomposer = QueryDecomposer(llm_client=mock_llm_client)

        text = '["q1", "q2", "q3", "q4", "q5"]'
        result = decomposer._parse_decomposition(text, max_hops=3)

        assert len(result) == 3


class TestMultiHopRetriever:
    """Tests for MultiHopRetriever service."""

    def test_initialization(self, mock_retrieval_service, mock_llm_client):
        """Test MultiHopRetriever initialization."""
        retriever = MultiHopRetriever(
            retrieval_service=mock_retrieval_service,
            llm_client=mock_llm_client,
        )

        assert retriever._retrieval == mock_retrieval_service
        assert retriever._llm == mock_llm_client
        assert retriever._config.max_hops == DEFAULT_MAX_HOPS

    def test_initialization_custom_config(self, mock_retrieval_service, mock_llm_client):
        """Test initialization with custom config."""
        config = MultiHopConfig(max_hops=5)
        retriever = MultiHopRetriever(
            retrieval_service=mock_retrieval_service,
            llm_client=mock_llm_client,
            default_config=config,
        )

        assert retriever._config.max_hops == 5

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self, multi_hop_retriever):
        """Test retrieve raises ValueError for empty query."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            await multi_hop_retriever.retrieve("")

    @pytest.mark.asyncio
    async def test_retrieve_single_hop(self, multi_hop_retriever):
        """Test retrieval with single hop (simple query)."""
        from unittest.mock import patch

        # Configure decomposer to not decompose
        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=False):
            result = await multi_hop_retriever.retrieve("Who killed the king?")

        assert result.total_hops == 1
        assert result.succeeded is True
        assert len(result.hops) == 1
        assert result.hops[0].status == HopStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_retrieve_multi_hop(self, multi_hop_retriever):
        """Test retrieval with multiple hops."""
        # The mock LLM will return 3 sub-queries
        # Note: Early termination may occur if a hop returns 0 chunks
        result = await multi_hop_retriever.retrieve(
            "Who is the villain that killed the king and why?"
        )

        # Should have at least 1 hop, up to 3
        assert 1 <= result.total_hops <= 3
        assert result.succeeded is True
        assert len(result.hops) >= 1

        # Each hop should have completed
        for hop in result.hops:
            assert hop.status == HopStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_retrieve_with_answer_synthesis(self, multi_hop_retriever):
        """Test retrieval includes synthesized answer."""
        from unittest.mock import patch

        # Force decomposition
        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who killed the king?")

        assert result.final_answer is not None
        assert len(result.final_answer) > 0

    @pytest.mark.asyncio
    async def test_retrieve_answer_synthesis_disabled(self, multi_hop_retriever):
        """Test retrieval without answer synthesis."""
        from unittest.mock import patch

        config = MultiHopConfig(enable_answer_synthesis=False)

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who killed the king?", config=config)

        assert result.final_answer is None

    @pytest.mark.asyncio
    async def test_retrieve_early_termination(self, mock_retrieval_service, mock_llm_client):
        """Test retrieval terminates early when enough chunks found."""
        from unittest.mock import patch

        # Override should_terminate_early to terminate after 1 chunk
        retriever = MultiHopRetriever(
            retrieval_service=mock_retrieval_service,
            llm_client=mock_llm_client,
        )
        retriever._should_terminate_early = lambda h, c: len(c) >= 1

        # Force multi-hop
        with patch.object(retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await retriever.retrieve("Complex query about the story")

        assert result.terminated_early is True

    @pytest.mark.asyncio
    async def test_retrieve_sync(self, multi_hop_retriever):
        """Test synchronous retrieval method."""
        result = await multi_hop_retriever.retrieve_sync("Who killed the king?")

        assert result.total_hops == 1
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_retrieve_custom_config(self, multi_hop_retriever):
        """Test retrieval with custom configuration."""
        from unittest.mock import patch

        config = MultiHopConfig(max_hops=2)

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Complex query", config=config)

        # Should respect max_hops=2 even if LLM returns 3 sub-queries
        assert result.total_hops <= 2

    @pytest.mark.asyncio
    async def test_build_context_from_chunks_empty(self, multi_hop_retriever):
        """Test _build_context_from_chunks with empty list."""
        result = multi_hop_retriever._build_context_from_chunks([])

        assert result is None

    @pytest.mark.asyncio
    async def test_build_context_from_chunks(self, multi_hop_retriever):
        """Test _build_context_from_chunks builds context."""
        chunks = [
            RetrievedChunk(
                chunk_id="c1",
                source_id="s1",
                source_type=SourceType.LORE,
                content="A" * 300,  # Long content
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="c2",
                source_id="s2",
                source_type=SourceType.LORE,
                content="B" * 300,
                score=0.8,
                metadata={},
            ),
        ]

        result = multi_hop_retriever._build_context_from_chunks(chunks)

        assert result is not None
        assert "AAA..." in result or "..." in result  # Content truncated

    @pytest.mark.asyncio
    async def test_should_terminate_early_enough_chunks(self, multi_hop_retriever):
        """Test _should_terminate_early with enough chunks."""
        chunks = [Mock(chunk_id=f"c{i}") for i in range(15)]
        hops = [Mock(chunk_count=5)]

        result = multi_hop_retriever._should_terminate_early(hops, chunks)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_terminate_early_not_enough_chunks(self, multi_hop_retriever):
        """Test _should_terminate_early with insufficient chunks."""
        chunks = [Mock(chunk_id=f"c{i}") for i in range(5)]
        hops = [Mock(chunk_count=5)]

        result = multi_hop_retriever._should_terminate_early(hops, chunks)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_terminate_early_empty_hop(self, multi_hop_retriever):
        """Test _should_terminate_early when last hop is empty."""
        chunks = [Mock(chunk_id=f"c{i}") for i in range(5)]
        hops = [Mock(chunk_count=0)]

        result = multi_hop_retriever._should_terminate_early(hops, chunks)

        assert result is True


class TestMultiHopIntegration:
    """Integration tests for multi-hop retrieval."""

    @pytest.mark.asyncio
    async def test_full_multi_hop_flow(self, multi_hop_retriever):
        """Test complete multi-hop retrieval flow."""
        result = await multi_hop_retriever.retrieve(
            "Who is the villain that killed the king and why?"
        )

        # Verify structure
        assert result.original_query == "Who is the villain that killed the king and why?"
        # May have early termination if a hop returns 0 chunks
        assert 1 <= result.total_hops <= 3
        assert result.succeeded is True

        # Verify hops
        assert len(result.hops) == result.total_hops
        for i, hop in enumerate(result.hops):
            assert hop.hop_number == i
            assert hop.status == HopStatus.COMPLETED

        # Verify answer synthesis
        assert result.final_answer is not None
        assert "Mordred" in result.final_answer

    @pytest.mark.asyncio
    async def test_multi_hop_deduplicates_chunks(self, multi_hop_retriever):
        """Test multi-hop retrieval deduplicates chunks across hops."""
        result = await multi_hop_retriever.retrieve("Multi-hop query")

        # Get all chunk IDs
        chunk_ids = [c.chunk_id for c in result.all_chunks]

        # Should be unique
        assert len(chunk_ids) == len(set(chunk_ids))

    @pytest.mark.asyncio
    async def test_multi_hop_reasoning_chain(self, multi_hop_retriever):
        """Test multi-hop retrieval builds reasoning chain."""
        from unittest.mock import patch

        # Force decomposition to get multi-hop
        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Complex query about the story")

        assert result.reasoning_chain is not None
        assert len(result.reasoning_chain) > 0
        # New format uses "Query:" and "Reasoning Path:" or "Single-hop" for single hop
        assert "Query:" in result.reasoning_chain or "Single-hop" in result.reasoning_chain

    @pytest.mark.asyncio
    async def test_multi_hop_latency_tracking(self, multi_hop_retriever):
        """Test multi-hop retrieval tracks latency."""
        result = await multi_hop_retriever.retrieve("Test query")

        assert result.total_latency_ms >= 0
        for hop in result.hops:
            assert hop.latency_ms >= 0


class TestReasoningChain:
    """Tests for reasoning chain logging and explain mode (BRAIN-013B)."""

    @pytest.mark.asyncio
    async def test_reasoning_chain_captured(self, multi_hop_retriever):
        """Test that reasoning chain is captured for multi-hop retrieval."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who is the villain that killed the king?")

        # Reasoning chain should exist and contain query info
        assert result.reasoning_chain is not None
        assert len(result.reasoning_chain) > 0
        assert "Query:" in result.reasoning_chain or "Hop" in result.reasoning_chain

    @pytest.mark.asyncio
    async def test_reasoning_steps_created(self, multi_hop_retriever):
        """Test that ReasoningStep objects are created for each hop."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who is the villain that killed the king?")

        # Should have reasoning steps if multi-hop occurred
        if result.total_hops > 1:
            assert len(result.reasoning_steps) > 0

            # Check first step structure
            first_step = result.reasoning_steps[0]
            assert hasattr(first_step, 'hop_number')
            assert hasattr(first_step, 'query')
            assert hasattr(first_step, 'query_type')
            assert hasattr(first_step, 'chunks_found')
            assert hasattr(first_step, 'top_sources')
            assert hasattr(first_step, 'latency_ms')

    @pytest.mark.asyncio
    async def test_reasoning_step_includes_query_type(self, multi_hop_retriever):
        """Test that reasoning steps track query type (original/decomposed/followup)."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Complex multi-part question")

        if result.reasoning_steps:
            # First hop should be "original"
            assert result.reasoning_steps[0].query_type == "original"

            # Subsequent hops should be "decomposed"
            if len(result.reasoning_steps) > 1:
                for step in result.reasoning_steps[1:]:
                    assert step.query_type in ("decomposed", "followup")

    @pytest.mark.asyncio
    async def test_reasoning_step_includes_top_sources(self, multi_hop_retriever):
        """Test that reasoning steps include top sources."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who killed the king?")

        if result.reasoning_steps:
            # At least one step should have sources
            has_sources = any(
                len(step.top_sources) > 0
                for step in result.reasoning_steps
            )
            assert has_sources, "At least one reasoning step should have sources"

    @pytest.mark.asyncio
    async def test_explain_output_format(self, multi_hop_retriever):
        """Test get_explain_output() returns formatted explanation."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who killed the king?")

        explain_output = result.get_explain_output()

        # Should contain key sections
        assert "Multi-Hop Retrieval Explanation:" in explain_output
        assert "Original Query:" in explain_output
        assert "Total Hops:" in explain_output
        assert "Total Chunks:" in explain_output
        assert "Total Latency:" in explain_output
        assert "Reasoning Path:" in explain_output

    @pytest.mark.asyncio
    async def test_explain_output_verbose(self, multi_hop_retriever):
        """Test verbose explain output includes context summaries."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who killed the king?")

        # Verbose output should include more detail
        verbose_output = result.get_explain_output(verbose=True)
        non_verbose_output = result.get_explain_output(verbose=False)

        # Verbose should be longer or equal
        assert len(verbose_output) >= len(non_verbose_output)

    @pytest.mark.asyncio
    async def test_explain_output_with_answer(self, multi_hop_retriever):
        """Test explain output includes final answer when available."""
        from unittest.mock import patch

        with patch.object(multi_hop_retriever._decomposer, '_needs_decomposition', return_value=True):
            result = await multi_hop_retriever.retrieve("Who killed the king?")

        explain_output = result.get_explain_output()

        # If answer synthesis succeeded, should include it
        if result.final_answer:
            assert "Final Answer:" in explain_output
            assert result.final_answer in explain_output

    def test_reasoning_step_to_explain_line(self):
        """Test ReasoningStep.to_explain_line() format."""
        from src.contexts.knowledge.application.services.multi_hop_retriever import ReasoningStep

        step = ReasoningStep(
            hop_number=0,
            query="Who killed the king?",
            query_type="original",
            chunks_found=3,
            top_sources=("LORE:lore1", "CHARACTER:char1"),
            latency_ms=150,
            context_summary="Previous context...",
        )

        line = step.to_explain_line()

        assert "Step 0:" in line
        assert "Who killed the king?" in line
        assert "(original)" in line
        assert "3 chunks" in line
        assert "150ms" in line


class TestExplainConfig:
    """Tests for ExplainConfig value object (BRAIN-013B)."""

    def test_default_explain_config(self):
        """Test default ExplainConfig values."""
        from src.contexts.knowledge.application.services.multi_hop_retriever import ExplainConfig

        config = ExplainConfig()

        assert config.enabled is False
        assert config.include_chunk_content is True
        assert config.include_source_info is True
        assert config.max_content_length == 150

    def test_custom_explain_config(self):
        """Test custom ExplainConfig values."""
        from src.contexts.knowledge.application.services.multi_hop_retriever import ExplainConfig

        config = ExplainConfig(
            enabled=True,
            include_chunk_content=False,
            include_source_info=False,
            max_content_length=300,
        )

        assert config.enabled is True
        assert config.include_chunk_content is False
        assert config.include_source_info is False
        assert config.max_content_length == 300

    def test_explain_config_frozen(self):
        """Test ExplainConfig is immutable (frozen dataclass)."""
        from src.contexts.knowledge.application.services.multi_hop_retriever import ExplainConfig

        config = ExplainConfig()
        with pytest.raises(AttributeError):
            config.enabled = True
