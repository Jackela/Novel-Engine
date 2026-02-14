"""
Unit tests for SmartTaggingService.

BRAIN-038-01: Smart Tagging Service Setup
Tests tag generation for sample content.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.knowledge.application.ports.i_llm_client import LLMError, LLMResponse
from src.contexts.knowledge.application.services.smart_tagging_service import (
    GeneratedTag,
    SmartTaggingError,
    SmartTaggingService,
    TagCategory,
    TaggingConfig,
    TaggingResult,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_llm_client():
    """Fixture for mock LLM client."""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_tagging_response():
    """Sample LLM response for tagging."""
    return json.dumps(
        {
            "genre": ["sci-fi", "space-opera"],
            "mood": ["tense", "mysterious"],
            "themes": ["survival", "discovery"],
            "characters_present": ["commander-shepard", "garrus"],
            "locations": ["normandy", "citadel"],
        }
    )


class TestSmartTaggingService:
    """Test suite for SmartTaggingService."""

    @pytest.mark.asyncio
    async def test_generate_tags_basic(self, mock_llm_client, sample_tagging_response):
        """Test basic tag generation from sample content."""
        # Setup mock response
        mock_llm_client.generate = AsyncMock(
            return_value=LLMResponse(
                text=sample_tagging_response,
                model="test-model",
                input_tokens=100,
                output_tokens=50,
                raw_usage={},
            )
        )

        service = SmartTaggingService(llm_client=mock_llm_client)

        content = "Commander Shepard stood on the Normandy's bridge, gazing at the Citadel through the viewport. The station's massive arms cradled the heart of galactic civilization."

        result = await service.generate_tags(content, content_type="scene")

        # Verify result structure
        assert isinstance(result, TaggingResult)
        assert result.content_type == "scene"
        assert len(result.tags) > 0

        # Verify genre tags
        genre_tags = result.get_tags_by_category(TagCategory.GENRE)
        assert "sci-fi" in genre_tags
        assert "space-opera" in genre_tags

        # Verify mood tags
        mood_tags = result.get_tags_by_category(TagCategory.MOOD)
        assert len(mood_tags) > 0

        # Verify all tags
        all_tags = result.get_all_tags()
        assert len(all_tags) > 0

    @pytest.mark.asyncio
    async def test_generate_tags_empty_content(self, mock_llm_client):
        """Test that empty content raises error."""
        service = SmartTaggingService(llm_client=mock_llm_client)

        with pytest.raises(SmartTaggingError, match="Content cannot be empty"):
            await service.generate_tags("")

        with pytest.raises(SmartTaggingError, match="Content cannot be empty"):
            await service.generate_tags("   ")

    @pytest.mark.asyncio
    async def test_generate_tags_llm_error(self, mock_llm_client):
        """Test handling of LLM errors."""
        mock_llm_client.generate = AsyncMock(side_effect=LLMError("API error"))

        service = SmartTaggingService(llm_client=mock_llm_client)

        with pytest.raises(SmartTaggingError, match="LLM error"):
            await service.generate_tags("Test content")

    @pytest.mark.asyncio
    async def test_generate_tags_invalid_json(self, mock_llm_client):
        """Test handling of invalid JSON response."""
        mock_llm_client.generate = AsyncMock(
            return_value=LLMResponse(
                text="This is not valid JSON",
                model="test-model",
                input_tokens=100,
                output_tokens=10,
                raw_usage={},
            )
        )

        service = SmartTaggingService(llm_client=mock_llm_client)

        with pytest.raises(SmartTaggingError, match="Invalid JSON"):
            await service.generate_tags("Test content")

    @pytest.mark.asyncio
    async def test_generate_tags_json_code_block(
        self, mock_llm_client, sample_tagging_response
    ):
        """Test parsing JSON from markdown code block."""
        mock_llm_client.generate = AsyncMock(
            return_value=LLMResponse(
                text=f"```json\n{sample_tagging_response}\n```",
                model="test-model",
                input_tokens=100,
                output_tokens=50,
                raw_usage={},
            )
        )

        service = SmartTaggingService(llm_client=mock_llm_client)

        result = await service.generate_tags("Test content")

        assert len(result.tags) > 0
        assert "sci-fi" in result.get_tags_by_category(TagCategory.GENRE)

    @pytest.mark.asyncio
    async def test_generate_tags_custom_config(self, mock_llm_client):
        """Test tag generation with custom configuration."""
        mock_llm_client.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"genre": ["fantasy"], "mood": ["dark"]}',
                model="test-model",
                input_tokens=100,
                output_tokens=20,
                raw_usage={},
            )
        )

        config = TaggingConfig(
            categories=[TagCategory.GENRE, TagCategory.MOOD],
            max_tags_per_category=3,
            temperature=0.5,
        )

        service = SmartTaggingService(llm_client=mock_llm_client, config=config)

        result = await service.generate_tags(
            "The dragon scales gleamed in the darkness."
        )

        # Verify only configured categories are returned
        assert len(result.get_tags_by_category(TagCategory.GENRE)) > 0
        assert len(result.get_tags_by_category(TagCategory.MOOD)) > 0
        # Characters and locations should be empty (not in config)
        assert len(result.get_tags_by_category(TagCategory.CHARACTERS_PRESENT)) == 0

    @pytest.mark.asyncio
    async def test_generate_tags_content_truncation(self, mock_llm_client):
        """Test that long content is truncated for the prompt."""
        mock_llm_client.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"genre": ["test"]}',
                model="test-model",
                input_tokens=100,
                output_tokens=10,
                raw_usage={},
            )
        )

        service = SmartTaggingService(llm_client=mock_llm_client)

        # Create content longer than max length
        long_content = "A" * 5000

        result = await service.generate_tags(long_content)

        # Should succeed without error
        assert len(result.tags) > 0

        # Verify the request was made with truncated content
        call_args = mock_llm_client.generate.call_args
        request = call_args[0][0]
        assert "[Content truncated...]" in request.user_prompt

    def test_tag_category_enum(self):
        """Test TagCategory enum values."""
        assert TagCategory.GENRE.value == "genre"
        assert TagCategory.MOOD.value == "mood"
        assert TagCategory.THEMES.value == "themes"
        assert TagCategory.CHARACTERS_PRESENT.value == "characters_present"
        assert TagCategory.LOCATIONS.value == "locations"

    def test_generated_tag_validation(self):
        """Test GeneratedTag validation."""
        # Valid tag
        tag = GeneratedTag(category=TagCategory.GENRE, value="fantasy", confidence=0.9)
        assert tag.value == "fantasy"
        assert tag.category == TagCategory.GENRE

        # Empty value should raise error
        with pytest.raises(ValueError, match="Tag value cannot be empty"):
            GeneratedTag(category=TagCategory.GENRE, value="", confidence=0.9)

        # Invalid confidence should raise error
        with pytest.raises(ValueError, match="Confidence must be between"):
            GeneratedTag(category=TagCategory.GENRE, value="fantasy", confidence=1.5)

    def test_tagging_result_get_tags_by_category(self):
        """Test TaggingResult.get_tags_by_category."""
        tags = [
            GeneratedTag(TagCategory.GENRE, "fantasy", 0.9),
            GeneratedTag(TagCategory.GENRE, "adventure", 0.8),
            GeneratedTag(TagCategory.MOOD, "dark", 0.9),
        ]

        result = TaggingResult(content_type="scene", tags=tags)

        genre_tags = result.get_tags_by_category(TagCategory.GENRE)
        assert genre_tags == ["fantasy", "adventure"]

        mood_tags = result.get_tags_by_category(TagCategory.MOOD)
        assert mood_tags == ["dark"]

        # Empty category returns empty list
        assert result.get_tags_by_category(TagCategory.LOCATIONS) == []

    def test_tagging_result_get_all_tags(self):
        """Test TaggingResult.get_all_tags."""
        tags = [
            GeneratedTag(TagCategory.GENRE, "fantasy", 0.9),
            GeneratedTag(TagCategory.MOOD, "dark", 0.9),
        ]

        result = TaggingResult(content_type="scene", tags=tags)

        all_tags = result.get_all_tags()
        assert all_tags == ["fantasy", "dark"]

    def test_tagging_config_defaults(self):
        """Test TaggingConfig default values."""
        config = TaggingConfig()

        assert config.max_tags_per_category == 5
        assert config.min_confidence == 0.5
        assert config.temperature == 0.3
        assert len(config.categories) == 5  # All categories by default

    def test_tagging_config_validation(self):
        """Test TaggingConfig validation."""
        # Invalid max_tags_per_category
        with pytest.raises(
            ValueError, match="max_tags_per_category must be at least 1"
        ):
            TaggingConfig(max_tags_per_category=0)

        # Invalid min_confidence
        with pytest.raises(ValueError, match="min_confidence must be between"):
            TaggingConfig(min_confidence=1.5)

        # Invalid temperature
        with pytest.raises(ValueError, match="temperature must be between"):
            TaggingConfig(temperature=3.0)

    @pytest.mark.asyncio
    async def test_generate_tags_normalizes_values(self, mock_llm_client):
        """Test that tag values are normalized (lowercase, stripped)."""
        mock_llm_client.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"genre": ["  Sci-Fi  ", "FANTASY"]}',
                model="test-model",
                input_tokens=100,
                output_tokens=20,
                raw_usage={},
            )
        )

        service = SmartTaggingService(llm_client=mock_llm_client)

        result = await service.generate_tags("Test content")

        genre_tags = result.get_tags_by_category(TagCategory.GENRE)
        # Should be normalized to lowercase
        assert "sci-fi" in genre_tags
        assert "fantasy" in genre_tags
