"""
Test suite for Entity Extraction Service.

Tests entity extraction from narrative text and relationship extraction.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch

from src.contexts.knowledge.application.services.entity_extraction_service import (
    EntityExtractionService,
    ExtractionConfig,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
)
from src.contexts.knowledge.domain.models.entity import (
    EntityType,
    RelationshipType,
    ExtractedEntity,
    EntityMention,
    ExtractionResult,
    ExtractionResultWithRelationships,
    Relationship,
)
from src.contexts.knowledge.domain.errors import ValidationError, ExtractionError
from src.contexts.knowledge.application.ports.i_llm_client import ILLMClient, LLMRequest, LLMResponse


class TestExtractionConfig:
    """Tests for ExtractionConfig dataclass."""

    def test_default_config(self):
        """Test default extraction configuration."""
        config = ExtractionConfig()
        
        assert config.confidence_threshold == 0.5
        assert config.max_entities == 50
        assert config.include_mentions is True
        assert config.extract_relationships is False
        assert config.max_relationships == 30
        assert config.relationship_strength_threshold == 0.3
        assert config.temperature == DEFAULT_TEMPERATURE
        assert config.max_tokens == DEFAULT_MAX_TOKENS

    def test_custom_config(self):
        """Test custom extraction configuration."""
        config = ExtractionConfig(
            confidence_threshold=0.7,
            max_entities=20,
            include_mentions=False,
            extract_relationships=True,
            max_relationships=50,
            relationship_strength_threshold=0.5,
            temperature=0.5,
            max_tokens=3000,
        )
        
        assert config.confidence_threshold == 0.7
        assert config.max_entities == 20
        assert config.include_mentions is False
        assert config.extract_relationships is True
        assert config.max_relationships == 50
        assert config.relationship_strength_threshold == 0.5
        assert config.temperature == 0.5
        assert config.max_tokens == 3000

    def test_config_validates_confidence_threshold_min(self):
        """Test config validates confidence threshold minimum."""
        with pytest.raises(ValueError, match="confidence_threshold"):
            ExtractionConfig(confidence_threshold=-0.1)

    def test_config_validates_confidence_threshold_max(self):
        """Test config validates confidence threshold maximum."""
        with pytest.raises(ValueError, match="confidence_threshold"):
            ExtractionConfig(confidence_threshold=1.1)

    def test_config_validates_max_entities_min(self):
        """Test config validates max_entities minimum."""
        with pytest.raises(ValueError, match="max_entities"):
            ExtractionConfig(max_entities=0)

    def test_config_validates_max_entities_max(self):
        """Test config validates max_entities maximum."""
        with pytest.raises(ValueError, match="max_entities"):
            ExtractionConfig(max_entities=101)

    def test_config_validates_max_relationships_min(self):
        """Test config validates max_relationships minimum."""
        with pytest.raises(ValueError, match="max_relationships"):
            ExtractionConfig(max_relationships=0)

    def test_config_validates_max_relationships_max(self):
        """Test config validates max_relationships maximum."""
        with pytest.raises(ValueError, match="max_relationships"):
            ExtractionConfig(max_relationships=101)

    def test_config_validates_relationship_strength_threshold(self):
        """Test config validates relationship strength threshold."""
        with pytest.raises(ValueError, match="relationship_strength_threshold"):
            ExtractionConfig(relationship_strength_threshold=1.5)

    def test_config_validates_temperature_min(self):
        """Test config validates temperature minimum."""
        with pytest.raises(ValueError, match="temperature"):
            ExtractionConfig(temperature=-0.1)

    def test_config_validates_temperature_max(self):
        """Test config validates temperature maximum."""
        with pytest.raises(ValueError, match="temperature"):
            ExtractionConfig(temperature=2.1)


class TestEntityExtractionServiceInitialization:
    """Tests for EntityExtractionService initialization."""

    def test_initialization_with_default_config(self):
        """Test initialization with default config."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        assert service._llm_client == mock_llm
        assert isinstance(service._config, ExtractionConfig)

    def test_initialization_with_custom_config(self):
        """Test initialization with custom config."""
        mock_llm = Mock(spec=ILLMClient)
        custom_config = ExtractionConfig(max_entities=10)
        service = EntityExtractionService(llm_client=mock_llm, config=custom_config)
        
        assert service._config.max_entities == 10


