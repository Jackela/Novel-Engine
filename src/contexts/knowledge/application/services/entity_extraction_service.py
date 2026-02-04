"""
Entity Extraction Service

Extracts entities from narrative text using LLM-based extraction.
Supports Characters, Locations, Items, Events, and Organizations.
Uses structured output for reliable entity data extraction.

Constitution Compliance:
- Article II (Hexagonal): Application service using LLM port
- Article V (SOLID): SRP - entity extraction only

Warzone 4: AI Brain - BRAIN-029A
"""

from __future__ import annotations

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
        temperature: LLM temperature for extraction
        max_tokens: Maximum tokens in LLM response
    """

    confidence_threshold: float = DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD
    max_entities: int = DEFAULT_MAX_ENTITIES
    include_mentions: bool = True
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
