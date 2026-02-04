"""
Unit Tests for Entity Extraction Service

Warzone 4: AI Brain - BRAIN-029A

Tests for the entity extraction service that uses LLM to extract
named entities from narrative text (Characters, Locations, Items, Events, Organizations).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from src.contexts.knowledge.application.services.entity_extraction_service import (
    EntityExtractionService,
    ExtractionConfig,
    EntityExtractionError,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
)
from src.contexts.knowledge.application.ports.i_llm_client import (
    ILLMClient,
    LLMRequest,
    LLMResponse,
    LLMError,
)
from src.contexts.knowledge.domain.models.entity import (
    EntityType,
    ExtractedEntity,
    EntityMention,
    ExtractionResult,
    DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_ENTITIES,
    PRONOUNS,
)


# Sample LLM response for entity extraction
SAMPLE_EXTRACTION_JSON = """{
  "entities": [
    {
      "name": "Alice",
      "type": "character",
      "aliases": ["the warrior", "our hero"],
      "description": "A brave warrior on a quest",
      "first_appearance": 0,
      "confidence": 0.95
    },
    {
      "name": "The Rusty Sword",
      "type": "item",
      "aliases": [],
      "description": "An ancient weapon found in the tavern",
      "first_appearance": 42,
      "confidence": 0.88
    },
    {
      "name": "Golden Dragon Tavern",
      "type": "location",
      "aliases": ["the tavern", "the inn"],
      "description": "A popular gathering place for adventurers",
      "first_appearance": 28,
      "confidence": 0.92
    },
    {
      "name": "Battle of Three Peaks",
      "type": "event",
      "aliases": ["the great battle"],
      "description": "A legendary conflict that shaped the kingdom",
      "first_appearance": 85,
      "confidence": 0.85
    },
    {
      "name": "Adventurers Guild",
      "type": "organization",
      "aliases": ["the guild"],
      "description": "An organization that regulates questing",
      "first_appearance": 120,
      "confidence": 0.90
    }
  ],
  "mentions": [
    {
      "entity_name": "Alice",
      "mention_text": "Alice",
      "start_pos": 0,
      "end_pos": 5,
      "is_pronoun": false
    },
    {
      "entity_name": "Alice",
      "mention_text": "she",
      "start_pos": 15,
      "end_pos": 18,
      "is_pronoun": true
    },
    {
      "entity_name": "Golden Dragon Tavern",
      "mention_text": "the tavern",
      "start_pos": 28,
      "end_pos": 38,
      "is_pronoun": false
    }
  ]
}"""


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=SAMPLE_EXTRACTION_JSON,
            model="test-model",
            tokens_used=150,
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
def invalid_json_llm_client():
    """Create a mock LLM client that returns invalid JSON."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text="This is not valid JSON at all",
            model="test-model",
        )

    client.generate = mock_generate
    return client


@pytest.fixture
def markdown_json_llm_client():
    """Create a mock LLM client that returns JSON in markdown code blocks."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=f'Here is the extracted data:\n```json\n{SAMPLE_EXTRACTION_JSON}\n```',
            model="test-model",
        )

    client.generate = mock_generate
    return client


@pytest.fixture
def default_config():
    """Create default extraction configuration."""
    return ExtractionConfig()


@pytest.fixture
def entity_extraction_service(mock_llm_client):
    """Create an EntityExtractionService instance with mock LLM."""
    return EntityExtractionService(llm_client=mock_llm_client)


class TestExtractionConfig:
    """Tests for ExtractionConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExtractionConfig()

        assert config.confidence_threshold == DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD
        assert config.max_entities == DEFAULT_MAX_ENTITIES
        assert config.include_mentions is True
        assert config.temperature == DEFAULT_TEMPERATURE
        assert config.max_tokens == DEFAULT_MAX_TOKENS

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ExtractionConfig(
            confidence_threshold=0.7,
            max_entities=25,
            include_mentions=False,
            temperature=0.5,
            max_tokens=1500,
        )

        assert config.confidence_threshold == 0.7
        assert config.max_entities == 25
        assert config.include_mentions is False
        assert config.temperature == 0.5
        assert config.max_tokens == 1500

    def test_config_validation_confidence_too_low(self):
        """Test validation rejects confidence < 0."""
        with pytest.raises(ValueError, match="confidence_threshold"):
            ExtractionConfig(confidence_threshold=-0.1)

    def test_config_validation_confidence_too_high(self):
        """Test validation rejects confidence > 1."""
        with pytest.raises(ValueError, match="confidence_threshold"):
            ExtractionConfig(confidence_threshold=1.1)

    def test_config_validation_max_entities_too_low(self):
        """Test validation rejects max_entities < 1."""
        with pytest.raises(ValueError, match="max_entities"):
            ExtractionConfig(max_entities=0)

    def test_config_validation_max_entities_too_high(self):
        """Test validation rejects max_entities > 100."""
        with pytest.raises(ValueError, match="max_entities"):
            ExtractionConfig(max_entities=101)

    def test_config_validation_temperature_out_of_range(self):
        """Test validation rejects temperature outside 0-2."""
        with pytest.raises(ValueError, match="temperature"):
            ExtractionConfig(temperature=2.5)

    def test_config_frozen(self):
        """Test config is immutable (frozen dataclass)."""
        config = ExtractionConfig()
        with pytest.raises(AttributeError):
            config.max_entities = 10