@pytest.mark.asyncio
class TestEntityExtractionServiceExtract:
    """Tests for entity extraction."""

    @pytest_asyncio.fixture
    async def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock(spec=ILLMClient)
        client.generate = AsyncMock(return_value=LLMResponse(
            text='{"entities": [{"name": "Alice", "type": "character", "aliases": ["Ali"], "description": "Main character", "first_appearance": 0}], "mentions": [{"entity_name": "Alice", "mention_text": "Alice", "start_pos": 0, "end_pos": 5, "is_pronoun": false}]}',
            model="test-model",
            tokens_used=100,
        ))
        return client

    @pytest_asyncio.fixture
    async def extraction_service(self, mock_llm_client):
        """Create extraction service."""
        return EntityExtractionService(llm_client=mock_llm_client)

    async def test_extract_success(self, extraction_service):
        """Test successful entity extraction."""
        result = await extraction_service.extract("Alice went to the store.")
        
        assert result.is_ok
        assert result.value.entity_count > 0

    async def test_extract_empty_text(self, extraction_service):
        """Test extraction with empty text."""
        result = await extraction_service.extract("")
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    async def test_extract_whitespace_text(self, extraction_service):
        """Test extraction with whitespace-only text."""
        result = await extraction_service.extract("   ")
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    async def test_extract_non_string_text(self, extraction_service):
        """Test extraction with non-string text."""
        result = await extraction_service.extract(123)
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    async def test_extract_llm_failure(self, extraction_service, mock_llm_client):
        """Test extraction when LLM fails."""
        mock_llm_client.generate = AsyncMock(side_effect=Exception("LLM error"))
        
        result = await extraction_service.extract("Test text.")
        
        assert result.is_error
        assert isinstance(result.error, ExtractionError)

    async def test_extract_invalid_json_response(self, extraction_service, mock_llm_client):
        """Test extraction with invalid JSON response."""
        mock_llm_client.generate = AsyncMock(return_value=LLMResponse(
            text="Not valid JSON",
            model="test-model",
            tokens_used=50,
        ))
        
        result = await extraction_service.extract("Test text.")
        
        # Should return empty result on parse failure
        assert result.is_ok
        assert result.value.entity_count == 0

    async def test_extract_with_custom_config(self, extraction_service):
        """Test extraction with custom config."""
        custom_config = ExtractionConfig(confidence_threshold=0.8)
        
        result = await extraction_service.extract(
            "Alice went to the store.",
            config=custom_config,
        )
        
        assert result.is_ok

    async def test_extract_entities_filtered_by_confidence(self, extraction_service, mock_llm_client):
        """Test that entities are filtered by confidence threshold."""
        mock_llm_client.generate = AsyncMock(return_value=LLMResponse(
            text='{"entities": [{"name": "Alice", "type": "character", "confidence": 0.9}, {"name": "Bob", "type": "character", "confidence": 0.3}], "mentions": []}',
            model="test-model",
            tokens_used=100,
        ))
        
        result = await extraction_service.extract(
            "Test text.",
            config=ExtractionConfig(confidence_threshold=0.5),
        )
        
        assert result.is_ok
        # Only Alice should pass the confidence filter
        assert result.value.entity_count == 1


@pytest.mark.asyncio
class TestEntityExtractionServiceBatch:
    """Tests for batch entity extraction."""

    @pytest_asyncio.fixture
    async def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock(spec=ILLMClient)
        client.generate = AsyncMock(return_value=LLMResponse(
            text='{"entities": [{"name": "Test", "type": "character"}], "mentions": []}',
            model="test-model",
            tokens_used=50,
        ))
        return client

    @pytest_asyncio.fixture
    async def extraction_service(self, mock_llm_client):
        """Create extraction service."""
        return EntityExtractionService(llm_client=mock_llm_client)

    async def test_extract_batch_success(self, extraction_service):
        """Test successful batch extraction."""
        texts = ["Text one.", "Text two."]
        
        result = await extraction_service.extract_batch(texts)
        
        assert result.is_ok
        assert len(result.value) == 2

    async def test_extract_batch_invalid_input(self, extraction_service):
        """Test batch extraction with invalid input."""
        result = await extraction_service.extract_batch("not a list")
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    async def test_extract_batch_empty_list(self, extraction_service):
        """Test batch extraction with empty list."""
        result = await extraction_service.extract_batch([])
        
        assert result.is_ok
        assert len(result.value) == 0

    async def test_extract_batch_partial_failure(self, extraction_service, mock_llm_client):
        """Test batch extraction with partial failure."""
        mock_llm_client.generate = AsyncMock(side_effect=[
            LLMResponse(text='{"entities": [], "mentions": []}', model="test-model", tokens_used=50),
            Exception("LLM error"),
        ])
        
        result = await extraction_service.extract_batch(["Text one.", "Text two."])
        
        assert result.is_ok
        assert len(result.value) == 2
        # Second result should be empty due to failure
        assert result.value[1].entity_count == 0


