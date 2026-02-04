"""
Entity Extraction Service

Extracts entities and relationships from narrative text using LLM-based extraction.
Supports Characters, Locations, Items, Events, and Organizations.
Uses structured output for reliable entity data extraction.

Constitution Compliance:
- Article II (Hexagonal): Application service using LLM port
- Article V (SOLID): SRP - entity extraction only

Warzone 4: AI Brain - BRAIN-029A, BRAIN-030A
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from ...application.ports.i_llm_client import ILLMClient, LLMRequest, LLMError
from ...domain.models.entity import (
    EntityType,
    ExtractedEntity,
    EntityMention,
    ExtractionResult,
    ExtractionResultWithRelationships,
    Relationship,
    RelationshipType,
    DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_ENTITIES,
    PRONOUNS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = structlog.get_logger()


# Configuration constants
DEFAULT_TEMPERATURE = 0.3  # Lower for more deterministic extraction
DEFAULT_MAX_TOKENS = 2000


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    """
    Configuration for entity extraction.

    Why frozen:
        Immutable snapshot ensures configuration doesn't change during processing.

    Attributes:
        confidence_threshold: Minimum confidence for extracted entities (0.0-1.0)
        max_entities: Maximum number of entities to extract
        include_mentions: Whether to extract individual mentions
        extract_relationships: Whether to extract relationships between entities
        max_relationships: Maximum number of relationships to extract
        relationship_strength_threshold: Minimum strength for relationships (0.0-1.0)
        temperature: LLM temperature for extraction
        max_tokens: Maximum tokens in LLM response
    """

    confidence_threshold: float = DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD
    max_entities: int = DEFAULT_MAX_ENTITIES
    include_mentions: bool = True
    extract_relationships: bool = False
    max_relationships: int = 30
    relationship_strength_threshold: float = 0.3
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        if self.max_entities < 1:
            raise ValueError("max_entities must be at least 1")
        if self.max_entities > 100:
            raise ValueError("max_entities must not exceed 100")
        if self.max_relationships < 1:
            raise ValueError("max_relationships must be at least 1")
        if self.max_relationships > 100:
            raise ValueError("max_relationships must not exceed 100")
        if not 0.0 <= self.relationship_strength_threshold <= 1.0:
            raise ValueError("relationship_strength_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")


class EntityExtractionError(Exception):
    """Base exception for entity extraction errors."""

    pass


class EntityExtractionService:
    """
    Service for extracting entities from narrative text using LLM.

    Uses structured JSON output from LLM to extract entities with
    their types, aliases, descriptions, and positions in text.

    Example:
        >>> service = EntityExtractionService(llm_client=client)
        >>> result = await service.extract(
        ...     text="Alice entered the tavern. The barkeep smiled.",
        ...     config=ExtractionConfig()
        ... )
        >>> for entity in result.entities:
        ...     print(f"{entity.name}: {entity.entity_type}")
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        config: ExtractionConfig | None = None,
    ) -> None:
        """
        Initialize the EntityExtractionService.

        Args:
            llm_client: LLM client for extraction
            config: Extraction configuration (uses defaults if None)
        """
        self._llm_client = llm_client
        self._config = config or ExtractionConfig()
        self._logger = logger.bind(service="entity_extraction")

    def _build_extraction_prompt(self, text: str) -> tuple[str, str]:
        """
        Build the system and user prompts for entity extraction.

        Args:
            text: The narrative text to extract entities from

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        entity_types = ", ".join([e.value for e in EntityType])

        system_prompt = f"""You are an expert at analyzing narrative text and extracting entities.

Extract entities of these types: {entity_types}.

For each entity, provide:
- name: The primary name (proper cased)
- type: One of: {entity_types}
- aliases: Alternative names or references (empty array if none)
- description: Brief description (1-2 sentences)
- first_appearance: Character position where first mentioned

Return ONLY valid JSON. Format:
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "character|location|item|event|organization",
      "aliases": ["alias1", "alias2"],
      "description": "Brief description",
      "first_appearance": 0
    }}
  ],
  "mentions": [
    {{
      "entity_name": "Entity Name",
      "mention_text": "exact text from source",
      "start_pos": 0,
      "end_pos": 10,
      "is_pronoun": false
    }}
  ]
}}"""

        # Truncate text if too long for prompt
        max_text_length = 8000  # Leave room for system prompt and response
        truncated_text = text[:max_text_length]
        if len(text) > max_text_length:
            truncated_text += "\n[Text truncated...]"

        user_prompt = f"""Extract entities from this narrative text:

{text}