class TestExtractedEntity:
    """Tests for ExtractedEntity value object."""

    def test_entity_creation(self):
        """Test creating a valid entity."""
        entity = ExtractedEntity(
            name="Alice",
            entity_type=EntityType.CHARACTER,
            aliases=("the warrior", "hero"),
            description="A brave warrior",
            confidence=0.95,
        )

        assert entity.name == "Alice"
        assert entity.entity_type == EntityType.CHARACTER
        assert entity.aliases == ("the warrior", "hero")
        assert entity.description == "A brave warrior"
        assert entity.confidence == 0.95

    def test_entity_validation_empty_name(self):
        """Test validation rejects empty name."""
        with pytest.raises(ValueError, match="name"):
            ExtractedEntity(name="", entity_type=EntityType.CHARACTER)

    def test_entity_validation_whitespace_name(self):
        """Test validation rejects whitespace-only name."""
        with pytest.raises(ValueError, match="name"):
            ExtractedEntity(name="   ", entity_type=EntityType.CHARACTER)

    def test_entity_validation_confidence_too_low(self):
        """Test validation rejects confidence < 0."""
        with pytest.raises(ValueError, match="Confidence"):
            ExtractedEntity(
                name="Test",
                entity_type=EntityType.CHARACTER,
                confidence=-0.1,
            )

    def test_entity_validation_confidence_too_high(self):
        """Test validation rejects confidence > 1."""
        with pytest.raises(ValueError, match="Confidence"):
            ExtractedEntity(
                name="Test",
                entity_type=EntityType.CHARACTER,
                confidence=1.1,
            )

    def test_entity_validation_negative_appearance(self):
        """Test validation rejects negative first_appearance."""
        with pytest.raises(ValueError, match="first_appearance"):
            ExtractedEntity(
                name="Test",
                entity_type=EntityType.CHARACTER,
                first_appearance=-1,
            )

    def test_has_alias_exact_name(self):
        """Test has_alias returns True for exact name match."""
        entity = ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER)
        assert entity.has_alias("Alice") is True
        assert entity.has_alias("alice") is True  # Case-insensitive

    def test_has_alias_matches_alias_list(self):
        """Test has_alias returns True for aliases."""
        entity = ExtractedEntity(
            name="Alice",
            entity_type=EntityType.CHARACTER,
            aliases=("the warrior", "Hero"),
        )
        assert entity.has_alias("the warrior") is True
        assert entity.has_alias("The Warrior") is True  # Case-insensitive
        assert entity.has_alias("hero") is True

    def test_has_alias_no_match(self):
        """Test has_alias returns False for non-matching."""
        entity = ExtractedEntity(
            name="Alice",
            entity_type=EntityType.CHARACTER,
            aliases=("the warrior",),
        )
        assert entity.has_alias("Bob") is False


class TestEntityMention:
    """Tests for EntityMention value object."""

    def test_mention_creation(self):
        """Test creating a valid mention."""
        mention = EntityMention(
            entity_name="Alice",
            mention_text="Alice",
            start_pos=0,
            end_pos=5,
            is_pronoun=False,
        )

        assert mention.entity_name == "Alice"
        assert mention.mention_text == "Alice"
        assert mention.start_pos == 0
        assert mention.end_pos == 5
        assert mention.is_pronoun is False

    def test_mention_length(self):
        """Test mention length property."""
        mention = EntityMention(
            entity_name="Alice",
            mention_text="Alice",
            start_pos=10,
            end_pos=15,
        )
        assert mention.length == 5

    def test_mention_validation_empty_text(self):
        """Test validation rejects empty mention text."""
        with pytest.raises(ValueError, match="Mention text"):
            EntityMention(
                entity_name="Alice",
                mention_text="",
                start_pos=0,
                end_pos=0,
            )

    def test_mention_validation_negative_start(self):
        """Test validation rejects negative start_pos."""
        with pytest.raises(ValueError, match="start_pos"):
            EntityMention(
                entity_name="Alice",
                mention_text="Alice",
                start_pos=-1,
                end_pos=5,
            )

    def test_mention_validation_end_before_start(self):
        """Test validation rejects end_pos < start_pos."""
        with pytest.raises(ValueError, match="end_pos"):
            EntityMention(
                entity_name="Alice",
                mention_text="Alice",
                start_pos=10,
                end_pos=5,
            )


