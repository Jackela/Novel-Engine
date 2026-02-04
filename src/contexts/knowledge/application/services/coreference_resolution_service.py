"""
Co-reference Resolution Service

Resolves pronouns and references to their canonical entity names.
Enables proper entity tracking across narrative text by identifying
when "he", "she", "it", etc. refer to specific named entities.

Constitution Compliance:
- Article II (Hexagonal): Application service using LLM port
- Article V (SOLID): SRP - co-reference resolution only

Warzone 4: AI Brain - BRAIN-029B
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from ...application.ports.i_llm_client import ILLMClient, LLMRequest, LLMError
from ...domain.models.entity import (
    ExtractedEntity,
    EntityMention,
    ExtractionResult,
    PRONOUNS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = structlog.get_logger()


# Configuration constants
DEFAULT_COREF_TEMPERATURE = 0.2  # Very low for deterministic resolution
DEFAULT_COREF_MAX_TOKENS = 1500
DEFAULT_MAX_REFERENCES = 50
DEFAULT_WINDOW_SIZE = 500  # Characters to look back for context


@dataclass(frozen=True, slots=True)
class CoreferenceConfig:
    """
    Configuration for co-reference resolution.

    Why frozen:
        Immutable snapshot ensures configuration doesn't change during processing.

    Attributes:
        window_size: Characters to look back for entity context
        max_references: Maximum number of references to resolve
        temperature: LLM temperature for resolution (lower = more deterministic)
        max_tokens: Maximum tokens in LLM response
        use_llm_fallback: Whether to use LLM when heuristics fail
    """

    window_size: int = DEFAULT_WINDOW_SIZE
    max_references: int = DEFAULT_MAX_REFERENCES
    temperature: float = DEFAULT_COREF_TEMPERATURE
    max_tokens: int = DEFAULT_COREF_MAX_TOKENS
    use_llm_fallback: bool = True

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.window_size < 100:
            raise ValueError("window_size must be at least 100")
        if self.max_references < 1:
            raise ValueError("max_references must be at least 1")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """
    A resolved co-reference mapping.

    Attributes:
        mention_text: The pronoun or reference text (e.g., "he", "she")
        entity_name: The resolved entity name (e.g., "Alice")
        start_pos: Position where the reference appears
        end_pos: Position where the reference ends
        confidence: Confidence score for the resolution (0.0-1.0)
        resolution_method: How the reference was resolved (heuristic, llm, explicit)
    """

    mention_text: str
    entity_name: str
    start_pos: int
    end_pos: int
    confidence: float
    resolution_method: str  # "heuristic", "llm", "explicit"

    def __post_init__(self) -> None:
        """Validate resolved reference data."""
        if not self.mention_text or not self.mention_text.strip():
            raise ValueError("mention_text must not be empty")
        if not self.entity_name or not self.entity_name.strip():
            raise ValueError("entity_name must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.start_pos < 0:
            raise ValueError("start_pos must be non-negative")
        if self.end_pos < self.start_pos:
            raise ValueError("end_pos must be >= start_pos")


@dataclass(frozen=True, slots=True)
class CoreferenceResult:
    """
    Result of co-reference resolution.

    Attributes:
        resolved_references: List of resolved references
        unresolved_mentions: Mentions that could not be resolved
        resolution_rate: Percentage of mentions successfully resolved
        method_counts: Count of resolutions by method
    """

    resolved_references: tuple[ResolvedReference, ...]
    unresolved_mentions: tuple[EntityMention, ...]
    resolution_rate: float
    method_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_resolved(self) -> int:
        """Total number of references resolved."""
        return len(self.resolved_references)

    @property
    def total_unresolved(self) -> int:
        """Total number of mentions that could not be resolved."""
        return len(self.unresolved_mentions)


class CoreferenceResolutionError(Exception):
    """Base exception for co-reference resolution errors."""

    pass


class CoreferenceResolutionService:
    """
    Service for resolving co-references in narrative text.

    Uses a hybrid approach:
    1. Heuristic-based resolution for common patterns
    2. LLM-based resolution for ambiguous cases
    3. Explicit mention mapping from extraction results

    Example:
        >>> service = CoreferenceResolutionService(llm_client=client)
        >>> result = await service.resolve(extraction_result)
        >>> for ref in result.resolved_references:
        ...     print(f"{ref.mention_text} -> {ref.entity_name}")
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        config: CoreferenceConfig | None = None,
    ) -> None:
        """
        Initialize the CoreferenceResolutionService.

        Args:
            llm_client: LLM client for resolution
            config: Resolution configuration (uses defaults if None)
        """
        self._llm_client = llm_client
        self._config = config or CoreferenceConfig()
        self._logger = logger.bind(service="coreference_resolution")

    def _find_candidate_entities(
        self,
        entities: tuple[ExtractedEntity, ...],
        position: int,
        text: str,
    ) -> list[tuple[ExtractedEntity, int]]:
        """
        Find candidate entities that could be referenced near a position.

        Args:
            entities: All extracted entities
            position: Position in text to find nearby entities
            text: Full source text

        Returns:
            List of (entity, distance) tuples sorted by proximity
        """
        candidates: list[tuple[ExtractedEntity, int]] = []

        for entity in entities:
            # Check if entity appears before this position
            if entity.first_appearance < position:
                distance = position - entity.first_appearance
                # Only consider entities within the window
                if distance <= self._config.window_size:
                    candidates.append((entity, distance))

        # Sort by proximity (closer entities are more likely)
        candidates.sort(key=lambda x: x[1])
        return candidates

    def _resolve_pronoun_heuristic(
        self,
        mention_text: str,
        candidates: list[tuple[ExtractedEntity, int]],
    ) -> tuple[str | None, float]:
        """
        Resolve a pronoun using heuristic rules.

        Args:
            mention_text: The pronoun text
            candidates: List of candidate entities with distances

        Returns:
            Tuple of (resolved_entity_name, confidence) or (None, 0.0)
        """
        pronoun_lower = mention_text.lower().strip()

        # Subject pronouns preference: most recently mentioned entity
        if pronoun_lower in {"he", "she", "it", "they"}:
            if candidates:
                entity, distance = candidates[0]
                # Higher confidence for closer references
                confidence = max(0.5, 1.0 - (distance / self._config.window_size))
                return entity.name, confidence

        # Object pronouns: also prefer most recent
        if pronoun_lower in {"him", "her", "them", "it"}:
            if candidates:
                entity, distance = candidates[0]
                confidence = max(0.5, 1.0 - (distance / self._config.window_size))
                return entity.name, confidence

        # Possessive pronouns: most recently mentioned entity
        if pronoun_lower in {"his", "hers", "its", "theirs"}:
            if candidates:
                entity, distance = candidates[0]
                confidence = max(0.5, 1.0 - (distance / self._config.window_size))
                return entity.name, confidence

        return None, 0.0

    def _get_gender_from_name(self, name: str) -> str | None:
        """
        Infer gender from entity name (simple heuristic).

        Args:
            name: Entity name to analyze

        Returns:
            "masculine", "feminine", "neutral", or None
        """
        name_lower = name.lower()

        # Common masculine patterns
        masculine_endings = ("o", "er", "or", "is", "us", "ander", "ard")
        if name_lower.endswith(masculine_endings):
            return "masculine"

        # Common feminine patterns
        feminine_endings = ("a", "ia", "ette", "elle", "ine", "en", "yn")
        if name_lower.endswith(feminine_endings):
            return "feminine"

        # Neutral patterns (groups, organizations, locations)
        neutral_patterns = (
            "guild", "army", "order", "company", "tavern", "inn",
            "kingdom", "empire", "forest", "mountain", "river"
        )
        if any(p in name_lower for p in neutral_patterns):
            return "neutral"

        return None

    def _filter_candidates_by_pronoun(
        self,
        candidates: list[tuple[ExtractedEntity, int]],
        pronoun: str,
    ) -> list[tuple[ExtractedEntity, int]]:
        """
        Filter candidates based on pronoun gender agreement.

        Args:
            candidates: List of candidate entities
            pronoun: The pronoun being resolved

        Returns:
            Filtered list of candidates
        """
        pronoun_lower = pronoun.lower()

        # Skip filtering for neutral/unknown pronouns
        if pronoun_lower not in {"he", "him", "his", "she", "her", "hers"}:
            return candidates

        # Determine pronoun gender
        if pronoun_lower in {"he", "him", "his"}:
            pronoun_gender = "masculine"
        elif pronoun_lower in {"she", "her", "hers"}:
            pronoun_gender = "feminine"
        else:
            return candidates

        # Filter candidates by gender
        filtered = []
        for entity, distance in candidates:
            entity_gender = self._get_gender_from_name(entity.name)
            if entity_gender is None or entity_gender == pronoun_gender or entity_gender == "neutral":
                filtered.append((entity, distance))

        return filtered if filtered else candidates

    async def _resolve_with_llm(
        self,
        text: str,
        mention: EntityMention,
        entities: tuple[ExtractedEntity, ...],
    ) -> tuple[str | None, float]:
        """
        Resolve a reference using LLM when heuristics fail.

        Args:
            text: Full source text
            mention: The mention to resolve
            entities: Available entities

        Returns:
            Tuple of (resolved_entity_name, confidence) or (None, 0.0)
        """
        # Build context window around mention
        window_start = max(0, mention.start_pos - 200)
        window_end = min(len(text), mention.end_pos + 100)
        context = text[window_start:window_end]

        # Build entity list for context
        entity_list = "\n".join(
            f"- {e.name} ({e.entity_type.value})"
            for e in entities[:20]  # Limit to avoid token overflow
        )

        system_prompt = """You are an expert at understanding narrative text and resolving co-references.

Given a text excerpt with entities and a pronoun/reference, determine which entity the reference refers to.

Respond with ONLY valid JSON in this format:
{
  "entity_name": "Name of the entity",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}

Rules:
- Choose the most recently mentioned entity that matches the reference
- Consider gender agreement (he/him -> masculine, she/her -> feminine)
- Consider context and semantic clues
- If unsure, choose the closest previous entity mention
- Return null for entity_name if truly ambiguous"""

        user_prompt = f"""Context (available entities):
{entity_list}

Text excerpt:
\"\"\"
{context}
\"\"\"

The reference "{mention.mention_text}" at position {mention.start_pos} refers to which entity?

Respond with ONLY valid JSON."""

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )

        try:
            response = await self._llm_client.generate(request)
            result = self._parse_llm_response(response.text)

            entity_name = result.get("entity_name")
            confidence_value = result.get("confidence", 0.5)

            if entity_name and isinstance(entity_name, str):
                confidence = (
                    float(confidence_value) if isinstance(confidence_value, (int, float)) else 0.5
                )
                return entity_name, min(1.0, max(0.0, confidence))

        except (LLMError, json.JSONDecodeError, KeyError) as e:
            self._logger.warning(
                "llm_resolution_failed",
                error=str(e),
                mention_text=mention.mention_text,
            )

        return None, 0.0

    def _parse_llm_response(self, response_text: str) -> dict[str, object]:
        """
        Parse LLM response into structured data.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Parsed JSON dictionary
        """
        cleaned = response_text.strip()

        # Find JSON block if embedded in markdown
        if "```json" in cleaned:
            start = cleaned.find("```json") + 7
            end = cleaned.find("```", start)
            if end != -1:
                cleaned = cleaned[start:end].strip()
        elif "```" in cleaned:
            start = cleaned.find("```") + 3
            end = cleaned.find("```", start)
            if end != -1:
                cleaned = cleaned[start:end].strip()

        # Handle null response
        if cleaned.lower() == "null":
            return {"entity_name": None, "confidence": 0.0}

        parsed: dict[str, object] = json.loads(cleaned)
        return parsed

    async def resolve(
        self,
        extraction_result: ExtractionResult,
        config: CoreferenceConfig | None = None,
    ) -> CoreferenceResult:
        """
        Resolve co-references in an extraction result.

        Args:
            extraction_result: Result from entity extraction
            config: Optional override configuration

        Returns:
            CoreferenceResult with resolved and unresolved references
        """
        effective_config = config or self._config
        text = ""  # We'll need to reconstruct or access original text

        self._logger.info(
            "starting_coreference_resolution",
            entity_count=extraction_result.entity_count,
            mention_count=extraction_result.mention_count,
        )

        resolved: list[ResolvedReference] = []
        unresolved: list[EntityMention] = []
        method_counts: dict[str, int] = {"heuristic": 0, "llm": 0, "explicit": 0}

        # Process pronoun mentions
        pronoun_mentions = [
            m for m in extraction_result.mentions
            if m.is_pronoun or m.mention_text.lower().strip() in PRONOUNS
        ]

        for mention in pronoun_mentions[:effective_config.max_references]:
            # Get candidates
            candidates = self._find_candidate_entities(
                extraction_result.entities,
                mention.start_pos,
                text,
            )

            # Filter by pronoun gender
            candidates = self._filter_candidates_by_pronoun(
                candidates,
                mention.mention_text,
            )

            entity_name: str | None = None
            confidence: float = 0.0
            method: str = "heuristic"

            # Try heuristic first
            if candidates:
                entity_name, confidence = self._resolve_pronoun_heuristic(
                    mention.mention_text,
                    candidates,
                )

            # Fall back to LLM if configured and heuristic failed
            if entity_name is None and effective_config.use_llm_fallback:
                entity_name, confidence = await self._resolve_with_llm(
                    text,
                    mention,
                    extraction_result.entities,
                )
                method = "llm"

            # Record result
            if entity_name:
                resolved.append(ResolvedReference(
                    mention_text=mention.mention_text,
                    entity_name=entity_name,
                    start_pos=mention.start_pos,
                    end_pos=mention.end_pos,
                    confidence=confidence,
                    resolution_method=method,
                ))
                method_counts[method] += 1
            else:
                unresolved.append(mention)

        # Calculate resolution rate
        total_pronouns = len(pronoun_mentions)
        resolution_rate = (
            len(resolved) / total_pronouns
            if total_pronouns > 0
            else 1.0
        )

        result = CoreferenceResult(
            resolved_references=tuple(resolved),
            unresolved_mentions=tuple(unresolved),
            resolution_rate=resolution_rate,
            method_counts=method_counts,
        )

        self._logger.info(
            "coreference_resolution_complete",
            total_resolved=result.total_resolved,
            total_unresolved=result.total_unresolved,
            resolution_rate=resolution_rate,
        )

        return result

    async def resolve_with_text(
        self,
        text: str,
        entities: tuple[ExtractedEntity, ...],
        mentions: tuple[EntityMention, ...],
        config: CoreferenceConfig | None = None,
    ) -> CoreferenceResult:
        """
        Resolve co-references with explicit text and extracted data.

        Args:
            text: Original source text
            entities: Extracted entities
            mentions: Extracted mentions
            config: Optional override configuration

        Returns:
            CoreferenceResult with resolved and unresolved references
        """
        effective_config = config or self._config

        self._logger.info(
            "starting_coreference_resolution_with_text",
            entity_count=len(entities),
            mention_count=len(mentions),
        )

        resolved: list[ResolvedReference] = []
        unresolved: list[EntityMention] = []
        method_counts: dict[str, int] = {"heuristic": 0, "llm": 0, "explicit": 0}

        # Process pronoun mentions
        pronoun_mentions = [
            m for m in mentions
            if m.is_pronoun or m.mention_text.lower().strip() in PRONOUNS
        ]

        for mention in pronoun_mentions[:effective_config.max_references]:
            # Get candidates
            candidates = self._find_candidate_entities(
                entities,
                mention.start_pos,
                text,
            )

            # Filter by pronoun gender
            candidates = self._filter_candidates_by_pronoun(
                candidates,
                mention.mention_text,
            )

            entity_name: str | None = None
            confidence: float = 0.0
            method: str = "heuristic"

            # Try heuristic first
            if candidates:
                entity_name, confidence = self._resolve_pronoun_heuristic(
                    mention.mention_text,
                    candidates,
                )

            # Fall back to LLM if configured and heuristic failed
            if entity_name is None and effective_config.use_llm_fallback:
                entity_name, confidence = await self._resolve_with_llm(
                    text,
                    mention,
                    entities,
                )
                method = "llm"

            # Record result
            if entity_name:
                resolved.append(ResolvedReference(
                    mention_text=mention.mention_text,
                    entity_name=entity_name,
                    start_pos=mention.start_pos,
                    end_pos=mention.end_pos,
                    confidence=confidence,
                    resolution_method=method,
                ))
                method_counts[method] += 1
            else:
                unresolved.append(mention)

        # Calculate resolution rate
        total_pronouns = len(pronoun_mentions)
        resolution_rate = (
            len(resolved) / total_pronouns
            if total_pronouns > 0
            else 1.0
        )

        result = CoreferenceResult(
            resolved_references=tuple(resolved),
            unresolved_mentions=tuple(unresolved),
            resolution_rate=resolution_rate,
            method_counts=method_counts,
        )

        self._logger.info(
            "coreference_resolution_complete",
            total_resolved=result.total_resolved,
            total_unresolved=result.total_unresolved,
            resolution_rate=resolution_rate,
        )

        return result

    async def resolve_batch(
        self,
        texts: Sequence[str],
        entities_list: Sequence[tuple[ExtractedEntity, ...]],
        mentions_list: Sequence[tuple[EntityMention, ...]],
        config: CoreferenceConfig | None = None,
    ) -> list[CoreferenceResult]:
        """
        Resolve co-references for multiple texts.

        Args:
            texts: Sequence of source texts
            entities_list: Extracted entities for each text
            mentions_list: Extracted mentions for each text
            config: Optional override configuration

        Returns:
            List of CoreferenceResults, one per input text
        """
        if not (len(texts) == len(entities_list) == len(mentions_list)):
            raise ValueError(
                "texts, entities_list, and mentions_list must have the same length"
            )

        results: list[CoreferenceResult] = []

        for i, text in enumerate(texts):
            self._logger.info(
                "processing_batch_item",
                index=i,
                total=len(texts),
            )
            result = await self.resolve_with_text(
                text,
                entities_list[i],
                mentions_list[i],
                config,
            )
            results.append(result)

        return results