Respond with ONLY valid JSON matching the schema above."""

        return system_prompt, user_prompt

    def _parse_llm_response(self, response_text: str) -> dict[str, object]:
        """
        Parse the LLM response into structured data.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Parsed JSON dictionary

        Raises:
            EntityExtractionError: If parsing fails
        """
        # Try to extract JSON from response
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

        try:
            result: dict[str, object] = json.loads(cleaned)
            return result
        except json.JSONDecodeError as e:
            self._logger.warning(
                "failed_to_parse_llm_response",
                error=str(e),
                response_length=len(response_text),
            )
            raise EntityExtractionError(f"Failed to parse LLM response as JSON: {e}")

    def _build_entities(
        self, entities_data: list[dict], source_length: int
    ) -> list[ExtractedEntity]:
        """
        Build ExtractedEntity objects from parsed data.

        Args:
            entities_data: List of entity dictionaries from LLM
            source_length: Length of source text for validation

        Returns:
            List of ExtractedEntity objects
        """
        entities: list[ExtractedEntity] = []

        for entity_data in entities_data[:self._config.max_entities]:
            try:
                entity_type_str = entity_data.get("type", "").lower()
                # Handle various type name formats
                entity_type_str = entity_type_str.rstrip("s")  # Remove plural 's'

                try:
                    entity_type = EntityType(entity_type_str)
                except ValueError:
                    # Map common variations
                    type_mapping = {
                        "person": EntityType.CHARACTER,
                        "place": EntityType.LOCATION,
                        "object": EntityType.ITEM,
                        "incident": EntityType.EVENT,
                        "group": EntityType.ORGANIZATION,
                    }
                    entity_type = type_mapping.get(
                        entity_type_str, EntityType.CHARACTER
                    )

                entity = ExtractedEntity(
                    name=entity_data.get("name", "Unknown"),
                    entity_type=entity_type,
                    aliases=tuple(entity_data.get("aliases", [])),
                    description=entity_data.get("description", ""),
                    first_appearance=entity_data.get("first_appearance", 0),
                    confidence=entity_data.get("confidence", 1.0),
                    metadata=entity_data.get("metadata", {}),
                )

                # Filter by confidence threshold
                if entity.confidence >= self._config.confidence_threshold:
                    entities.append(entity)

            except (ValueError, KeyError) as e:
                self._logger.warning(
                    "failed_to_build_entity",
                    error=str(e),
                    entity_data=entity_data,
                )
                continue

        return entities

    def _build_mentions(
        self, mentions_data: list[dict], source_length: int
    ) -> list[EntityMention]:
        """
        Build EntityMention objects from parsed data.

        Args:
            mentions_data: List of mention dictionaries from LLM
            source_length: Length of source text for validation

        Returns:
            List of EntityMention objects
        """
        mentions: list[EntityMention] = []

        for mention_data in mentions_data:
            try:
                mention_text = mention_data.get("mention_text", "")
                is_pronoun = mention_data.get("is_pronoun", False)

                # Auto-detect pronouns if not specified
                if not is_pronoun:
                    is_pronoun = mention_text.lower().strip() in PRONOUNS

                mention = EntityMention(
                    entity_name=mention_data.get("entity_name", ""),
                    mention_text=mention_text,
                    start_pos=mention_data.get("start_pos", 0),
                    end_pos=mention_data.get("end_pos", 0),
                    is_pronoun=is_pronoun,
                )
                mentions.append(mention)

            except (ValueError, KeyError) as e:
                self._logger.warning(
                    "failed_to_build_mention",
                    error=str(e),
                    mention_data=mention_data,
                )
                continue

        return mentions

    async def extract(
        self,
        text: str,
        config: ExtractionConfig | None = None,
    ) -> ExtractionResult:
        """
        Extract entities from narrative text.

        Args:
            text: The narrative text to extract entities from
            config: Optional override configuration

        Returns:
            ExtractionResult containing entities and mentions

        Raises:
            EntityExtractionError: If extraction fails
        """
        effective_config = config or self._config
        source_length = len(text)

        self._logger.info(
            "starting_entity_extraction",
            text_length=source_length,
            confidence_threshold=effective_config.confidence_threshold,
            max_entities=effective_config.max_entities,
        )

        # Build prompts
        system_prompt, user_prompt = self._build_extraction_prompt(text)

        # Create LLM request
        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=effective_config.temperature,
            max_tokens=effective_config.max_tokens,
        )

        # Call LLM
        try:
            response = await self._llm_client.generate(request)
            model_used = response.model
            tokens_used = response.tokens_used
        except LLMError as e:
            self._logger.error("llm_generation_failed", error=str(e))
            raise EntityExtractionError(f"LLM generation failed: {e}")

        # Parse response
        try:
            parsed = self._parse_llm_response(response.text)
        except EntityExtractionError:
            # Return empty result on parse failure
            return ExtractionResult(
                entities=(),
                mentions=(),
                source_length=source_length,
                model_used=model_used,
                tokens_used=tokens_used,
            )

        # Build entities and mentions
        entities_data_raw = parsed.get("entities", [])
        mentions_data_raw = parsed.get("mentions", [])

        # Type narrowing for JSON data
        entities_data: list[dict] = (
            entities_data_raw if isinstance(entities_data_raw, list) else []
        )
        mentions_data: list[dict] = (
            mentions_data_raw if isinstance(mentions_data_raw, list) else []
        )

        entities = self._build_entities(entities_data, source_length)
        mentions = (
            self._build_mentions(mentions_data, source_length)
            if effective_config.include_mentions
            else []
        )

        result = ExtractionResult(
            entities=tuple(entities),
            mentions=tuple(mentions),
            source_length=source_length,
            model_used=model_used,
            tokens_used=tokens_used,
        )

        self._logger.info(
            "entity_extraction_complete",
            entity_count=result.entity_count,
            mention_count=result.mention_count,
            tokens_used=tokens_used,
        )

        return result

    async def extract_batch(
        self,
        texts: Sequence[str],
        config: ExtractionConfig | None = None,
    ) -> list[ExtractionResult]:
        """
        Extract entities from multiple texts.

        Args:
            texts: Sequence of narrative texts to process
            config: Optional override configuration

        Returns:
            List of ExtractionResults, one per input text
        """
        results: list[ExtractionResult] = []

        for i, text in enumerate(texts):
            self._logger.info(
                "processing_batch_item",
                index=i,
                total=len(texts),
            )
            result = await self.extract(text, config)
            results.append(result)

        return results

    async def extract_large_text(
        self,
        text: str,
        config: ExtractionConfig | None = None,
        chunk_size: int = 8000,
        overlap: int = 500,
    ) -> ExtractionResult:
        """
        Extract entities from a large text by chunking it.

        Processes large texts that exceed prompt token limits by splitting
        them into overlapping chunks, extracting entities from each chunk,
        and merging the results.

        Args:
            text: Large narrative text to process
            config: Optional override configuration
            chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks for context continuity

        Returns:
            Merged ExtractionResult with deduplicated entities and mentions
        """
        effective_config = config or self._config
        source_length = len(text)

        self._logger.info(
            "starting_large_text_extraction",
            text_length=source_length,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        # Skip chunking for small texts
        if source_length <= chunk_size:
            return await self.extract(text, config)

        # Split into chunks
        chunks: list[str] = []
        start = 0

        while start < source_length:
            end = min(start + chunk_size, source_length)
            chunks.append(text[start:end])
            start = end - overlap if end < source_length else source_length

        self._logger.info(
            "split_into_chunks",
            chunk_count=len(chunks),
        )

        # Extract from each chunk
        chunk_results: list[ExtractionResult] = []
        offset = 0

        for i, chunk in enumerate(chunks):
            self._logger.info(
                "processing_chunk",
                chunk_index=i,
                total_chunks=len(chunks),
            )

            result = await self.extract(chunk, effective_config)

            # Adjust entity and mention positions for original text
            adjusted_entities = [
                ExtractedEntity(
                    name=e.name,
                    entity_type=e.entity_type,
                    aliases=e.aliases,
                    description=e.description,
                    first_appearance=e.first_appearance + offset,
                    confidence=e.confidence,
                    metadata=e.metadata,
                )
                for e in result.entities
            ]

            adjusted_mentions = [
                EntityMention(
                    entity_name=m.entity_name,
                    mention_text=m.mention_text,
                    start_pos=m.start_pos + offset,
                    end_pos=m.end_pos + offset,
                    is_pronoun=m.is_pronoun,
                )
                for m in result.mentions
            ]

            # Create adjusted result
            chunk_results.append(ExtractionResult(
                entities=tuple(adjusted_entities),
                mentions=tuple(adjusted_mentions),
                source_length=len(chunk),
                timestamp=result.timestamp,
                model_used=result.model_used,
                tokens_used=result.tokens_used,
            ))

            offset += len(chunk) - overlap if i < len(chunks) - 1 else len(chunk)

        # Merge results
        merged = self._merge_extraction_results(chunk_results, source_length)

        self._logger.info(
            "large_text_extraction_complete",
            total_entities=merged.entity_count,
            total_mentions=merged.mention_count,
        )

        return merged

    def _merge_extraction_results(
        self,
        results: list[ExtractionResult],
        source_length: int,
    ) -> ExtractionResult:
        """
        Merge multiple extraction results into one.

        Deduplicates entities by name and merges mentions.

        Args:
            results: List of ExtractionResults to merge
            source_length: Length of the original source text

        Returns:
            Merged ExtractionResult
        """
        seen_entities: dict[str, ExtractedEntity] = {}
        all_mentions: list[EntityMention] = []
        total_tokens = 0
        models_used: set[str] = set()

        for result in results:
            # Merge entities (keep first occurrence, highest confidence)
            for entity in result.entities:
                key = entity.name.lower()
                if key not in seen_entities:
                    seen_entities[key] = entity
                else:
                    # Update if this has higher confidence
                    if entity.confidence > seen_entities[key].confidence:
                        seen_entities[key] = entity

            # Collect all mentions
            all_mentions.extend(result.mentions)

            # Track tokens and models
            if result.tokens_used:
                total_tokens += result.tokens_used
            if result.model_used:
                models_used.add(result.model_used)

        return ExtractionResult(
            entities=tuple(seen_entities.values()),
            mentions=tuple(all_mentions),
            source_length=source_length,
            model_used=", ".join(sorted(models_used)),
            tokens_used=total_tokens if total_tokens > 0 else None,
        )

    # Relationship extraction methods

    def _build_relationship_extraction_prompt(
        self, text: str, entities: tuple[ExtractedEntity, ...]
    ) -> tuple[str, str]:
        """
        Build prompts for relationship extraction.

        Args:
            text: The narrative text to extract relationships from
            entities: Previously extracted entities to find relationships between

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Build list of known entities for context
        entity_list = "\n".join(
            f"- {e.name} ({e.entity_type.value})"
            for e in entities
        )

        # Build list of relationship types
        relationship_types = ", ".join([rt.value for rt in RelationshipType])

        system_prompt = f"""You are an expert at analyzing narrative text and extracting relationships between entities.

Known entities in this text:
{entity_list}

Extract relationships of these types: {relationship_types}.

For each relationship, provide:
- source: Name of the source entity (from the list above)
- target: Name of the target entity (from the list above)
- type: One of: {relationship_types}
- context: Brief quote or description showing where this relationship appears
- strength: Confidence 0.0-1.0 (use 1.0 for explicitly stated, 0.5-0.7 for implied)
- bidirectional: true if relationship works both ways (e.g., KNOWS, ALLIED_WITH)
- temporal: Time reference if applicable (e.g., "during chapter 1", "before the battle")

Return ONLY valid JSON. Format:
{{
  "relationships": [
    {{
      "source": "Entity Name",
      "target": "Another Entity",
      "type": "knows|killed|loves|hates|parent_of|child_of|member_of|leads|serves|owns|located_at|occurred_at|participated_in|allied_with|enemy_of|mentored|other",
      "context": "Brief context from text",
      "strength": 1.0,
      "bidirectional": false,
      "temporal": ""
    }}
  ]
}}"""

        user_prompt = f"""Extract relationships from this narrative text:

{text}

Respond with ONLY valid JSON matching the schema above."""

        return system_prompt, user_prompt

    def _build_relationships(
        self,
        relationships_data: list[dict],
        known_entities: tuple[ExtractedEntity, ...],
    ) -> list[Relationship]:
        """
        Build Relationship objects from parsed data.

        Args:
            relationships_data: List of relationship dictionaries from LLM
            known_entities: Tuple of known entities for validation

        Returns:
            List of Relationship objects
        """
        relationships: list[Relationship] = []
        known_names = {e.name.lower() for e in known_entities}

        for rel_data in relationships_data[:self._config.max_relationships]:
            try:
                source = rel_data.get("source", "").strip()
                target = rel_data.get("target", "").strip()

                # Skip if entities aren't recognized
                if source.lower() not in known_names or target.lower() not in known_names:
                    self._logger.warning(
                        "relationship_references_unknown_entity",
                        source=source,
                        target=target,
                    )
                    continue

                # Skip self-relationships
                if source.lower() == target.lower():
                    continue

                # Parse relationship type
                type_str = rel_data.get("type", "other").lower().replace("-", "_")
                try:
                    relationship_type = RelationshipType(type_str)
                except ValueError:
                    # Map common variations
                    type_mapping = {
                        "know": RelationshipType.KNOWS,
                        "kill": RelationshipType.KILLED,
                        "love": RelationshipType.LOVES,
                        "hate": RelationshipType.HATES,
                        "parent": RelationshipType.PARENT_OF,
                        "child": RelationshipType.CHILD_OF,
                        "member": RelationshipType.MEMBER_OF,
                        "lead": RelationshipType.LEADS,
                        "serve": RelationshipType.SERVES,
                        "own": RelationshipType.OWNS,
                        "located": RelationshipType.LOCATED_AT,
                        "occurred": RelationshipType.OCCURRED_AT,
                        "participated": RelationshipType.PARTICIPATED_IN,
                        "ally": RelationshipType.ALLIED_WITH,
                        "enemy": RelationshipType.ENEMY_OF,
                        "mentor": RelationshipType.MENTORED,
                    }
                    relationship_type = type_mapping.get(type_str, RelationshipType.OTHER)

                strength = float(rel_data.get("strength", 1.0))
                # Filter by strength threshold
                if strength < self._config.relationship_strength_threshold:
                    continue

                relationship = Relationship(
                    source=source,
                    target=target,
                    relationship_type=relationship_type,
                    context=rel_data.get("context", ""),
                    strength=min(1.0, max(0.0, strength)),  # Clamp to 0-1
                    bidirectional=rel_data.get("bidirectional", False),
                    temporal_marker=rel_data.get("temporal", ""),
                    metadata=rel_data.get("metadata", {}),
                )
                relationships.append(relationship)

            except (ValueError, KeyError) as e:
                self._logger.warning(
                    "failed_to_build_relationship",
                    error=str(e),
                    relationship_data=rel_data,
                )
                continue

        return relationships

    async def extract_with_relationships(
        self,
        text: str,
        config: ExtractionConfig | None = None,
    ) -> ExtractionResultWithRelationships:
        """
        Extract entities and relationships from narrative text.

        First extracts entities, then extracts relationships between them.
        Returns an enhanced result containing both entities and relationships.

        Args:
            text: The narrative text to extract from
            config: Optional override configuration (must have extract_relationships=True)

        Returns:
            ExtractionResultWithRelationships containing entities and relationships

        Raises:
            EntityExtractionError: If extraction fails
        """
        effective_config = config or self._config

        # Enable relationship extraction for this call
        if isinstance(config, ExtractionConfig):
            extraction_config = dataclasses.replace(
                effective_config,
                extract_relationships=True
            )
        else:
            extraction_config = effective_config

        # First extract entities
        entity_result = await self.extract(text, extraction_config)

        self._logger.info(
            "starting_relationship_extraction",
            entity_count=entity_result.entity_count,
            max_relationships=extraction_config.max_relationships,
        )

        # Build relationship extraction prompts
        system_prompt, user_prompt = self._build_relationship_extraction_prompt(
            text, entity_result.entities
        )

        # Create LLM request for relationships
        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=extraction_config.temperature,
            max_tokens=extraction_config.max_tokens,
        )

        # Call LLM for relationships
        try:
            response = await self._llm_client.generate(request)
        except LLMError as e:
            self._logger.error("relationship_llm_generation_failed", error=str(e))
            # Return entities only on failure
            return ExtractionResultWithRelationships(
                entities=entity_result.entities,
                mentions=entity_result.mentions,
                source_length=entity_result.source_length,
                relationships=(),
                timestamp=entity_result.timestamp,
                model_used=entity_result.model_used,
                tokens_used=entity_result.tokens_used,
            )

        # Parse relationship response
        try:
            parsed = self._parse_llm_response(response.text)
        except EntityExtractionError:
            # Return entities only on parse failure
            return ExtractionResultWithRelationships(
                entities=entity_result.entities,
                mentions=entity_result.mentions,
                source_length=entity_result.source_length,
                relationships=(),
                timestamp=entity_result.timestamp,
                model_used=entity_result.model_used,
                tokens_used=entity_result.tokens_used,
            )

        # Build relationships
        relationships_data_raw = parsed.get("relationships", [])
        relationships_data: list[dict] = (
            relationships_data_raw if isinstance(relationships_data_raw, list) else []
        )

        relationships = self._build_relationships(
            relationships_data, entity_result.entities
        )

        self._logger.info(
            "relationship_extraction_complete",
            relationship_count=len(relationships),
        )

        return ExtractionResultWithRelationships(
            entities=entity_result.entities,
            mentions=entity_result.mentions,
            source_length=entity_result.source_length,
            relationships=tuple(relationships),
            timestamp=entity_result.timestamp,
            model_used=entity_result.model_used,
            tokens_used=entity_result.tokens_used,
        )