class TestExtractionResult:
    """Tests for ExtractionResult value object."""

    def test_result_creation(self):
        """Test creating a valid result."""
        entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
            ExtractedEntity(name="Bob", entity_type=EntityType.CHARACTER),
        )
        mentions = (
            EntityMention(
                entity_name="Alice", mention_text="Alice", start_pos=0, end_pos=5
            ),
        )

        result = ExtractionResult(
            entities=entities,
            mentions=mentions,
            source_length=100,
            model_used="test-model",
            tokens_used=150,
        )

        assert result.entity_count == 2
        assert result.mention_count == 1
        assert result.source_length == 100
        assert result.model_used == "test-model"
        assert result.tokens_used == 150

    def test_get_entities_by_type(self):
        """Test filtering entities by type."""
        entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
            ExtractedEntity(name="Tavern", entity_type=EntityType.LOCATION),
            ExtractedEntity(name="Bob", entity_type=EntityType.CHARACTER),
        )
        result = ExtractionResult(entities=entities, mentions=(), source_length=100)

        characters = result.get_entities_by_type(EntityType.CHARACTER)
        locations = result.get_entities_by_type(EntityType.LOCATION)

        assert len(characters) == 2
        assert len(locations) == 1
        assert all(e.entity_type == EntityType.CHARACTER for e in characters)

    def test_get_entity_mentions(self):
        """Test getting mentions for a specific entity."""
        mentions = (
            EntityMention(
                entity_name="Alice", mention_text="Alice", start_pos=0, end_pos=5
            ),
            EntityMention(
                entity_name="Alice", mention_text="she", start_pos=10, end_pos=13
            ),
            EntityMention(
                entity_name="Bob", mention_text="Bob", start_pos=20, end_pos=23
            ),
        )
        result = ExtractionResult(entities=(), mentions=mentions, source_length=100)

        alice_mentions = result.get_entity_mentions("Alice")
        bob_mentions = result.get_entity_mentions("Bob")

        assert len(alice_mentions) == 2
        assert len(bob_mentions) == 1


