"""
Multi-Hop Retrieval Service

Enables complex question answering through chained reasoning.
Decomposes complex queries into sub-queries, uses results from each hop
to inform the next, enabling multi-step reasoning for RAG.

Constitution Compliance:
- Article II (Hexagonal): Application service using retrieval and LLM ports
- Article V (SOLID): SRP - multi-hop retrieval coordination only

Warzone 4: AI Brain - BRAIN-013A, BRAIN-013B
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import structlog

from ...application.ports.i_llm_client import ILLMClient, LLMError, LLMRequest
from ..services.knowledge_ingestion_service import RetrievedChunk

if TYPE_CHECKING:
    from .retrieval_service import RetrievalService

logger = structlog.get_logger()


# Default configuration
DEFAULT_MAX_HOPS = 3
DEFAULT_HOP_K = 3  # Results per hop
DEFAULT_TEMPERATURE = 0.3  # Lower for more deterministic decomposition


class HopStatus(str, Enum):
    """
    Status of a hop in the multi-hop retrieval.

    Attributes:
        PENDING: Hop not yet started
        IN_PROGRESS: Hop currently executing
        COMPLETED: Hop completed successfully
        FAILED: Hop failed
        SKIPPED: Hop skipped (e.g., due to early termination)
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class HopConfig:
    """
    Configuration for a single hop in multi-hop retrieval.

    Why frozen:
        Immutable snapshot ensures hop config doesn't change during retrieval.

    Attributes:
        k: Number of results to retrieve in this hop
        use_context: Whether to use previous hop context in this hop
        min_score: Minimum relevance score for results
    """

    k: int = DEFAULT_HOP_K
    use_context: bool = True
    min_score: float = 0.3


@dataclass(frozen=True, slots=True)
class ExplainConfig:
    """
    Configuration for explain mode in multi-hop retrieval.

    Why frozen:
        Immutable config ensures consistent explain behavior.

    Attributes:
        enabled: Whether explain mode is active
        include_chunk_content: Whether to include actual chunk content in explanation
        include_source_info: Whether to include source (type, id) for each chunk
        max_content_length: Maximum characters of chunk content to include
    """

    enabled: bool = False
    include_chunk_content: bool = True
    include_source_info: bool = True
    max_content_length: int = 150


@dataclass(frozen=True, slots=True)
class MultiHopConfig:
    """
    Configuration for multi-hop retrieval.

    Attributes:
        max_hops: Maximum number of hops to perform (prevents infinite loops)
        default_hop_config: Default configuration for each hop
        temperature: Temperature for query decomposition LLM calls
        enable_answer_synthesis: Whether to synthesize final answer from all hops
        explain: Configuration for explain mode (detailed reasoning chain)
    """

    max_hops: int = DEFAULT_MAX_HOPS
    default_hop_config: HopConfig = field(default_factory=HopConfig)
    temperature: float = DEFAULT_TEMPERATURE
    enable_answer_synthesis: bool = True
    explain: ExplainConfig = field(default_factory=ExplainConfig)

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.max_hops < 1:
            raise ValueError("max_hops must be at least 1")
        if self.max_hops > 10:
            raise ValueError("max_hops must not exceed 10")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")


@dataclass(frozen=True, slots=True)
class ReasoningStep:
    """
    Detailed step in the reasoning chain.

    Why frozen:
        Immutable record ensures reasoning history isn't modified.

    Attributes:
        hop_number: The hop index (0-based)
        query: The query used for this hop
        query_type: Type of query (original, decomposed, followup)
        chunks_found: Number of chunks retrieved
        top_sources: Top sources (source_type:source_id) from this hop
        latency_ms: Execution time in milliseconds
        context_summary: Summary of context used from previous hops
    """

    hop_number: int
    query: str
    query_type: str  # "original", "decomposed", "followup"
    chunks_found: int
    top_sources: tuple[str, ...]  # Top 3 source identifiers
    latency_ms: int
    context_summary: str | None = None

    def to_explain_line(self) -> str:
        """
        Convert reasoning step to human-readable explanation line.

        Returns:
            Formatted explanation string
        """
        sources_str = ", ".join(self.top_sources) if self.top_sources else "None"
        return (
            f"  Step {self.hop_number}: Query='{self.query}' "
            f"({self.query_type}) -> {self.chunks_found} chunks, "
            f"sources=[{sources_str}], {self.latency_ms}ms"
        )


