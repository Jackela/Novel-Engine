"""
Smart Tagging Service

Automatically generates descriptive tags for narrative content using LLM analysis.
Supports genre, mood, themes, characters_present, and locations tag categories.
Tags help with content discovery, filtering, and organization.

Constitution Compliance:
- Article II (Hexagonal): Application service using LLM port
- Article V (SOLID): SRP - tag generation only

Warzone 4: AI Brain - BRAIN-038-01, BRAIN-038-02
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import structlog

from ...application.ports.i_llm_client import (
    ILLMClient,
    LLMError,
    LLMRequest,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = structlog.get_logger()


# Configuration constants
DEFAULT_TEMPERATURE = 0.3  # Lower for more deterministic tagging
DEFAULT_MAX_TOKENS = 500


class TagCategory(Enum):
    """
    Categories of tags for narrative content.

    Why enum:
        Provides type-safe category selection and clear documentation
        of supported tag types.
    """

    GENRE = "genre"  # Fiction genres (sci-fi, fantasy, mystery, etc.)
    MOOD = "mood"  # Emotional tone (tense, melancholic, hopeful, etc.)
    THEMES = "themes"  # Thematic elements (redemption, betrayal, etc.)
    CHARACTERS_PRESENT = "characters_present"  # Named characters in content
    LOCATIONS = "locations"  # Named locations mentioned


@dataclass(frozen=True, slots=True)
class GeneratedTag:
    """
    A single generated tag with its category.

    Why frozen:
        Immutable tag ensures consistency once generated.
    """

    category: TagCategory
    value: str
    confidence: float = 1.0  # 0.0 to 1.0

    def __post_init__(self) -> None:
        """Validate tag data."""
        if not self.value or not self.value.strip():
            raise ValueError("Tag value cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        # Normalize the value
        object.__setattr__(self, "value", self.value.strip().lower())


@dataclass(frozen=True, slots=True)
class TaggingResult:
    """
    Result of smart tagging operation.

    Why frozen:
        Immutable snapshot prevents accidental modification.
    """

    content_type: str  # Type of content (scene, character, lore, etc.)
    tags: Sequence[GeneratedTag]
    raw_llm_response: str | None = None

    def get_tags_by_category(self, category: TagCategory) -> list[str]:
        """
        Get all tag values for a specific category.

        Args:
            category: The tag category to filter by

        Returns:
            List of tag values for the category
        """
        return [tag.value for tag in self.tags if tag.category == category]

    def get_all_tags(self) -> list[str]:
        """
        Get all tag values as a flat list.

        Returns:
            List of all tag values
        """
        return [tag.value for tag in self.tags]


@dataclass(frozen=True, slots=True)
class TaggingConfig:
    """
    Configuration for smart tagging.

    Why frozen:
        Immutable snapshot ensures configuration doesn't change during processing.

    Attributes:
        categories: Tag categories to generate (default: all)
        max_tags_per_category: Maximum tags to generate per category
        min_confidence: Minimum confidence threshold for tags
        temperature: LLM temperature for generation
        max_tokens: Maximum tokens in LLM response
    """

    categories: Sequence[TagCategory] = (
        TagCategory.GENRE,
        TagCategory.MOOD,
        TagCategory.THEMES,
        TagCategory.CHARACTERS_PRESENT,
        TagCategory.LOCATIONS,
    )
    max_tags_per_category: int = 5
    min_confidence: float = 0.5
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.max_tags_per_category < 1:
            raise ValueError("max_tags_per_category must be at least 1")
        if self.max_tags_per_category > 20:
            raise ValueError("max_tags_per_category must not exceed 20")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")


class SmartTaggingError(Exception):
    """Base exception for smart tagging errors."""


class SmartTaggingService:
    """
    Service for automatically generating tags for narrative content.

    Uses LLM analysis to identify genres, moods, themes, characters,
    and locations within narrative text. Tags enable content discovery
    and intelligent filtering across the knowledge base.

    Example:
        >>> service = SmartTaggingService(llm_client=client)
        >>> result = await service.generate_tags(
        ...     content="The spaceship drifted through the asteroid field...",
        ...     content_type="scene"
        ... )
        >>> print(result.get_tags_by_category(TagCategory.GENRE))
        ['sci-fi', 'space opera']
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        config: TaggingConfig | None = None,
    ) -> None:
        """
        Initialize the SmartTaggingService.

        Args:
            llm_client: LLM client for tag generation
            config: Tagging configuration (uses defaults if None)
        """
        self._llm_client = llm_client
        self._config = config or TaggingConfig()
        self._logger = logger.bind(service="smart_tagging")

    def _build_tagging_prompt(self, content: str, content_type: str) -> tuple[str, str]:
        """
        Build the system and user prompts for tag generation.

        Args:
            content: The narrative content to tag
            content_type: Type of content (scene, character, lore, etc.)

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        categories_desc = self._get_category_descriptions()

        system_prompt = f"""You are an expert at analyzing narrative content and generating descriptive tags.