class TestEntityExtractionService:
    """Tests for EntityExtractionService."""

    @pytest.mark.asyncio
    async def test_extract_success(self, entity_extraction_service):
        """Test successful entity extraction."""
        text = "Alice entered the Golden Dragon Tavern. She was a brave warrior."

        result = await entity_extraction_service.extract(text)

        assert result.entity_count == 5
        assert result.mention_count == 3
        assert result.source_length == len(text)

    @pytest.mark.asyncio
    async def test_extract_characters(self, entity_extraction_service):
        """Test extracting character entities."""
        text = "Alice entered the tavern."

        result = await entity_extraction_service.extract(text)
        characters = result.get_entities_by_type(EntityType.CHARACTER)

        assert len(characters) >= 1
        assert any(e.name == "Alice" for e in characters)

    @pytest.mark.asyncio
    async def test_extract_locations(self, entity_extraction_service):
        """Test extracting location entities."""
        text = "Alice entered the Golden Dragon Tavern."

        result = await entity_extraction_service.extract(text)
        locations = result.get_entities_by_type(EntityType.LOCATION)

        assert len(locations) >= 1
        assert any("tavern" in e.name.lower() or "tavern" in e.aliases for e in locations)

    @pytest.mark.asyncio
    async def test_extract_items(self, entity_extraction_service):
        """Test extracting item entities."""
        text = "Alice found The Rusty Sword in the tavern."

        result = await entity_extraction_service.extract(text)
        items = result.get_entities_by_type(EntityType.ITEM)

        assert len(items) >= 1
        assert any("sword" in e.name.lower() for e in items)

    @pytest.mark.asyncio
    async def test_extract_events(self, entity_extraction_service):
        """Test extracting event entities."""
        text = "They spoke of the Battle of Three Peaks."

        result = await entity_extraction_service.extract(text)
        events = result.get_entities_by_type(EntityType.EVENT)

        assert len(events) >= 1
        assert any("battle" in e.name.lower() for e in events)

    @pytest.mark.asyncio
    async def test_extract_organizations(self, entity_extraction_service):
        """Test extracting organization entities."""
        text = "She was a member of the Adventurers Guild."

        result = await entity_extraction_service.extract(text)
        organizations = result.get_entities_by_type(EntityType.ORGANIZATION)

        assert len(organizations) >= 1
        assert any("guild" in e.name.lower() for e in organizations)

    @pytest.mark.asyncio
    async def test_extract_with_custom_config(self, mock_llm_client):
        """Test extraction with custom configuration."""
        service = EntityExtractionService(
            llm_client=mock_llm_client,
            config=ExtractionConfig(
                confidence_threshold=0.9,
                max_entities=10,
            ),
        )
        text = "Alice entered the tavern."

        result = await service.extract(text)

        # With higher threshold, some entities may be filtered out
        assert result.entity_count <= 10

    @pytest.mark.asyncio
    async def test_extract_without_mentions(self, mock_llm_client):
        """Test extraction without mention extraction."""
        service = EntityExtractionService(
            llm_client=mock_llm_client,
            config=ExtractionConfig(include_mentions=False),
        )
        text = "Alice entered the tavern."

        result = await service.extract(text)

        assert result.mention_count == 0

    @pytest.mark.asyncio
    async def test_extract_llm_error(self, failing_llm_client):
        """Test extraction handles LLM errors."""
        service = EntityExtractionService(llm_client=failing_llm_client)
        text = "Alice entered the tavern."

        with pytest.raises(EntityExtractionError, match="LLM generation failed"):
            await service.extract(text)

    @pytest.mark.asyncio
    async def test_extract_invalid_json(self, invalid_json_llm_client):
        """Test extraction handles invalid JSON gracefully."""
        service = EntityExtractionService(llm_client=invalid_json_llm_client)
        text = "Alice entered the tavern."

        result = await service.extract(text)

        # Should return empty result on parse failure
        assert result.entity_count == 0
        assert result.mention_count == 0

    @pytest.mark.asyncio
    async def test_extract_markdown_json(self, markdown_json_llm_client):
        """Test extraction handles JSON wrapped in markdown code blocks."""
        service = EntityExtractionService(llm_client=markdown_json_llm_client)
        text = "Alice entered the tavern."

        result = await service.extract(text)

        # Should successfully extract from markdown-wrapped JSON
        assert result.entity_count > 0

    @pytest.mark.asyncio
    async def test_extract_batch(self, entity_extraction_service):
        """Test batch extraction of multiple texts."""
        texts = [
            "Alice entered the tavern.",
            "Bob drew his sword.",
            "The guild master watched.",
        ]

        results = await entity_extraction_service.extract_batch(texts)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_extract_with_alias_matching(self, entity_extraction_service):
        """Test that entity aliases work correctly."""
        text = "Alice entered the Golden Dragon Tavern."

        result = await entity_extraction_service.extract(text)

        # Find the tavern entity and check aliases
        tavern = next(
            (e for e in result.entities if "tavern" in e.name.lower()), None
        )
        assert tavern is not None
        assert tavern.has_alias("the tavern") or tavern.has_alias("the inn")


class TestPronounsConstant:
    """Tests for PRONOUNS constant."""

    def test_pronouns_set_populated(self):
        """Test that PRONOUNS contains expected values."""
        assert "he" in PRONOUNS
        assert "she" in PRONOUNS
        assert "it" in PRONOUNS
        assert "they" in PRONOUNS
        assert "him" in PRONOUNS
        assert "her" in PRONOUNS
        assert "them" in PRONOUNS

    def test_pronouns_are_lowercase(self):
        """Test that all pronouns are lowercase."""
        assert all(p.islower() for p in PRONOUNS)


@pytest.mark.unit
@pytest.mark.medium
class TestEntityExtractionServiceIntegration:
    """
    Integration-style tests that exercise the full extraction flow.

    These tests use mock LLM but test the complete pipeline from
    text input to ExtractionResult output.
    """

    @pytest.mark.asyncio
    async def test_full_extraction_pipeline(self, mock_llm_client):
        """Test the complete extraction pipeline with sample text."""
        service = EntityExtractionService(llm_client=mock_llm_client)
        text = "Alice entered the Golden Dragon Tavern. She was known as the warrior. The barkeep greeted her."

        result = await service.extract(text)

        # Verify result structure
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.entities, tuple)
        assert isinstance(result.mentions, tuple)
        assert result.source_length == len(text)
        assert result.model_used == "test-model"
        assert result.tokens_used == 150

        # Verify we got expected entity types
        entity_types = {e.entity_type for e in result.entities}
        assert EntityType.CHARACTER in entity_types
        assert EntityType.LOCATION in entity_types

        # Verify mention tracking
        alice_mentions = result.get_entity_mentions("Alice")
        assert len(alice_mentions) >= 1