@pytest.mark.asyncio
class TestEntityExtractionServiceLargeText:
    """Tests for large text extraction."""

    @pytest_asyncio.fixture
    async def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock(spec=ILLMClient)
        client.generate = AsyncMock(return_value=LLMResponse(
            text='{"entities": [{"name": "Test", "type": "character"}], "mentions": []}',
            model="test-model",
            tokens_used=50,
        ))
        return client

    @pytest_asyncio.fixture
    async def extraction_service(self, mock_llm_client):
        """Create extraction service."""
        return EntityExtractionService(llm_client=mock_llm_client)

    async def test_extract_large_text_success(self, extraction_service):
        """Test successful large text extraction."""
        large_text = "Test content. " * 1000  # Create large text
        
        result = await extraction_service.extract_large_text(large_text)
        
        assert result.is_ok

    async def test_extract_large_text_small_text(self, extraction_service, mock_llm_client):
        """Test large text extraction with small text (no chunking needed)."""
        small_text = "Small text."
        
        result = await extraction_service.extract_large_text(small_text)
        
        assert result.is_ok
        # Should call extract directly for small texts

    async def test_extract_large_text_invalid_chunk_size(self, extraction_service):
        """Test large text extraction with invalid chunk size."""
        result = await extraction_service.extract_large_text(
            "Text.",
            chunk_size=50,  # Too small
        )
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    async def test_extract_large_text_invalid_overlap(self, extraction_service):
        """Test large text extraction with invalid overlap."""
        result = await extraction_service.extract_large_text(
            "Text.",
            chunk_size=1000,
            overlap=1500,  # Larger than chunk_size
        )
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    async def test_extract_large_text_negative_overlap(self, extraction_service):
        """Test large text extraction with negative overlap."""
        result = await extraction_service.extract_large_text(
            "Text.",
            chunk_size=1000,
            overlap=-100,
        )
        
        assert result.is_error
        assert isinstance(result.error, ValidationError)


@pytest.mark.asyncio
class TestEntityExtractionServiceRelationships:
    """Tests for relationship extraction."""

    @pytest_asyncio.fixture
    async def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock(spec=ILLMClient)
        
        async def mock_generate(request):
            if "relationship" in request.system_prompt.lower():
                return LLMResponse(
                    text='{"relationships": [{"source": "Alice", "target": "Bob", "type": "knows", "context": "They met", "strength": 0.9, "bidirectional": true}]}',
                    model="test-model",
                    tokens_used=50,
                )
            else:
                return LLMResponse(
                    text='{"entities": [{"name": "Alice", "type": "character"}, {"name": "Bob", "type": "character"}], "mentions": []}',
                    model="test-model",
                    tokens_used=100,
                )
        
        client.generate = AsyncMock(side_effect=mock_generate)
        return client

    @pytest_asyncio.fixture
    async def extraction_service(self, mock_llm_client):
        """Create extraction service."""
        return EntityExtractionService(llm_client=mock_llm_client)

    async def test_extract_with_relationships_success(self, extraction_service):
        """Test successful relationship extraction."""
        result = await extraction_service.extract_with_relationships(
            "Alice and Bob are friends.",
        )
        
        assert result.is_ok
        assert isinstance(result.value, ExtractionResultWithRelationships)

    async def test_extract_with_relationships_empty_text(self, extraction_service):
        """Test relationship extraction with empty text."""
        result = await extraction_service.extract_with_relationships("")
        
        assert result.is_error

    async def test_extract_with_relationships_llm_failure(self, extraction_service, mock_llm_client):
        """Test relationship extraction when relationship LLM call fails."""
        async def failing_generate(request):
            if "relationship" in request.system_prompt.lower():
                raise Exception("Relationship extraction failed")
            else:
                return LLMResponse(
                    text='{"entities": [{"name": "Alice", "type": "character"}], "mentions": []}',
                    model="test-model",
                    tokens_used=50,
                )
        
        mock_llm_client.generate = AsyncMock(side_effect=failing_generate)
        
        result = await extraction_service.extract_with_relationships("Text.")
        
        # Should return entities even if relationship extraction fails
        assert result.is_ok
        assert result.value.entity_count > 0
        assert result.value.relationship_count == 0


