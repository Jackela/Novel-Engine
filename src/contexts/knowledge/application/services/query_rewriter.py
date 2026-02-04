"""
Query Rewriter Service

Improves RAG retrieval by rewriting user queries into multiple variants.
Uses LLM-based strategies to expand queries with synonyms, related terms,
and sub-query decomposition for better semantic matching.

Constitution Compliance:
- Article II (Hexagonal): Application service using LLM port
- Article V (SOLID): SRP - query rewriting only

Warzone 4: AI Brain - BRAIN-009A
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_llm_client import ILLMClient, LLMRequest, LLMError

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


# Strategy enumeration
class RewriteStrategy(str, Enum):
    """
    Query rewriting strategies.

    Strategies:
        SYNONYM: Expand query with synonyms and related terms
        DECOMPOSE: Break complex query into sub-queries
        HYBRID: Combination of synonym expansion and decomposition
    """

    SYNONYM = "synonym"
    DECOMPOSE = "decompose"
    HYBRID = "hybrid"


# Default configuration
DEFAULT_STRATEGY = RewriteStrategy.SYNONYM
DEFAULT_TEMPERATURE = 0.3  # Lower for more deterministic rewrites
DEFAULT_MAX_VARIANTS = 3
DEFAULT_INCLUDE_ORIGINAL = True


@dataclass(frozen=True, slots=True)
class RewriteConfig:
    """
    Configuration for query rewriting.

    Why frozen:
        Immutable snapshot ensures configuration doesn't change during processing.

    Attributes:
        strategy: Rewriting strategy to use
        max_variants: Maximum number of query variants to generate
        include_original: Whether to include the original query in results
        temperature: LLM temperature for rewrite generation
    """

    strategy: RewriteStrategy = DEFAULT_STRATEGY
    max_variants: int = DEFAULT_MAX_VARIANTS
    include_original: bool = DEFAULT_INCLUDE_ORIGINAL
    temperature: float = DEFAULT_TEMPERATURE

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.max_variants < 1:
            raise ValueError("max_variants must be at least 1")
        if self.max_variants > 10:
            raise ValueError("max_variants must not exceed 10")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")


@dataclass(frozen=True, slots=True)
class RewriteResult:
    """
    Result of query rewriting.

    Attributes:
        original_query: The original input query
        variants: List of query variants (including original if configured)
        strategy: Strategy used for rewriting
        cached: Whether the result was retrieved from cache
    """

    original_query: str
    variants: list[str]
    strategy: RewriteStrategy
    cached: bool = False


@dataclass
class QueryRewriterCacheEntry:
    """
    Cache entry for rewritten queries.

    Attributes:
        variants: Cached query variants
        strategy: Strategy used for rewriting
    """

    variants: list[str]
    strategy: RewriteStrategy


class QueryRewriter:
    """
    Service for rewriting queries to improve RAG retrieval.

    Uses LLM-based strategies to transform user queries into multiple variants:
    - Synonym expansion: Add related terms and synonyms
    - Sub-query decomposition: Break complex queries into simpler parts
    - Hybrid: Combine both approaches

    Includes caching to avoid redundant LLM calls for similar queries.

    Constitution Compliance:
        - Article II (Hexagonal): Application service using LLM port
        - Article V (SOLID): SRP - query rewriting only

    Example:
        >>> rewriter = QueryRewriter(llm_client=gemini_client)
        >>> result = await rewriter.rewrite("protagonist motivation")
        >>> print(result.variants)
        ["protagonist motivation", "main character goals", "hero driving forces"]
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        default_config: RewriteConfig | None = None,
        cache_enabled: bool = True,
    ):
        """
        Initialize the query rewriter.

        Args:
            llm_client: LLM client for generating query variants
            default_config: Default configuration for rewrites
            cache_enabled: Whether to cache rewrite results
        """
        self._llm = llm_client
        self._config = default_config or RewriteConfig()
        self._cache_enabled = cache_enabled
        self._cache: dict[str, QueryRewriterCacheEntry] = {}

        logger.info(
            "query_rewriter_initialized",
            strategy=self._config.strategy.value,
            max_variants=self._config.max_variants,
            cache_enabled=cache_enabled,
        )

    async def rewrite(
        self,
        query: str,
        config: RewriteConfig | None = None,
    ) -> RewriteResult:
        """
        Rewrite a query into multiple variants.

        Args:
            query: The original query to rewrite
            config: Optional configuration override

        Returns:
            RewriteResult with original and variant queries

        Raises:
            ValueError: If query is empty
            LLMError: If LLM generation fails

        Example:
            >>> result = await rewriter.rewrite("brave warrior")
            >>> print(result.variants)
            ["brave warrior", "courageous fighter", "heroic soldier"]
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        # Use provided config or defaults
        rewrite_config = config or self._config

        # Check cache first
        if self._cache_enabled:
            cached = self._get_from_cache(query, rewrite_config.strategy)
            if cached:
                logger.debug(
                    "query_rewrite_cache_hit",
                    query=query,
                    strategy=rewrite_config.strategy.value,
                )
                return RewriteResult(
                    original_query=query,
                    variants=self._build_result_variants(query, cached.variants, rewrite_config),
                    strategy=rewrite_config.strategy,
                    cached=True,
                )

        logger.debug(
            "query_rewrite_start",
            query=query,
            strategy=rewrite_config.strategy.value,
        )

        # Generate variants based on strategy
        try:
            variants = await self._generate_variants(query, rewrite_config)
        except LLMError as e:
            logger.error(
                "query_rewrite_llm_failed",
                query=query,
                error=str(e),
            )
            # Return original query on failure
            return RewriteResult(
                original_query=query,
                variants=[query] if rewrite_config.include_original else [],
                strategy=rewrite_config.strategy,
                cached=False,
            )

        # Cache the results
        if self._cache_enabled:
            self._add_to_cache(query, variants, rewrite_config.strategy)

        result_variants = self._build_result_variants(query, variants, rewrite_config)

        logger.info(
            "query_rewrite_complete",
            query=query,
            strategy=rewrite_config.strategy.value,
            variant_count=len(result_variants),
        )

        return RewriteResult(
            original_query=query,
            variants=result_variants,
            strategy=rewrite_config.strategy,
            cached=False,
        )

    def rewrite_sync(
        self,
        query: str,
        config: RewriteConfig | None = None,
    ) -> RewriteResult:
        """
        Synchronous version of rewrite for non-async contexts.

        Uses mock/fallback behavior without LLM calls.
        Only returns original query with basic modifications.

        Args:
            query: The original query
            config: Optional configuration override

        Returns:
            RewriteResult with basic query variants
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        rewrite_config = config or self._config

        # Simple rule-based variants
        variants = self._generate_simple_variants(query, rewrite_config)

        return RewriteResult(
            original_query=query,
            variants=variants,
            strategy=rewrite_config.strategy,
            cached=False,
        )

    def clear_cache(self) -> None:
        """Clear the rewrite cache."""
        self._cache.clear()
        logger.debug("query_rewrite_cache_cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache size and related stats
        """
        return {
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
        }

    async def _generate_variants(
        self,
        query: str,
        config: RewriteConfig,
    ) -> list[str]:
        """
        Generate query variants using LLM.

        Args:
            query: Original query
            config: Rewrite configuration

        Returns:
            List of query variants
        """
        prompt = self._build_prompt(query, config)

        request = LLMRequest(
            system_prompt=self._get_system_prompt(config.strategy),
            user_prompt=prompt,
            temperature=config.temperature,
            max_tokens=500,
        )

        response = await self._llm.generate(request)
        return self._parse_response(response.text, config.max_variants)

    def _get_system_prompt(self, strategy: RewriteStrategy) -> str:
        """
        Get system prompt for the given strategy.

        Args:
            strategy: Rewrite strategy

        Returns:
            System instruction prompt
        """
        if strategy == RewriteStrategy.SYNONYM:
            return """You are an expert at query expansion for information retrieval.
Your task is to rewrite user queries to improve search results by adding synonyms,
related terms, and alternative phrasings.

Guidelines:
- Preserve the core meaning of the original query
- Use terms that would appear in relevant documents
- Return valid JSON array of strings
- Generate 2-5 alternative queries"""
        elif strategy == RewriteStrategy.DECOMPOSE:
            return """You are an expert at breaking complex queries into simpler sub-queries.
Your task is to decompose user queries into focused parts that can be searched separately.

Guidelines:
- Each sub-query should capture one aspect of the original
- Sub-queries should be independently searchable
- Return valid JSON array of strings
- Generate 2-4 sub-queries"""
        else:  # HYBRID
            return """You are an expert at query optimization for information retrieval.
Your task is to both expand queries with synonyms AND decompose complex queries into parts.

Guidelines:
- Mix expanded phrasings and decomposed sub-queries
- Preserve the core meaning throughout
- Return valid JSON array of strings
- Generate 3-5 alternative queries"""

    def _build_prompt(self, query: str, config: RewriteConfig) -> str:
        """
        Build the user prompt for query rewriting.

        Args:
            query: Original query
            config: Rewrite configuration

        Returns:
            Formatted prompt for LLM
        """
        return f"""Original query: "{query}"

Generate {config.max_variants} alternative queries that would improve search retrieval.
Return ONLY a valid JSON array of strings, like this:
["alternative 1", "alternative 2", "alternative 3"]"""

    def _parse_response(self, text: str, max_variants: int) -> list[str]:
        """
        Parse LLM response to extract query variants.

        Args:
            text: LLM response text
            max_variants: Maximum variants to return

        Returns:
            List of parsed query variants
        """
        # Try to parse as JSON array
        try:
            # Extract JSON from response (might be in markdown)
            clean_text = text.strip()
            if clean_text.startswith("```"):
                # Remove markdown code block
                lines = clean_text.split("\n")
                clean_text = "\n".join(lines[1:-1])

            variants = json.loads(clean_text)

            if isinstance(variants, list):
                # Ensure all items are strings
                result = [str(v).strip() for v in variants if v]
                return result[:max_variants]

        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning(
                "query_rewrite_json_parse_failed",
                response=text[:200],
            )

        # Fallback: split by newlines and commas
        result = []
        for line in text.split("\n"):
            line = line.strip()
            # Remove common prefixes
            for prefix in ['"-', "* ", "• ", "- ", "1. ", "2. ", "3. "]:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip('"').strip()
                    break
            if line and len(line) > 2:
                result.append(line)

        return result[:max_variants]

    def _generate_simple_variants(
        self,
        query: str,
        config: RewriteConfig,
    ) -> list[str]:
        """
        Generate simple rule-based variants (fallback).

        Args:
            query: Original query
            config: Rewrite configuration

        Returns:
            List of basic query variants
        """
        variants = []

        if config.include_original:
            variants.append(query)

        # Simple word substitutions
        substitutions = {
            "protagonist": ["main character", "hero", "lead character"],
            "warrior": ["fighter", "soldier", "combatant"],
            "brave": ["courageous", "fearless", "heroic"],
            "villain": ["antagonist", "enemy", "opponent"],
            "king": ["monarch", "ruler", "sovereign"],
        }

        for word, replacements in substitutions.items():
            if word.lower() in query.lower():
                for replacement in replacements[:1]:  # One replacement per word
                    variant = query.lower().replace(word, replacement)
                    if variant not in variants:
                        variants.append(variant)

        return variants[: config.max_variants + (1 if config.include_original else 0)]

    def _build_result_variants(
        self,
        original: str,
        generated: list[str],
        config: RewriteConfig,
    ) -> list[str]:
        """
        Build final variant list including original if configured.

        Args:
            original: Original query
            generated: Generated variants
            config: Rewrite configuration

        Returns:
            Final list of variants
        """
        variants = []

        if config.include_original:
            variants.append(original)

        # Add generated variants, avoiding duplicates
        for variant in generated:
            if variant.lower() != original.lower() and variant not in variants:
                variants.append(variant)

        # Limit to max_variants + (1 if including original)
        max_results = config.max_variants + (1 if config.include_original else 0)
        return variants[:max_results]

    def _get_from_cache(
        self,
        query: str,
        strategy: RewriteStrategy,
    ) -> QueryRewriterCacheEntry | None:
        """
        Get cached rewrite results.

        Args:
            query: Original query
            strategy: Rewrite strategy

        Returns:
            Cached entry if found, None otherwise
        """
        cache_key = self._make_cache_key(query, strategy)
        return self._cache.get(cache_key)

    def _add_to_cache(
        self,
        query: str,
        variants: list[str],
        strategy: RewriteStrategy,
    ) -> None:
        """
        Add rewrite results to cache.

        Args:
            query: Original query
            variants: Generated variants
            strategy: Rewrite strategy used
        """
        cache_key = self._make_cache_key(query, strategy)
        self._cache[cache_key] = QueryRewriterCacheEntry(
            variants=variants,
            strategy=strategy,
        )

    def _make_cache_key(self, query: str, strategy: RewriteStrategy) -> str:
        """
        Create cache key for query and strategy.

        Args:
            query: Original query
            strategy: Rewrite strategy

        Returns:
            Cache key string
        """
        return f"{strategy.value}:{query.lower().strip()}"


__all__ = [
    "QueryRewriter",
    "RewriteStrategy",
    "RewriteConfig",
    "RewriteResult",
    "DEFAULT_STRATEGY",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_VARIANTS",
    "DEFAULT_INCLUDE_ORIGINAL",
]