Your task is to analyze the given content and generate relevant tags for these categories:
{categories_desc}

For each category, provide up to {self._config.max_tags_per_category} relevant tags.
Return ONLY valid JSON in this exact format:
{{
  "genre": ["tag1", "tag2"],
  "mood": ["tag1", "tag2"],
  "themes": ["tag1", "tag2"],
  "characters_present": ["character_name1", "character_name2"],
  "locations": ["location_name1", "location_name2"]
}}

Rules:
- Tags should be single words or short phrases (2-3 words max)
- Use lowercase for all tags
- Use hyphens for multi-word tags (e.g., "space-opera", "coming-of-age")
- For characters_present: only include explicitly named characters
- For locations: only include explicitly named locations
- If no tags apply to a category, return an empty array
- Be specific and accurate rather than generic"""

        # Truncate content if too long for prompt
        max_content_length = 4000  # Leave room for system prompt and response
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "\n[Content truncated...]"

        return system_prompt, truncated_content

    def _get_category_descriptions(self) -> str:
        """
        Get human-readable descriptions for enabled tag categories.

        Returns:
            Formatted string describing each category
        """
        descriptions = {
            TagCategory.GENRE: "- genre: Fiction genres (sci-fi, fantasy, mystery, romance, thriller, western, etc.)",
            TagCategory.MOOD: "- mood: Emotional tone (tense, melancholic, hopeful, eerie, romantic, dark, etc.)",
            TagCategory.THEMES: "- themes: Thematic elements (redemption, betrayal, sacrifice, identity, justice, etc.)",
            TagCategory.CHARACTERS_PRESENT: "- characters_present: Named characters appearing in the content",
            TagCategory.LOCATIONS: "- locations: Named locations mentioned in the content",
        }

        enabled = "\n".join(
            descriptions[cat] for cat in self._config.categories if cat in descriptions
        )
        return enabled

    def _parse_llm_response(self, response_text: str) -> dict[str, list[str]]:
        """
        Parse the LLM response into structured tag data.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Dictionary mapping category names to tag lists

        Raises:
            SmartTaggingError: If response cannot be parsed
        """
        try:
            # Try to extract JSON from response
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)

            # Validate structure
            result = {}
            for category in self._config.categories:
                cat_name = category.value
                if cat_name in data:
                    tags = data[cat_name]
                    if isinstance(tags, list):
                        # Ensure all items are strings
                        result[cat_name] = [
                            str(tag).strip().lower()
                            for tag in tags
                            if tag and str(tag).strip()
                        ]
                    else:
                        result[cat_name] = []
                else:
                    result[cat_name] = []

            return result

        except json.JSONDecodeError as e:
            self._logger.error("llm_response_invalid_json", error=str(e))
            raise SmartTaggingError(f"Invalid JSON response: {e}") from e

    async def generate_tags(
        self, content: str, content_type: str = "unknown"
    ) -> TaggingResult:
        """
        Generate tags for the given content.

        Args:
            content: The narrative content to analyze
            content_type: Type of content (scene, character, lore, etc.)

        Returns:
            TaggingResult containing generated tags

        Raises:
            SmartTaggingError: If tag generation fails
        """
        if not content or not content.strip():
            raise SmartTaggingError("Content cannot be empty")

        self._logger.info(
            "generating_tags",
            content_type=content_type,
            content_length=len(content),
        )

        system_prompt, truncated_content = self._build_tagging_prompt(
            content, content_type
        )
        user_prompt = f"""Analyze this {content_type} and generate relevant tags:

{truncated_content}

Respond with ONLY valid JSON matching the schema above."""

        try:
            request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )

            response = await self._llm_client.generate(request)

            # Parse response into tags
            parsed_tags = self._parse_llm_response(response.text)

            # Convert to GeneratedTag objects
            tags: list[GeneratedTag] = []
            for category in self._config.categories:
                cat_name = category.value
                for tag_value in parsed_tags.get(cat_name, []):
                    tags.append(
                        GeneratedTag(
                            category=category,
                            value=tag_value,
                            confidence=1.0,  # LLM-generated tags get full confidence
                        )
                    )

            self._logger.info(
                "tags_generated",
                content_type=content_type,
                total_tags=len(tags),
                tags=tags,
            )

            return TaggingResult(
                content_type=content_type,
                tags=tags,
                raw_llm_response=response.text,
            )

        except LLMError as e:
            self._logger.error("llm_error_during_tagging", error=str(e))
            raise SmartTaggingError(f"LLM error during tagging: {e}") from e
        except SmartTaggingError:
            raise
        except Exception as e:
            self._logger.error("unexpected_error_during_tagging", error=str(e))
            raise SmartTaggingError(f"Unexpected error: {e}") from e
