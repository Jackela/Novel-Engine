"""
Unit Tests for Entity Extraction Service

Warzone 4: AI Brain - BRAIN-029A

Tests for the entity extraction service that uses LLM to extract
named entities from narrative text (Characters, Locations, Items, Events, Organizations).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.contexts.knowledge.application.ports.i_llm_client import (
    ILLMClient,
    LLMError,
    LLMRequest,
    LLMResponse,
)
from src.contexts.knowledge.application.services.entity_extraction_service import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    EntityExtractionError,
    EntityExtractionService,
    ExtractionConfig,
)
from src.contexts.knowledge.domain.models.entity import (
    DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_ENTITIES,
    PRONOUNS,
    EntityMention,
    EntityType,
    ExtractedEntity,
    ExtractionResult,
    ExtractionResultWithRelationships,
    Relationship,
    RelationshipType,
)

# Sample LLM response for entity extraction

pytestmark = pytest.mark.unit

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
            text=f"Here is the extracted data:\n```json\n{SAMPLE_EXTRACTION_JSON}\n```",
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
        assert any(
            "tavern" in e.name.lower() or "tavern" in e.aliases for e in locations
        )

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
        tavern = next((e for e in result.entities if "tavern" in e.name.lower()), None)
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


# Relationship extraction samples and fixtures
SAMPLE_RELATIONSHIP_JSON = """{
  "relationships": [
    {
      "source": "Alice",
      "target": "Bob",
      "type": "killed",
      "context": "Alice killed Bob with a single strike",
      "strength": 1.0,
      "bidirectional": false,
      "temporal": ""
    },
    {
      "source": "Alice",
      "target": "The Rusty Sword",
      "type": "owns",
      "context": "Alice wielded The Rusty Sword",
      "strength": 0.9,
      "bidirectional": false,
      "temporal": ""
    },
    {
      "source": "Alice",
      "target": "Golden Dragon Tavern",
      "type": "located_at",
      "context": "Alice was at the Golden Dragon Tavern",
      "strength": 1.0,
      "bidirectional": false,
      "temporal": "during chapter 1"
    },
    {
      "source": "Alice",
      "target": "Bob",
      "type": "knows",
      "context": "Alice and Bob were old friends",
      "strength": 0.8,
      "bidirectional": true,
      "temporal": ""
    },
    {
      "source": "Bob",
      "target": "Adventurers Guild",
      "type": "member_of",
      "context": "Bob was a member of the Adventurers Guild",
      "strength": 1.0,
      "bidirectional": false,
      "temporal": ""
    }
  ]
}"""


@pytest.fixture
def relationship_llm_client():
    """Create a mock LLM client that returns relationship data."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        # Check if this is a relationship extraction request by the prompt content
        if "relationships" in request.system_prompt.lower():
            return LLMResponse(
                text=SAMPLE_RELATIONSHIP_JSON,
                model="test-model",
                tokens_used=100,
            )
        else:
            # Return entity data for entity extraction
            # Include Bob and Carol as entities for relationship tests
            return LLMResponse(
                text="""{
  "entities": [
    {
      "name": "Alice",
      "type": "character",
      "aliases": ["the warrior"],
      "description": "A brave warrior",
      "first_appearance": 0,
      "confidence": 0.95
    },
    {
      "name": "Bob",
      "type": "character",
      "aliases": [],
      "description": "Alice's adversary",
      "first_appearance": 20,
      "confidence": 0.90
    },
    {
      "name": "Carol",
      "type": "character",
      "aliases": [],
      "description": "Another character",
      "first_appearance": 40,
      "confidence": 0.90
    },
    {
      "name": "The Rusty Sword",
      "type": "item",
      "aliases": [],
      "description": "An ancient weapon",
      "first_appearance": 30,
      "confidence": 0.88
    },
    {
      "name": "Golden Dragon Tavern",
      "type": "location",
      "aliases": ["the tavern"],
      "description": "A tavern",
      "first_appearance": 10,
      "confidence": 0.92
    },
    {
      "name": "Adventurers Guild",
      "type": "organization",
      "aliases": ["the guild"],
      "description": "An organization",
      "first_appearance": 50,
      "confidence": 0.90
    }
  ],
  "mentions": []
}""",
                model="test-model",
                tokens_used=150,
            )

    client.generate = mock_generate
    return client