class TestEntityExtractionServiceParsing:
    """Tests for response parsing."""

    def test_parse_llm_response_json_block(self):
        """Test parsing JSON from markdown code block."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        response = '```json\n{"entities": [], "mentions": []}\n```'
        result = service._parse_llm_response(response)
        
        assert result.is_ok
        assert "entities" in result.value

    def test_parse_llm_response_plain_json(self):
        """Test parsing plain JSON."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        response = '{"entities": [], "mentions": []}'
        result = service._parse_llm_response(response)
        
        assert result.is_ok

    def test_parse_llm_response_invalid_json(self):
        """Test parsing invalid JSON."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        response = 'Not valid JSON'
        result = service._parse_llm_response(response)
        
        assert result.is_error


class TestEntityExtractionServiceEntityBuilding:
    """Tests for entity building."""

    def test_build_entities_with_type_mapping(self):
        """Test building entities with type mapping."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        entities_data = [
            {"name": "John", "type": "person"},  # Maps to CHARACTER
            {"name": "Paris", "type": "place"},  # Maps to LOCATION
        ]
        
        entities = service._build_entities(entities_data, 100)
        
        assert len(entities) == 2
        assert entities[0].entity_type == EntityType.CHARACTER
        assert entities[1].entity_type == EntityType.LOCATION

    def test_build_entities_with_unknown_type(self):
        """Test building entities with unknown type defaults to CHARACTER."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        entities_data = [
            {"name": "Unknown", "type": "unknown_type"},
        ]
        
        entities = service._build_entities(entities_data, 100)
        
        assert len(entities) == 1
        assert entities[0].entity_type == EntityType.CHARACTER

    def test_build_entities_respects_max_entities(self):
        """Test that max_entities limit is respected."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(
            llm_client=mock_llm,
            config=ExtractionConfig(max_entities=2),
        )
        
        entities_data = [
            {"name": f"Entity{i}", "type": "character"}
            for i in range(10)
        ]
        
        entities = service._build_entities(entities_data, 100)
        
        assert len(entities) == 2


class TestEntityExtractionServiceMentionBuilding:
    """Tests for mention building."""

    def test_build_mentions_pronoun_detection(self):
        """Test automatic pronoun detection in mentions."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        mentions_data = [
            {"entity_name": "Alice", "mention_text": "she", "start_pos": 10, "end_pos": 13},
            {"entity_name": "Bob", "mention_text": "Bob", "start_pos": 20, "end_pos": 23},
        ]
        
        mentions = service._build_mentions(mentions_data, 100)
        
        assert len(mentions) == 2
        # "she" should be detected as pronoun
        assert mentions[0].is_pronoun is True
        # "Bob" should not be pronoun
        assert mentions[1].is_pronoun is False


class TestEntityExtractionServiceRelationshipBuilding:
    """Tests for relationship building."""

    def test_build_relationships_with_type_mapping(self):
        """Test building relationships with type mapping."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        known_entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
            ExtractedEntity(name="Bob", entity_type=EntityType.CHARACTER),
        )
        
        relationships_data = [
            {"source": "Alice", "target": "Bob", "type": "know"},  # Maps to KNOWS
        ]
        
        relationships = service._build_relationships(relationships_data, known_entities)
        
        assert len(relationships) == 1
        assert relationships[0].relationship_type == RelationshipType.KNOWS

    def test_build_relationships_skips_unknown_entities(self):
        """Test that relationships with unknown entities are skipped."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        known_entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
        )
        
        relationships_data = [
            {"source": "Alice", "target": "UnknownEntity", "type": "knows"},
        ]
        
        relationships = service._build_relationships(relationships_data, known_entities)
        
        assert len(relationships) == 0

    def test_build_relationships_skips_self_relationships(self):
        """Test that self-relationships are skipped."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(llm_client=mock_llm)
        
        known_entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
        )
        
        relationships_data = [
            {"source": "Alice", "target": "Alice", "type": "knows"},
        ]
        
        relationships = service._build_relationships(relationships_data, known_entities)
        
        assert len(relationships) == 0

    def test_build_relationships_filters_by_strength(self):
        """Test that relationships are filtered by strength threshold."""
        mock_llm = Mock(spec=ILLMClient)
        service = EntityExtractionService(
            llm_client=mock_llm,
            config=ExtractionConfig(relationship_strength_threshold=0.5),
        )
        
        known_entities = (
            ExtractedEntity(name="Alice", entity_type=EntityType.CHARACTER),
            ExtractedEntity(name="Bob", entity_type=EntityType.CHARACTER),
        )
        
        relationships_data = [
            {"source": "Alice", "target": "Bob", "type": "knows", "strength": 0.3},  # Below threshold
            {"source": "Alice", "target": "Bob", "type": "loves", "strength": 0.9},  # Above threshold
        ]
        
        relationships = service._build_relationships(relationships_data, known_entities)
        
        assert len(relationships) == 1
        assert relationships[0].relationship_type == RelationshipType.LOVES