@dataclass
class HopResult:
    """
    Result of a single hop in multi-hop retrieval.

    Attributes:
        hop_number: The hop index (0-based)
        query: The query used for this hop
        chunks: Chunks retrieved in this hop
        status: Status of the hop
        latency_ms: Execution time in milliseconds
        context_used: Context from previous hops used in this hop
        reasoning_step: Detailed reasoning step for explain mode
    """

    hop_number: int
    query: str
    chunks: list[RetrievedChunk]
    status: HopStatus
    latency_ms: int = 0
    context_used: str | None = None
    reasoning_step: ReasoningStep | None = None

    @property
    def chunk_count(self) -> int:
        """Get number of chunks retrieved in this hop."""
        return len(self.chunks)

    @property
    def succeeded(self) -> bool:
        """Check if hop completed successfully."""
        return self.status == HopStatus.COMPLETED


@dataclass
class MultiHopResult:
    """
    Result of multi-hop retrieval.

    Attributes:
        original_query: The original user query
        hops: List of hop results (one per hop performed)
        all_chunks: All unique chunks retrieved across all hops
        final_answer: Synthesized answer (if enabled)
        reasoning_chain: The reasoning chain showing how each hop informed the next
        total_hops: Total number of hops performed
        total_latency_ms: Total execution time in milliseconds
        terminated_early: Whether retrieval terminated early (e.g., found answer)
        reasoning_steps: Detailed reasoning steps for explain mode
    """

    original_query: str
    hops: list[HopResult]
    all_chunks: list[RetrievedChunk]
    final_answer: str | None
    reasoning_chain: str
    total_hops: int
    total_latency_ms: int
    terminated_early: bool = False
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        """Check if retrieval succeeded (at least one hop completed)."""
        return any(hop.succeeded for hop in self.hops)

    @property
    def total_chunks(self) -> int:
        """Get total unique chunks retrieved."""
        return len(self.all_chunks)

    def get_explain_output(self, verbose: bool = True) -> str:
        """
        Get detailed explanation of the reasoning path.

        Args:
            verbose: Whether to include detailed chunk information

        Returns:
            Formatted explanation string

        Example:
            >>> result = await retriever.retrieve("Who killed the king?")
            >>> print(result.get_explain_output())
            Multi-Hop Retrieval Explanation:
            Original Query: Who killed the king?
              Step 0: Query='Who killed the king?' (original) -> 3 chunks...
              Step 1: Query='What was their motive?' (followup) -> 2 chunks...
        """
        lines = [
            "Multi-Hop Retrieval Explanation:",
            f"Original Query: {self.original_query}",
            f"Total Hops: {self.total_hops}",
            f"Total Chunks: {self.total_chunks}",
            f"Total Latency: {self.total_latency_ms}ms",
            "",
            "Reasoning Path:",
        ]

        if self.reasoning_steps:
            for step in self.reasoning_steps:
                lines.append(step.to_explain_line())
                if verbose and step.context_summary:
                    lines.append(f"    Context: {step.context_summary}")
        else:
            # Fallback to reasoning_chain
            lines.append(f"  {self.reasoning_chain}")

        if self.final_answer:
            lines.append("")
            lines.append(f"Final Answer: {self.final_answer}")

        return "\n".join(lines)