class TestRelationshipType:
    """Tests for RelationshipType enum."""

    def test_all_relationship_types_defined(self):
        """Test that expected relationship types are defined."""
        assert RelationshipType.KNOWS.value == "knows"
        assert RelationshipType.KILLED.value == "killed"
        assert RelationshipType.LOVES.value == "loves"
        assert RelationshipType.HATES.value == "hates"
        assert RelationshipType.PARENT_OF.value == "parent_of"
        assert RelationshipType.CHILD_OF.value == "child_of"
        assert RelationshipType.MEMBER_OF.value == "member_of"
        assert RelationshipType.LEADS.value == "leads"
        assert RelationshipType.SERVES.value == "serves"
        assert RelationshipType.OWNS.value == "owns"
        assert RelationshipType.LOCATED_AT.value == "located_at"
        assert RelationshipType.OCCURRED_AT.value == "occurred_at"
        assert RelationshipType.PARTICIPATED_IN.value == "participated_in"
        assert RelationshipType.ALLIED_WITH.value == "allied_with"
        assert RelationshipType.ENEMY_OF.value == "enemy_of"
        assert RelationshipType.MENTORED.value == "mentored"
        assert RelationshipType.OTHER.value == "other"

    def test_relationship_type_from_string(self):
        """Test creating RelationshipType from string values."""
        assert RelationshipType("knows") == RelationshipType.KNOWS
        assert RelationshipType("killed") == RelationshipType.KILLED
        assert RelationshipType("loves") == RelationshipType.LOVES


class TestRelationship:
    """Tests for Relationship value object."""

    def test_relationship_creation(self):
        """Test creating a valid relationship."""
        relationship = Relationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KILLED,
            context="Alice killed Bob in battle",
            strength=1.0,
        )

        assert relationship.source == "Alice"
        assert relationship.target == "Bob"
        assert relationship.relationship_type == RelationshipType.KILLED
        assert relationship.context == "Alice killed Bob in battle"
        assert relationship.strength == 1.0
        assert relationship.bidirectional is False

    def test_relationship_validation_empty_source(self):
        """Test validation rejects empty source."""
        with pytest.raises(ValueError, match="Source"):
            Relationship(
                source="",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )

    def test_relationship_validation_empty_target(self):
        """Test validation rejects empty target."""
        with pytest.raises(ValueError, match="Target"):
            Relationship(
                source="Alice",
                target="",
                relationship_type=RelationshipType.KNOWS,
            )

    def test_relationship_validation_strength_too_low(self):
        """Test validation rejects strength < 0."""
        with pytest.raises(ValueError, match="Strength"):
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                strength=-0.1,
            )

    def test_relationship_validation_strength_too_high(self):
        """Test validation rejects strength > 1."""
        with pytest.raises(ValueError, match="Strength"):
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                strength=1.1,
            )

    def test_is_self_relationship(self):
        """Test self-relationship detection."""
        self_rel = Relationship(
            source="Alice",
            target="Alice",
            relationship_type=RelationshipType.KNOWS,
        )
        normal_rel = Relationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KNOWS,
        )

        assert self_rel.is_self_relationship is True
        assert normal_rel.is_self_relationship is False

    def test_invert_parent_child(self):
        """Test inverting parent-child relationship."""
        parent_rel = Relationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.PARENT_OF,
        )

        inverted = parent_rel.invert()

        assert inverted.source == "Bob"
        assert inverted.target == "Alice"
        assert inverted.relationship_type == RelationshipType.CHILD_OF

    def test_invert_kills(self):
        """Test inverting kill relationship (no inverse type)."""
        kill_rel = Relationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KILLED,
        )

        inverted = kill_rel.invert()

        assert inverted.source == "Bob"
        assert inverted.target == "Alice"
        # KILLED has no inverse, so type stays the same
        assert inverted.relationship_type == RelationshipType.KILLED

    def test_invert_symmetric(self):
        """Test inverting symmetric relationship (type stays same)."""
        knows_rel = Relationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KNOWS,
        )

        inverted = knows_rel.invert()

        assert inverted.source == "Bob"
        assert inverted.target == "Alice"
        assert inverted.relationship_type == RelationshipType.KNOWS


class TestExtractionResultWithRelationships:
    """Tests for ExtractionResultWithRelationships."""

    def test_result_with_relationships_creation(self):
        """Test creating result with relationships."""
        entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
            ExtractedEntity(name="Bob", entity_type=EntityType.CHARACTER),
        )
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KILLED,
            ),
        )

        result = ExtractionResultWithRelationships(
            entities=entities,
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        assert result.entity_count == 2
        assert result.relationship_count == 1

    def test_get_relationships_for_entity(self):
        """Test getting relationships for a specific entity."""
        relationships = (
            Relationship(
                source="Alice", target="Bob", relationship_type=RelationshipType.KILLED
            ),
            Relationship(
                source="Bob", target="Carol", relationship_type=RelationshipType.KNOWS
            ),
            Relationship(
                source="Carol", target="Alice", relationship_type=RelationshipType.LOVES
            ),
        )

        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        alice_rels = result.get_relationships_for_entity("Alice")
        bob_rels = result.get_relationships_for_entity("Bob")

        # Alice is source of one, target of another
        assert len(alice_rels) == 2
        # Bob is target of one, source of another
        assert len(bob_rels) == 2

    def test_get_relationships_by_type(self):
        """Test filtering relationships by type."""
        relationships = (
            Relationship(
                source="Alice", target="Bob", relationship_type=RelationshipType.KILLED
            ),
            Relationship(
                source="Carol", target="Dave", relationship_type=RelationshipType.KILLED
            ),
            Relationship(
                source="Alice", target="Carol", relationship_type=RelationshipType.KNOWS
            ),
        )

        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        killed_rels = result.get_relationships_by_type(RelationshipType.KILLED)
        knows_rels = result.get_relationships_by_type(RelationshipType.KNOWS)

        assert len(killed_rels) == 2
        assert len(knows_rels) == 1

    def test_find_relationship(self):
        """Test finding relationships between specific entities."""
        relationships = (
            Relationship(
                source="Alice", target="Bob", relationship_type=RelationshipType.KILLED
            ),
            Relationship(
                source="Alice", target="Bob", relationship_type=RelationshipType.KNOWS
            ),
            Relationship(
                source="Alice", target="Carol", relationship_type=RelationshipType.KNOWS
            ),
        )

        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        # Find all relationships between Alice and Bob
        alice_bob_rels = result.find_relationship("Alice", "Bob")
        assert len(alice_bob_rels) == 2

        # Find specific type
        killed_rel = result.find_relationship("Alice", "Bob", RelationshipType.KILLED)
        assert len(killed_rel) == 1

        # Find non-existent relationships
        none_rel = result.find_relationship("Bob", "Carol")
        assert len(none_rel) == 0


class TestRelationshipExtraction:
    """Tests for relationship extraction in EntityExtractionService."""

    @pytest.mark.asyncio
    async def test_extract_with_relationships_success(self, relationship_llm_client):
        """Test successful extraction of entities and relationships."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = "Alice killed Bob with a single strike at the Golden Dragon Tavern."

        result = await service.extract_with_relationships(text)

        assert isinstance(result, ExtractionResultWithRelationships)
        assert result.entity_count > 0
        assert result.relationship_count > 0

    @pytest.mark.asyncio
    async def test_extract_with_relationships_filters_by_strength(
        self, relationship_llm_client
    ):
        """Test that relationships below strength threshold are filtered."""
        service = EntityExtractionService(
            llm_client=relationship_llm_client,
            config=ExtractionConfig(relationship_strength_threshold=0.95),
        )
        text = "Alice killed Bob."

        result = await service.extract_with_relationships(text)

        # Only relationships with strength >= 0.95 should be included
        for rel in result.relationships:
            assert rel.strength >= 0.95

    @pytest.mark.asyncio
    async def test_extract_with_relationships_max_limit(self, relationship_llm_client):
        """Test that max_relationships limit is respected."""
        service = EntityExtractionService(
            llm_client=relationship_llm_client,
            config=ExtractionConfig(max_relationships=2),
        )
        text = "Alice killed Bob. Alice loves Carol. Bob hates Dave."

        result = await service.extract_with_relationships(text)

        assert result.relationship_count <= 2

    @pytest.mark.asyncio
    async def test_extract_with_relationships_ignores_unknown_entities(
        self, mock_llm_client
    ):
        """Test that relationships referencing unknown entities are skipped."""
        client = mock_llm_client

        async def mock_generate(request: LLMRequest) -> LLMResponse:
            if "relationships" in request.system_prompt.lower():
                return LLMResponse(
                    text='{"relationships": ['
                    '{"source": "Alice", "target": "UnknownPerson", '
                    '"type": "knows", "strength": 1.0}'
                    "]}",
                    model="test-model",
                    tokens_used=50,
                )
            return LLMResponse(
                text=SAMPLE_EXTRACTION_JSON,
                model="test-model",
                tokens_used=150,
            )

        client.generate = mock_generate

        service = EntityExtractionService(llm_client=client)
        result = await service.extract_with_relationships("Alice entered the tavern.")

        # Relationship to UnknownPerson should be skipped
        assert result.relationship_count == 0

    @pytest.mark.asyncio
    async def test_extract_with_relationships_handles_parse_failure(
        self, mock_llm_client
    ):
        """Test that relationship parse failure returns entities only."""
        client = mock_llm_client

        async def mock_generate(request: LLMRequest) -> LLMResponse:
            if "relationships" in request.system_prompt.lower():
                return LLMResponse(
                    text="Invalid JSON response",
                    model="test-model",
                )
            return LLMResponse(
                text=SAMPLE_EXTRACTION_JSON,
                model="test-model",
                tokens_used=150,
            )

        client.generate = mock_generate

        service = EntityExtractionService(llm_client=client)
        result = await service.extract_with_relationships("Alice entered the tavern.")

        # Should return entities even if relationship parsing fails
        assert result.entity_count > 0
        assert result.relationship_count == 0

    @pytest.mark.asyncio
    async def test_extract_killed_relationship(self, relationship_llm_client):
        """Test extracting 'killed' relationship."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = "Alice killed Bob with a single strike."

        result = await service.extract_with_relationships(text)

        killed_rels = result.get_relationships_by_type(RelationshipType.KILLED)
        assert len(killed_rels) > 0
        assert killed_rels[0].source == "Alice"
        assert killed_rels[0].target == "Bob"

    @pytest.mark.asyncio
    async def test_extract_knows_relationship(self, relationship_llm_client):
        """Test extracting 'knows' relationship."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = "Alice and Bob were old friends."

        result = await service.extract_with_relationships(text)

        knows_rels = result.get_relationships_by_type(RelationshipType.KNOWS)
        assert len(knows_rels) > 0

    @pytest.mark.asyncio
    async def test_extract_owns_relationship(self, relationship_llm_client):
        """Test extracting 'owns' relationship."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = "Alice wielded The Rusty Sword."

        result = await service.extract_with_relationships(text)

        owns_rels = result.get_relationships_by_type(RelationshipType.OWNS)
        assert len(owns_rels) > 0

    @pytest.mark.asyncio
    async def test_extract_member_of_relationship(self, relationship_llm_client):
        """Test extracting 'member_of' relationship."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = "Bob was a member of the Adventurers Guild."

        result = await service.extract_with_relationships(text)

        member_rels = result.get_relationships_by_type(RelationshipType.MEMBER_OF)
        assert len(member_rels) > 0

    @pytest.mark.asyncio
    async def test_extract_located_at_relationship(self, relationship_llm_client):
        """Test extracting 'located_at' relationship."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = "Alice was at the Golden Dragon Tavern."

        result = await service.extract_with_relationships(text)

        located_rels = result.get_relationships_by_type(RelationshipType.LOCATED_AT)
        assert len(located_rels) > 0


@pytest.mark.unit
@pytest.mark.medium
class TestRelationshipExtractionIntegration:
    """Integration tests for relationship extraction."""

    @pytest.mark.asyncio
    async def test_full_relationship_extraction_pipeline(self, relationship_llm_client):
        """Test the complete relationship extraction pipeline."""
        service = EntityExtractionService(llm_client=relationship_llm_client)
        text = """
        Alice entered the Golden Dragon Tavern. She was looking for Bob,
        who had killed her father. Little did she know, Bob was also there,
        sitting in the corner with his sword The Rusty Sword.
        """

        result = await service.extract_with_relationships(text)

        # Verify result structure
        assert isinstance(result, ExtractionResultWithRelationships)
        assert result.entity_count > 0
        assert result.source_length == len(text)

        # Verify we can query relationships
        if result.relationship_count > 0:
            # Check that relationships have valid source/target
            for rel in result.relationships:
                assert rel.source
                assert rel.target
                assert isinstance(rel.relationship_type, RelationshipType)
                assert 0.0 <= rel.strength <= 1.0


@pytest.mark.unit
@pytest.mark.medium
class TestBidirectionalRelationshipNormalization:
    """Tests for BRAIN-030B: Bidirectional relationship normalization."""

    def test_normalize_bidirectional_symmetric_knows(self):
        """Test normalization adds inverse for symmetric KNOWS relationship."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                bidirectional=False,
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        normalized = result.normalize_bidirectional()

        # Should add Bob -> Alice relationship
        assert normalized.relationship_count == 2
        alice_to_bob = [
            r
            for r in normalized.relationships
            if r.source == "Alice" and r.target == "Bob"
        ]
        bob_to_alice = [
            r
            for r in normalized.relationships
            if r.source == "Bob" and r.target == "Alice"
        ]
        assert len(alice_to_bob) == 1
        assert len(bob_to_alice) == 1
        assert bob_to_alice[0].relationship_type == RelationshipType.KNOWS

    def test_normalize_bidirectional_symmetric_allied_with(self):
        """Test normalization adds inverse for ALLIED_WITH relationship."""
        relationships = (
            Relationship(
                source="Kingdom A",
                target="Kingdom B",
                relationship_type=RelationshipType.ALLIED_WITH,
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        normalized = result.normalize_bidirectional()

        assert normalized.relationship_count == 2
        b_to_a = [
            r
            for r in normalized.relationships
            if r.source == "Kingdom B" and r.target == "Kingdom A"
        ]
        assert len(b_to_a) == 1
        assert b_to_a[0].relationship_type == RelationshipType.ALLIED_WITH

    def test_normalize_bidirectional_explicit_flag(self):
        """Test normalization respects explicit bidirectional flag with inverse type."""
        # Use PARENT_OF which has an inverse type defined
        relationships = (
            Relationship(
                source="Arthur",
                target="Mordred",
                relationship_type=RelationshipType.PARENT_OF,
                bidirectional=True,  # Explicitly bidirectional
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        normalized = result.normalize_bidirectional()

        # Should add inverse with CHILD_OF type
        assert normalized.relationship_count == 2
        child_of_rel = [
            r
            for r in normalized.relationships
            if r.source == "Mordred" and r.target == "Arthur"
        ]
        assert len(child_of_rel) == 1
        assert child_of_rel[0].relationship_type == RelationshipType.CHILD_OF

    def test_normalize_bidirectional_no_duplicates(self):
        """Test normalization doesn't create duplicates if both directions exist."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            ),
            Relationship(
                source="Bob",
                target="Alice",
                relationship_type=RelationshipType.KNOWS,
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        normalized = result.normalize_bidirectional()

        # Should not add duplicates
        assert normalized.relationship_count == 2

    def test_normalize_bidirectional_parent_child(self):
        """Test normalization for PARENT_OF -> CHILD_OF pair."""
        relationships = (
            Relationship(
                source="Arthur",
                target="Mordred",
                relationship_type=RelationshipType.PARENT_OF,
                bidirectional=True,
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        normalized = result.normalize_bidirectional()

        # Should add Mordred -> Arthur with CHILD_OF type
        assert normalized.relationship_count == 2
        child_of_rel = [
            r
            for r in normalized.relationships
            if r.source == "Mordred" and r.target == "Arthur"
        ]
        assert len(child_of_rel) == 1
        assert child_of_rel[0].relationship_type == RelationshipType.CHILD_OF

    def test_normalize_bidirectional_empty_relationships(self):
        """Test normalization handles empty relationships."""
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=(),
        )

        normalized = result.normalize_bidirectional()

        assert normalized.relationship_count == 0

    def test_is_naturally_bidirectional(self):
        """Test is_naturally_bidirectional function."""
        from src.contexts.knowledge.domain.models.entity import (
            is_naturally_bidirectional,
        )

        assert is_naturally_bidirectional(RelationshipType.KNOWS) is True
        assert is_naturally_bidirectional(RelationshipType.ALLIED_WITH) is True
        assert is_naturally_bidirectional(RelationshipType.ENEMY_OF) is True
        assert is_naturally_bidirectional(RelationshipType.LOVES) is True
        assert is_naturally_bidirectional(RelationshipType.HATES) is True
        assert is_naturally_bidirectional(RelationshipType.LOCATED_AT) is True

        assert is_naturally_bidirectional(RelationshipType.KILLED) is False
        assert is_naturally_bidirectional(RelationshipType.PARENT_OF) is False
        assert is_naturally_bidirectional(RelationshipType.LEADS) is False


@pytest.mark.unit
@pytest.mark.medium
class TestTemporalRelationships:
    """Tests for BRAIN-030B: Temporal relationship filtering."""

    def test_filter_by_temporal_exact_match(self):
        """Test filtering by exact temporal marker."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Alice",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 2",
            ),
            Relationship(
                source="Bob",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="",  # No temporal info
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        filtered = result.filter_by_temporal(temporal_marker="during chapter 1")

        assert filtered.relationship_count == 1
        assert filtered.relationships[0].target == "Bob"

    def test_filter_by_temporal_contains_substring(self):
        """Test filtering by temporal marker substring."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Alice",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="before the battle of chapter 1",
            ),
            Relationship(
                source="Bob",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="after chapter 2",
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        filtered = result.filter_by_temporal(contains_marker="chapter 1")

        assert filtered.relationship_count == 2

    def test_filter_by_temporal_empty_marker(self):
        """Test filtering for relationships without temporal info."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Bob",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="",  # No temporal info
            ),
            Relationship(
                source="Charlie",
                target="Dave",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="",  # No temporal info
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        filtered = result.filter_by_temporal(temporal_marker="")

        assert filtered.relationship_count == 2

    def test_filter_by_temporal_no_filter(self):
        """Test that no filter returns all relationships."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        filtered = result.filter_by_temporal()

        assert filtered.relationship_count == 1

    def test_get_temporal_markers(self):
        """Test getting all unique temporal markers."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Alice",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",  # Duplicate
            ),
            Relationship(
                source="Bob",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="before the battle",
            ),
            Relationship(
                source="Charlie",
                target="Dave",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="",  # Empty marker excluded
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        markers = result.get_temporal_markers()

        assert len(markers) == 2
        assert "before the battle" in markers
        assert "during chapter 1" in markers

    def test_get_relationships_at_time(self):
        """Test getting relationships valid at a specific time."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Alice",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 2",
            ),
            Relationship(
                source="Bob",
                target="Charlie",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="",  # No temporal info - assumed always valid
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        chapter1_rels = result.get_relationships_at_time("chapter 1")

        # Should match "during chapter 1" and empty marker (always valid)
        assert len(chapter1_rels) == 2

    def test_has_temporal_relationship(self):
        """Test checking if entity has temporal relationships."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Charlie",
                target="Dave",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="",  # No temporal info
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        assert result.has_temporal_relationship("Alice") is True
        assert result.has_temporal_relationship("Bob") is True
        assert result.has_temporal_relationship("Charlie") is False
        assert result.has_temporal_relationship("Dave") is False

    def test_combined_bidirectional_and_temporal(self):
        """Test combining bidirectional normalization with temporal filtering."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 1",
            ),
            Relationship(
                source="Charlie",
                target="Dave",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="during chapter 2",
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        # First normalize, then filter
        normalized = result.normalize_bidirectional()
        chapter1_rels = normalized.filter_by_temporal(contains_marker="chapter 1")

        # Should have Alice->Bob and Bob->Alice for chapter 1
        assert chapter1_rels.relationship_count == 2

    def test_temporal_case_insensitive(self):
        """Test temporal filtering is case-insensitive."""
        relationships = (
            Relationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                temporal_marker="During Chapter 1",
            ),
        )
        result = ExtractionResultWithRelationships(
            entities=(),
            mentions=(),
            source_length=100,
            relationships=relationships,
        )

        # Different cases should match
        filtered1 = result.filter_by_temporal(contains_marker="chapter 1")
        filtered2 = result.filter_by_temporal(contains_marker="CHAPTER 1")
        filtered3 = result.filter_by_temporal(contains_marker="Chapter 1")

        assert filtered1.relationship_count == 1
        assert filtered2.relationship_count == 1
        assert filtered3.relationship_count == 1