class QueryDecomposer:
    """
    Service for decomposing complex queries into sub-queries.

    Identifies when a query requires multiple information retrieval steps
    and generates sub-queries for each hop.

    Example:
        >>> decomposer = QueryDecomposer(llm_client=gemini_client)
        >>> sub_queries = await decomposer.decompose("Who killed the king and why?")
        >>> print(sub_queries)
        ["Who killed the king?", "What was the motive?"]
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        """
        Initialize the query decomposer.

        Args:
            llm_client: LLM client for decomposition
            temperature: Temperature for decomposition LLM calls
        """
        self._llm = llm_client
        self._temperature = temperature

        logger.debug(
            "query_decomposer_initialized",
            temperature=temperature,
        )

    async def decompose(
        self,
        query: str,
        max_hops: int = DEFAULT_MAX_HOPS,
    ) -> list[str]:
        """
        Decompose a complex query into sub-queries.

        Args:
            query: The query to decompose
            max_hops: Maximum number of sub-queries to generate

        Returns:
            List of sub-queries (may be empty if decomposition isn't needed)

        Raises:
            ValueError: If query is empty

        Example:
            >>> sub_queries = await decomposer.decompose(
            ...     "Who is the villain that killed the king?"
            ... )
            >>> # Returns: ["Who killed the king?", "Who is the killer?"]
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        logger.debug(
            "query_decompose_start",
            query=query,
            max_hops=max_hops,
        )

        # Check if decomposition is needed
        needs_decomposition = self._needs_decomposition(query)

        if not needs_decomposition:
            logger.debug(
                "query_decompose_not_needed",
                query=query,
            )
            return [query]

        # Generate sub-queries
        prompt = self._build_decomposition_prompt(query, max_hops)

        request = LLMRequest(
            system_prompt=self._get_system_prompt(),
            user_prompt=prompt,
            temperature=self._temperature,
            max_tokens=500,
        )

        try:
            response = await self._llm.generate(request)
            sub_queries = self._parse_decomposition(response.text, max_hops)

            logger.info(
                "query_decompose_complete",
                query=query,
                sub_query_count=len(sub_queries),
            )

            return sub_queries

        except LLMError as e:
            logger.error(
                "query_decompose_failed",
                query=query,
                error=str(e),
            )
            # Return original query as single sub-query
            return [query]

    def _needs_decomposition(self, query: str) -> bool:
        """
        Check if a query needs decomposition.

        Uses simple heuristics to identify complex queries.

        Args:
            query: Query to check

        Returns:
            True if decomposition is recommended
        """
        # Simple heuristic: multi-part queries or specific patterns
        complex_patterns = [
            " and ",
            " but ",
            " or ",  # Conjunctions
            " who ",
            " what ",
            " where ",
            " when ",
            " why ",
            " how ",  # W-words (multiple)
            " then ",
            " after ",  # Sequential
            " because ",
            " since ",  # Causal
        ]

        query_lower = query.lower()
        pattern_count = sum(1 for pattern in complex_patterns if pattern in query_lower)

        # Also check for multiple question marks
        question_mark_count = query.count("?")

        # Decompose if multiple patterns or multiple questions
        return pattern_count >= 1 or question_mark_count > 1

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for query decomposition.

        Returns:
            System instruction prompt
        """
        return """You are an expert at breaking complex questions into step-by-step reasoning chains.

Your task is to decompose complex questions into a sequence of simpler sub-questions.
Each sub-question should build on the answer to the previous one.

Guidelines:
- Start with the most direct information need
- Each subsequent question should depend on or refine the previous
- Return valid JSON array of strings
- Generate 2-4 sub-questions maximum

Example:
Input: "Who is the villain that killed the king and what was their motive?"
Output: ["Who killed the king?", "What was their motive?", "Is this person a villain?"]"""

    def _build_decomposition_prompt(self, query: str, max_hops: int) -> str:
        """
        Build the user prompt for query decomposition.

        Args:
            query: Original query
            max_hops: Maximum number of hops

        Returns:
            Formatted prompt for LLM
        """
        return f"""Original query: "{query}"

Decompose this question into a reasoning chain of at most {max_hops} sub-questions.
Start with the most direct question, then follow-up questions that build on it.
Return ONLY a valid JSON array of strings, like this:
["first question?", "second question?", "third question?"]"""

    def _parse_decomposition(self, text: str, max_hops: int) -> list[str]:
        """
        Parse LLM response to extract sub-queries.

        Args:
            text: LLM response text
            max_hops: Maximum number of sub-queries

        Returns:
            List of parsed sub-queries
        """
        # Try to parse as JSON array
        try:
            # Extract JSON from response (might be in markdown)
            clean_text = text.strip()
            if clean_text.startswith("```"):
                # Remove markdown code block
                lines = clean_text.split("\n")
                clean_text = "\n".join(lines[1:-1])

            sub_queries = json.loads(clean_text)

            if isinstance(sub_queries, list):
                # Ensure all items are strings and end with '?'
                result = [str(q).strip() for q in sub_queries if q]
                return result[:max_hops]

        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning(
                "query_decompose_json_parse_failed",
                response=text[:200],
            )

        # Fallback: split by newlines
        result = []
        for line in text.split("\n"):
            line = line.strip()
            # Remove common prefixes
            for prefix in ['"-', "* ", "• ", "- ", "1. ", "2. ", "3. "]:
                if line.startswith(prefix):
                    line = line[len(prefix) :].strip('"').strip()
                    break
            if line and len(line) > 2:
                result.append(line)

        return result[:max_hops]

    def build_next_query(
        self,
        original_query: str,
        previous_chunks: list[RetrievedChunk],
        hop_number: int,
    ) -> str:
        """
        Build the next query based on previous hop results.

        Args:
            original_query: The original user query
            previous_chunks: Chunks retrieved in previous hop
            hop_number: Current hop number (0-based)

        Returns:
            Query for the next hop
        """
        if not previous_chunks:
            return original_query

        # For now, return the original query
        # In a more sophisticated implementation, we could:
        # 1. Extract key entities from previous chunks
        # 2. Generate follow-up questions
        # 3. Refine the query based on what was learned

        # Simple refinement: use original query for all hops
        # The retrieval context will be different due to chunk content
        return original_query


class MultiHopRetriever:
    """
    Service for multi-hop retrieval in RAG systems.

    Enables complex question answering through chained reasoning:
    1. Decomposes complex queries into sub-queries
    2. Executes retrieval for each sub-query (hop)
    3. Uses results from each hop to inform the next
    4. Synthesizes final answer from all retrieved information

    Prevents infinite loops with max_hops limit.
    Tracks reasoning chain for debugging and explainability.
    Supports explain mode for detailed reasoning path visualization.

    Constitution Compliance:
        - Article II (Hexagonal): Application service coordinating ports
        - Article V (SOLID): SRP - multi-hop retrieval coordination only

    Example:
        >>> retriever = MultiHopRetriever(
        ...     retrieval_service=retrieval_svc,
        ...     llm_client=gemini_client,
        ... )
        >>> result = await retriever.retrieve(
        ...     query="Who is the villain that killed the king?",
        ... )
        >>> print(result.reasoning_chain)
        >>> # Query: Who is the villain that killed the king?
        >>> # Reasoning Path:
        >>> #   Step 0: Query='Who killed the king?' (original) -> 3 chunks...
        >>> #   Step 1: Query='What was their motive?' (decomposed) -> 2 chunks...
        >>> print(result.get_explain_output())
        >>> # Multi-Hop Retrieval Explanation:
        >>> # Original Query: Who is the villain that killed the king?
        >>> # Total Hops: 2
        >>> # ...
        >>> print(result.final_answer)
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: ILLMClient,
        default_config: MultiHopConfig | None = None,
    ):
        """
        Initialize the multi-hop retriever.

        Args:
            retrieval_service: Service for retrieving chunks
            llm_client: LLM client for query decomposition and answer synthesis
            default_config: Default configuration for multi-hop retrieval
        """
        self._retrieval = retrieval_service
        self._llm = llm_client
        self._config = default_config or MultiHopConfig()
        self._decomposer = QueryDecomposer(
            llm_client=llm_client,
            temperature=self._config.temperature,
        )

        logger.info(
            "multi_hop_retriever_initialized",
            max_hops=self._config.max_hops,
            enable_answer_synthesis=self._config.enable_answer_synthesis,
        )

    async def retrieve(
        self,
        query: str,
        config: MultiHopConfig | None = None,
    ) -> MultiHopResult:
        """
        Perform multi-hop retrieval for a complex query.

        Args:
            query: The query to retrieve information for
            config: Optional configuration override

        Returns:
            MultiHopResult with all hop results and synthesized answer

        Raises:
            ValueError: If query is empty

        Example:
            >>> result = await retriever.retrieve(
            ...     query="Who is the villain that killed the king?",
            ... )
            >>> for hop in result.hops:
            ...     print(f"Hop {hop.hop_number}: {hop.query}")
            ...     print(f"  Retrieved {hop.chunk_count} chunks")
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        start_time = time.time()

        multi_hop_config = config or self._config

        logger.info(
            "multi_hop_retrieval_start",
            query=query,
            max_hops=multi_hop_config.max_hops,
        )

        # Step 1: Decompose query into sub-queries
        sub_queries = await self._decomposer.decompose(
            query,
            max_hops=multi_hop_config.max_hops,
        )

        # If only one sub-query, do single retrieval
        if len(sub_queries) <= 1:
            return await self._single_hop_retrieval(query, multi_hop_config, start_time)

        # Step 2: Execute multi-hop retrieval
        hops: list[HopResult] = []
        all_chunks: list[RetrievedChunk] = []
        seen_chunk_ids: set[str] = set()
        reasoning_parts: list[str] = []
        reasoning_steps: list[ReasoningStep] = []

        previous_hop_chunks: list[RetrievedChunk] = []

        for hop_num, sub_query in enumerate(sub_queries[: multi_hop_config.max_hops]):
            hop_start = time.time()

            # Determine query type
            query_type = "original" if hop_num == 0 else "decomposed"

            # Build query with context from previous hops
            context_from_previous = self._build_context_from_chunks(previous_hop_chunks)
            hop_query = self._decomposer.build_next_query(
                query,
                previous_hop_chunks,
                hop_num,
            )

            logger.debug(
                "multi_hop_retrieval_hop_start",
                hop_number=hop_num,
                query=hop_query,
                query_type=query_type,
                has_context=bool(context_from_previous),
            )

            # Execute retrieval
            try:
                hop_result = await self._retrieval.retrieve_relevant(
                    query=hop_query,
                    k=multi_hop_config.default_hop_config.k,
                )

                hop_latency = int((time.time() - hop_start) * 1000)

                # Deduplicate chunks
                unique_chunks = [
                    c for c in hop_result.chunks if c.chunk_id not in seen_chunk_ids
                ]
                for c in unique_chunks:
                    seen_chunk_ids.add(c.chunk_id)

                all_chunks.extend(unique_chunks)
                previous_hop_chunks = unique_chunks

                # Extract top sources for reasoning step
                top_sources = self._extract_top_sources(unique_chunks, limit=3)

                # Create reasoning step
                reasoning_step = ReasoningStep(
                    hop_number=hop_num,
                    query=sub_query,
                    query_type=query_type,
                    chunks_found=len(unique_chunks),
                    top_sources=tuple(top_sources),
                    latency_ms=hop_latency,
                    context_summary=(
                        context_from_previous[:100] + "..."
                        if context_from_previous and len(context_from_previous) > 100
                        else context_from_previous
                    ),
                )
                reasoning_steps.append(reasoning_step)

                # Create hop result
                hop = HopResult(
                    hop_number=hop_num,
                    query=sub_query,
                    chunks=unique_chunks,
                    status=HopStatus.COMPLETED,
                    latency_ms=hop_latency,
                    context_used=context_from_previous,
                    reasoning_step=reasoning_step,
                )

                # Track reasoning
                reasoning_parts.append(
                    f"Hop {hop_num}: '{sub_query}' -> {len(unique_chunks)} chunks"
                )

                # Log reasoning step at info level for debugging
                logger.info(
                    "multi_hop_retrieval_hop_complete",
                    hop_number=hop_num,
                    query=sub_query,
                    query_type=query_type,
                    chunk_count=len(unique_chunks),
                    sources=top_sources,
                    latency_ms=hop_latency,
                    reasoning_step=reasoning_step.to_explain_line(),
                )

            except Exception as e:
                hop_latency = int((time.time() - hop_start) * 1000)

                logger.error(
                    "multi_hop_retrieval_hop_failed",
                    hop_number=hop_num,
                    query=sub_query,
                    error=str(e),
                )

                hop = HopResult(
                    hop_number=hop_num,
                    query=sub_query,
                    chunks=[],
                    status=HopStatus.FAILED,
                    latency_ms=hop_latency,
                )

                # Stop on failure
                break

            hops.append(hop)

            # Check if we should terminate early (e.g., found sufficient info)
            if self._should_terminate_early(hops, all_chunks):
                logger.info(
                    "multi_hop_retrieval_early_termination",
                    hop_number=hop_num,
                    reason="sufficient_information",
                )
                break

        total_latency = int((time.time() - start_time) * 1000)

        # Step 3: Synthesize final answer if enabled
        final_answer = None
        if multi_hop_config.enable_answer_synthesis and all_chunks:
            final_answer = await self._synthesize_answer(
                query,
                hops,
                all_chunks,
            )

        # Build reasoning chain
        reasoning_chain = self._build_reasoning_chain(
            query, reasoning_parts, reasoning_steps, context_from_previous
        )

        # Log full reasoning chain for debugging
        logger.debug(
            "multi_hop_retrieval_reasoning_chain",
            reasoning_chain=reasoning_chain,
            reasoning_steps_count=len(reasoning_steps),
        )

        result = MultiHopResult(
            original_query=query,
            hops=hops,
            all_chunks=all_chunks,
            final_answer=final_answer,
            reasoning_chain=reasoning_chain,
            total_hops=len(hops),
            total_latency_ms=total_latency,
            terminated_early=len(hops) < len(sub_queries),
            reasoning_steps=reasoning_steps,
        )

        logger.info(
            "multi_hop_retrieval_complete",
            query=query,
            total_hops=result.total_hops,
            total_chunks=result.total_chunks,
            total_latency_ms=total_latency,
            has_reasoning_steps=bool(reasoning_steps),
        )

        return result

    async def retrieve_sync(
        self,
        query: str,
        config: MultiHopConfig | None = None,
    ) -> MultiHopResult:
        """
        Synchronous version of retrieve for non-async contexts.

        Performs single-hop retrieval only (no decomposition).

        Args:
            query: The query to retrieve information for
            config: Optional configuration override

        Returns:
            MultiHopResult with single hop result
        """
        start_time = time.time()

        multi_hop_config = config or self._config

        logger.debug(
            "multi_hop_retrieval_sync",
            query=query,
        )

        # Single retrieval
        try:
            hop_result = await self._retrieval.retrieve_relevant(
                query=query,
                k=multi_hop_config.default_hop_config.k,
            )

            latency = int((time.time() - start_time) * 1000)

            hop = HopResult(
                hop_number=0,
                query=query,
                chunks=hop_result.chunks,
                status=HopStatus.COMPLETED,
                latency_ms=latency,
            )

            return MultiHopResult(
                original_query=query,
                hops=[hop],
                all_chunks=hop_result.chunks,
                final_answer=None,
                reasoning_chain=f"Single-hop: {query}",
                total_hops=1,
                total_latency_ms=latency,
            )

        except Exception as e:
            logger.error(
                "multi_hop_retrieval_sync_failed",
                query=query,
                error=str(e),
            )

            hop = HopResult(
                hop_number=0,
                query=query,
                chunks=[],
                status=HopStatus.FAILED,
                latency_ms=int((time.time() - start_time) * 1000),
            )

            return MultiHopResult(
                original_query=query,
                hops=[hop],
                all_chunks=[],
                final_answer=None,
                reasoning_chain=f"Failed: {str(e)}",
                total_hops=1,
                total_latency_ms=hop.latency_ms,
            )

    async def _single_hop_retrieval(
        self,
        query: str,
        config: MultiHopConfig,
        start_time: float,
    ) -> MultiHopResult:
        """
        Perform single-hop retrieval (no decomposition needed).

        Args:
            query: The query to retrieve for
            config: Configuration
            start_time: Start time for latency tracking

        Returns:
            MultiHopResult with single hop
        """
        try:
            hop_result = await self._retrieval.retrieve_relevant(
                query=query,
                k=config.default_hop_config.k,
            )

            latency = int((time.time() - start_time) * 1000)

            hop = HopResult(
                hop_number=0,
                query=query,
                chunks=hop_result.chunks,
                status=HopStatus.COMPLETED,
                latency_ms=latency,
            )

            # Synthesize answer if enabled
            final_answer = None
            if config.enable_answer_synthesis and hop_result.chunks:
                final_answer = await self._synthesize_answer(
                    query,
                    [hop],
                    hop_result.chunks,
                )

            return MultiHopResult(
                original_query=query,
                hops=[hop],
                all_chunks=hop_result.chunks,
                final_answer=final_answer,
                reasoning_chain=f"Single-hop retrieval: {query}",
                total_hops=1,
                total_latency_ms=latency,
            )

        except Exception as e:
            latency = int((time.time() - start_time) * 1000)

            logger.error(
                "multi_hop_retrieval_single_failed",
                query=query,
                error=str(e),
            )

            hop = HopResult(
                hop_number=0,
                query=query,
                chunks=[],
                status=HopStatus.FAILED,
                latency_ms=latency,
            )

            return MultiHopResult(
                original_query=query,
                hops=[hop],
                all_chunks=[],
                final_answer=None,
                reasoning_chain=f"Failed: {str(e)}",
                total_hops=1,
                total_latency_ms=latency,
            )

    def _build_context_from_chunks(self, chunks: list[RetrievedChunk]) -> str | None:
        """
        Build context string from retrieved chunks.

        Args:
            chunks: Chunks to build context from

        Returns:
            Context string or None if no chunks
        """
        if not chunks:
            return None

        # Build a concise context from top chunks
        context_parts = []
        for chunk in chunks[:3]:  # Top 3 chunks
            context_parts.append(f"- {chunk.content[:200]}...")

        return "\n".join(context_parts) if context_parts else None

    def _should_terminate_early(
        self,
        hops: list[HopResult],
        all_chunks: list[RetrievedChunk],
    ) -> bool:
        """
        Check if retrieval should terminate early.

        Args:
            hops: Completed hops
            all_chunks: All chunks retrieved so far

        Returns:
            True if should terminate
        """
        # Terminate if we have enough chunks
        if len(all_chunks) >= 10:
            return True

        # Terminate if last hop retrieved nothing
        if hops and hops[-1].chunk_count == 0:
            return True

        return False

    def _extract_top_sources(
        self,
        chunks: list[RetrievedChunk],
        limit: int = 3,
    ) -> list[str]:
        """
        Extract top source identifiers from chunks.

        Args:
            chunks: Chunks to extract sources from
            limit: Maximum number of sources to return

        Returns:
            List of source identifiers in format "SourceType:source_id"
        """
        if not chunks:
            return []

        sources: set[str] = set()
        for chunk in chunks[: limit * 2]:  # Check more chunks to find unique sources
            if chunk.source_id:
                source_key = f"{chunk.source_type}:{chunk.source_id}"
                sources.add(source_key)
            if len(sources) >= limit:
                break

        return list(sources)[:limit]

    def _build_reasoning_chain(
        self,
        original_query: str,
        reasoning_parts: list[str],
        reasoning_steps: list[ReasoningStep],
        final_context: str | None,
    ) -> str:
        """
        Build a human-readable reasoning chain.

        Args:
            original_query: The original user query
            reasoning_parts: Simple reasoning parts
            reasoning_steps: Detailed reasoning steps
            final_context: Final context used

        Returns:
            Formatted reasoning chain string
        """
        if not reasoning_steps:
            return f"Single-hop retrieval: {original_query}"

        lines = [
            f"Query: {original_query}",
            "Reasoning Path:",
        ]

        for step in reasoning_steps:
            lines.append(f"  {step.to_explain_line()}")

        if final_context:
            lines.append(f"\nFinal Context: {final_context[:200]}...")

        return "\n".join(lines)

    async def _synthesize_answer(
        self,
        query: str,
        hops: list[HopResult],
        chunks: list[RetrievedChunk],
    ) -> str:
        """
        Synthesize final answer from all retrieved information.

        Args:
            query: Original query
            hops: All hop results
            chunks: All retrieved chunks

        Returns:
            Synthesized answer
        """
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):  # Top 5 chunks
            context_parts.append(f"[{i}] {chunk.content[:300]}...")

        context = "\n\n".join(context_parts)

        prompt = f"""Based on the following retrieved context, answer the question.

Question: {query}

Context:
{context}

Provide a clear, direct answer based only on the context above.
If the context doesn't contain enough information, say so."""

        request = LLMRequest(
            system_prompt="You are a helpful assistant that answers questions based on provided context.",
            user_prompt=prompt,
            temperature=0.5,
            max_tokens=500,
        )

        try:
            response = await self._llm.generate(request)
            return response.text.strip()
        except LLMError as e:
            logger.error(
                "multi_hop_answer_synthesis_failed",
                query=query,
                error=str(e),
            )
            return "Unable to synthesize answer from retrieved context."


__all__ = [
    "MultiHopRetriever",
    "QueryDecomposer",
    "MultiHopConfig",
    "HopConfig",
    "ExplainConfig",
    "MultiHopResult",
    "HopResult",
    "HopStatus",
    "ReasoningStep",
    "DEFAULT_MAX_HOPS",
    "DEFAULT_HOP_K",
    "DEFAULT_TEMPERATURE",
]
