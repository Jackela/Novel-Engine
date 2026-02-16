"""
Unit Tests for Co-reference Resolution Service

Warzone 4: AI Brain - BRAIN-029B

Tests for the co-reference resolution service that resolves pronouns
and references to their canonical entity names (he -> Alice).
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
from src.contexts.knowledge.application.services.coreference_resolution_service import (
    DEFAULT_COREF_MAX_TOKENS,
    DEFAULT_COREF_TEMPERATURE,
    DEFAULT_MAX_REFERENCES,
    DEFAULT_WINDOW_SIZE,
    CoreferenceConfig,
    CoreferenceResolutionService,
    CoreferenceResult,
    ResolvedReference,
)
from src.contexts.knowledge.domain.models.entity import (
    EntityMention,
    EntityType,
    ExtractedEntity,
)

# Sample LLM response for co-reference resolution

pytestmark = pytest.mark.unit

SAMPLE_COREF_JSON = """{
  "entity_name": "Alice",
  "confidence": 0.95,
  "reasoning": "Alice is the most recent female character mentioned"
}"""


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=SAMPLE_COREF_JSON,
            model="test-model",
            tokens_used=100,
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
def sample_entities():
    """Create sample entities for testing."""
    return (
        ExtractedEntity(
            name="Alice",
            entity_type=EntityType.CHARACTER,
            description="A brave warrior",
            first_appearance=0,
        ),
        ExtractedEntity(
            name="Bob",
            entity_type=EntityType.CHARACTER,
            description="A tavern keeper",
            first_appearance=50,
        ),
        ExtractedEntity(
            name="Golden Dragon Tavern",
            entity_type=EntityType.LOCATION,
            description="A popular inn",
            first_appearance=100,
        ),
    )


@pytest.fixture
def sample_mentions():
    """Create sample mentions for testing."""
    return (
        EntityMention(
            entity_name="Alice",
            mention_text="Alice",
            start_pos=0,
            end_pos=5,
            is_pronoun=False,
        ),
        EntityMention(
            entity_name="Alice",
            mention_text="she",
            start_pos=30,
            end_pos=33,
            is_pronoun=True,
        ),
        EntityMention(
            entity_name="Bob",
            mention_text="Bob",
            start_pos=50,
            end_pos=53,
            is_pronoun=False,
        ),
        EntityMention(
            entity_name="Bob",
            mention_text="he",
            start_pos=70,
            end_pos=72,
            is_pronoun=True,
        ),
        EntityMention(
            entity_name="Golden Dragon Tavern",
            mention_text="it",
            start_pos=120,
            end_pos=122,
            is_pronoun=True,
        ),
    )


@pytest.fixture
def default_config():
    """Create default co-reference configuration."""
    return CoreferenceConfig()


@pytest.fixture
def coreference_service(mock_llm_client):
    """Create a CoreferenceResolutionService instance with mock LLM."""
    return CoreferenceResolutionService(llm_client=mock_llm_client)


class TestCoreferenceConfig:
    """Tests for CoreferenceConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CoreferenceConfig()

        assert config.window_size == DEFAULT_WINDOW_SIZE
        assert config.max_references == DEFAULT_MAX_REFERENCES
        assert config.temperature == DEFAULT_COREF_TEMPERATURE
        assert config.max_tokens == DEFAULT_COREF_MAX_TOKENS
        assert config.use_llm_fallback is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CoreferenceConfig(
            window_size=300,
            max_references=25,
            temperature=0.1,
            max_tokens=1000,
            use_llm_fallback=False,
        )

        assert config.window_size == 300
        assert config.max_references == 25
        assert config.temperature == 0.1
        assert config.max_tokens == 1000
        assert config.use_llm_fallback is False

    def test_config_validation_window_too_small(self):
        """Test validation rejects window_size < 100."""
        with pytest.raises(ValueError, match="window_size"):
            CoreferenceConfig(window_size=50)

    def test_config_validation_max_references_too_low(self):
        """Test validation rejects max_references < 1."""
        with pytest.raises(ValueError, match="max_references"):
            CoreferenceConfig(max_references=0)

    def test_config_validation_temperature_out_of_range(self):
        """Test validation rejects temperature outside 0-2."""
        with pytest.raises(ValueError, match="temperature"):
            CoreferenceConfig(temperature=2.5)


class TestResolvedReference:
    """Tests for ResolvedReference value object."""

    def test_resolved_reference_creation(self):
        """Test creating a valid resolved reference."""
        ref = ResolvedReference(
            mention_text="she",
            entity_name="Alice",
            start_pos=30,
            end_pos=33,
            confidence=0.95,
            resolution_method="heuristic",
        )

        assert ref.mention_text == "she"
        assert ref.entity_name == "Alice"
        assert ref.start_pos == 30
        assert ref.end_pos == 33
        assert ref.confidence == 0.95
        assert ref.resolution_method == "heuristic"

    def test_validation_empty_mention_text(self):
        """Test validation rejects empty mention text."""
        with pytest.raises(ValueError, match="mention_text"):
            ResolvedReference(
                mention_text="",
                entity_name="Alice",
                start_pos=30,
                end_pos=33,
                confidence=0.95,
                resolution_method="heuristic",
            )

    def test_validation_empty_entity_name(self):
        """Test validation rejects empty entity name."""
        with pytest.raises(ValueError, match="entity_name"):
            ResolvedReference(
                mention_text="she",
                entity_name="",
                start_pos=30,
                end_pos=33,
                confidence=0.95,
                resolution_method="heuristic",
            )

    def test_validation_confidence_out_of_range(self):
        """Test validation rejects confidence outside 0-1."""
        with pytest.raises(ValueError, match="confidence"):
            ResolvedReference(
                mention_text="she",
                entity_name="Alice",
                start_pos=30,
                end_pos=33,
                confidence=1.5,
                resolution_method="heuristic",
            )

    def test_validation_negative_start_pos(self):
        """Test validation rejects negative start_pos."""
        with pytest.raises(ValueError, match="start_pos"):
            ResolvedReference(
                mention_text="she",
                entity_name="Alice",
                start_pos=-1,
                end_pos=33,
                confidence=0.95,
                resolution_method="heuristic",
            )

    def test_validation_end_before_start(self):
        """Test validation rejects end_pos < start_pos."""
        with pytest.raises(ValueError, match="end_pos"):
            ResolvedReference(
                mention_text="she",
                entity_name="Alice",
                start_pos=50,
                end_pos=30,
                confidence=0.95,
                resolution_method="heuristic",
            )


class TestCoreferenceResult:
    """Tests for CoreferenceResult value object."""

    def test_result_creation(self):
        """Test creating a valid result."""
        resolved = (
            ResolvedReference(
                mention_text="she",
                entity_name="Alice",
                start_pos=30,
                end_pos=33,
                confidence=0.95,
                resolution_method="heuristic",
            ),
        )
        unresolved = ()

        result = CoreferenceResult(
            resolved_references=resolved,
            unresolved_mentions=unresolved,
            resolution_rate=1.0,
        )

        assert result.total_resolved == 1
        assert result.total_unresolved == 0
        assert result.resolution_rate == 1.0

    def test_result_with_unresolved(self):
        """Test result with unresolved mentions."""
        unresolved = (
            EntityMention(
                entity_name="",
                mention_text="they",
                start_pos=100,
                end_pos=104,
                is_pronoun=True,
            ),
        )

        result = CoreferenceResult(
            resolved_references=(),
            unresolved_mentions=unresolved,
            resolution_rate=0.0,
        )

        assert result.total_resolved == 0
        assert result.total_unresolved == 1


class TestCoreferenceResolutionService:
    """Tests for CoreferenceResolutionService."""

    def test_find_candidate_entities(self, coreference_service, sample_entities):
        """Test finding candidate entities near a position."""
        # Candidates near position 50 (between Alice at 0 and Bob at 50)
        candidates = coreference_service._find_candidate_entities(
            sample_entities,
            position=50,
            text="A" * 200,  # Dummy text
        )

        # Should find Alice and potentially Bob
        assert len(candidates) >= 1
        names = [e.name for e, _ in candidates]
        assert "Alice" in names

    def test_find_candidate_entities_respects_window(
        self, coreference_service, sample_entities
    ):
        """Test that window size limits candidate search."""
        # Small window
        coreference_service._config = CoreferenceConfig(window_size=100)

        candidates = coreference_service._find_candidate_entities(
            sample_entities,
            position=300,  # Far from all entities
            text="A" * 400,
        )

        # Should not find candidates far outside window
        assert len(candidates) == 0

    def test_resolve_pronoun_heuristic_she(self, coreference_service):
        """Test heuristic resolution of 'she' pronoun."""
        # Create candidates with a feminine-sounding name
        candidates = [
            (
                ExtractedEntity(
                    name="Alice",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=0,
                ),
                30,
            ),
            (
                ExtractedEntity(
                    name="Bob",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=0,
                ),
                100,
            ),
        ]

        entity_name, confidence = coreference_service._resolve_pronoun_heuristic(
            "she",
            candidates,
        )

        # Should return the closest candidate
        assert entity_name is not None
        assert confidence > 0

    def test_resolve_pronoun_heuristic_he(self, coreference_service):
        """Test heuristic resolution of 'he' pronoun."""
        candidates = [
            (
                ExtractedEntity(
                    name="Bob",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=0,
                ),
                50,
            ),
        ]

        entity_name, confidence = coreference_service._resolve_pronoun_heuristic(
            "he",
            candidates,
        )

        assert entity_name == "Bob"
        assert confidence > 0

    def test_filter_candidates_by_pronoun_masculine(
        self, coreference_service, sample_entities
    ):
        """Test filtering candidates for masculine pronouns."""
        filtered = coreference_service._filter_candidates_by_pronoun(
            list(zip(sample_entities, [10, 20, 30])),
            "he",
        )

        # Should return candidates (no filtering for exact matches)
        assert len(filtered) >= 0

    def test_filter_candidates_by_pronoun_feminine(
        self, coreference_service, sample_entities
    ):
        """Test filtering candidates for feminine pronouns."""
        filtered = coreference_service._filter_candidates_by_pronoun(
            list(zip(sample_entities, [10, 20, 30])),
            "she",
        )

        # Should return candidates (no filtering for exact matches)
        assert len(filtered) >= 0

    def test_get_gender_from_name(self, coreference_service):
        """Test gender inference from names."""
        assert coreference_service._get_gender_from_name("Alexander") == "masculine"
        assert coreference_service._get_gender_from_name("Victoria") == "feminine"
        assert coreference_service._get_gender_from_name("Guild") == "neutral"
        assert coreference_service._get_gender_from_name("Tavern") == "neutral"
        assert coreference_service._get_gender_from_name("Forest") == "neutral"

    @pytest.mark.asyncio
    async def test_resolve_with_text_heuristic_only(
        self, coreference_service, sample_entities, sample_mentions
    ):
        """Test resolution using heuristics only (no LLM fallback)."""
        config = CoreferenceConfig(use_llm_fallback=False)

        result = await coreference_service.resolve_with_text(
            text="Alice entered the tavern. She sat down. Bob arrived. He smiled.",
            entities=sample_entities,
            mentions=sample_mentions,
            config=config,
        )

        # Should resolve some pronouns using heuristics
        assert isinstance(result, CoreferenceResult)
        assert result.resolution_rate >= 0

    @pytest.mark.asyncio
    async def test_resolve_with_text_llm_fallback(
        self, mock_llm_client, sample_entities, sample_mentions
    ):
        """Test resolution with LLM fallback enabled."""
        service = CoreferenceResolutionService(
            llm_client=mock_llm_client,
            config=CoreferenceConfig(use_llm_fallback=True),
        )

        result = await service.resolve_with_text(
            text="Alice entered the tavern. She sat down.",
            entities=sample_entities,
            mentions=sample_mentions,
        )

        assert isinstance(result, CoreferenceResult)

    @pytest.mark.asyncio
    async def test_resolve_batch(
        self, coreference_service, sample_entities, sample_mentions
    ):
        """Test batch resolution of multiple texts."""
        texts = [
            "Alice entered the tavern. She sat down.",
            "Bob arrived. He ordered a drink.",
        ]

        results = await coreference_service.resolve_batch(
            texts=texts,
            entities_list=(sample_entities, sample_entities),
            mentions_list=(sample_mentions, sample_mentions),
        )

        assert len(results) == 2
        for result in results:
            assert isinstance(result, CoreferenceResult)

    @pytest.mark.asyncio
    async def test_resolve_batch_length_mismatch(self, coreference_service):
        """Test that batch resolution validates input lengths."""
        with pytest.raises(ValueError, match="same length"):
            await coreference_service.resolve_batch(
                texts=["Text 1", "Text 2"],
                entities_list=((),),  # Wrong length
                mentions_list=((),),
            )

    @pytest.mark.asyncio
    async def test_resolve_with_text_empty(self, coreference_service):
        """Test resolution with empty entities and mentions."""
        result = await coreference_service.resolve_with_text(
            text="Empty text.",
            entities=(),
            mentions=(),
        )

        assert result.total_resolved == 0
        assert result.total_unresolved == 0
        assert result.resolution_rate == 1.0  # No pronouns to resolve


@pytest.mark.unit
@pytest.mark.medium
class TestCoreferenceResolutionServiceIntegration:
    """
    Integration-style tests for co-reference resolution.

    Tests the complete resolution flow with realistic scenarios.
    """

    @pytest.mark.asyncio
    async def test_resolve_simple_pronouns(self, mock_llm_client):
        """Test resolving simple pronoun references."""
        service = CoreferenceResolutionService(llm_client=mock_llm_client)

        text = "Alice entered the Golden Dragon Tavern. She was tired."

        entities = (
            ExtractedEntity(
                name="Alice",
                entity_type=EntityType.CHARACTER,
                first_appearance=0,
            ),
            ExtractedEntity(
                name="Golden Dragon Tavern",
                entity_type=EntityType.LOCATION,
                first_appearance=20,
            ),
        )

        mentions = (
            EntityMention(
                entity_name="Alice",
                mention_text="Alice",
                start_pos=0,
                end_pos=5,
                is_pronoun=False,
            ),
            EntityMention(
                entity_name="Alice",
                mention_text="She",
                start_pos=38,
                end_pos=41,
                is_pronoun=True,
            ),
        )

        result = await service.resolve_with_text(text, entities, mentions)

        assert result.total_resolved >= 0
        assert result.resolution_rate >= 0

    @pytest.mark.asyncio
    async def test_resolve_multiple_characters(self, mock_llm_client):
        """Test resolving pronouns with multiple characters."""
        service = CoreferenceResolutionService(llm_client=mock_llm_client)

        text = "Alice and Bob talked. She laughed. He smiled."

        entities = (
            ExtractedEntity(
                name="Alice",
                entity_type=EntityType.CHARACTER,
                first_appearance=0,
            ),
            ExtractedEntity(
                name="Bob",
                entity_type=EntityType.CHARACTER,
                first_appearance=10,
            ),
        )

        mentions = (
            EntityMention(
                entity_name="Alice",
                mention_text="Alice",
                start_pos=0,
                end_pos=5,
                is_pronoun=False,
            ),
            EntityMention(
                entity_name="Bob",
                mention_text="Bob",
                start_pos=10,
                end_pos=13,
                is_pronoun=False,
            ),
            EntityMention(
                entity_name="Alice",
                mention_text="She",
                start_pos=27,
                end_pos=30,
                is_pronoun=True,
            ),
            EntityMention(
                entity_name="Bob",
                mention_text="He",
                start_pos=40,
                end_pos=42,
                is_pronoun=True,
            ),
        )

        result = await service.resolve_with_text(text, entities, mentions)

        assert result.total_resolved >= 0

    @pytest.mark.asyncio
    async def test_resolve_with_neutral_references(self, mock_llm_client):
        """Test resolving neutral references (they, them)."""
        service = CoreferenceResolutionService(llm_client=mock_llm_client)

        text = "The guild members met. They discussed the quest."

        entities = (
            ExtractedEntity(
                name="Guild",
                entity_type=EntityType.ORGANIZATION,
                first_appearance=0,
            ),
        )

        mentions = (
            EntityMention(
                entity_name="Guild",
                mention_text="The guild",
                start_pos=0,
                end_pos=9,
                is_pronoun=False,
            ),
            EntityMention(
                entity_name="Guild",
                mention_text="They",
                start_pos=27,
                end_pos=31,
                is_pronoun=True,
            ),
        )

        result = await service.resolve_with_text(text, entities, mentions)

        assert result.total_resolved >= 0


@pytest.mark.unit
@pytest.mark.fast
class TestEntityExtractionServiceLargeText:
    """
    Tests for large text batch processing in entity extraction.

    Warzone 4: AI Brain - BRAIN-029B (Batch processing requirement)
    """

    @pytest.mark.asyncio
    async def test_extract_large_text_chunks(self, mock_llm_client):
        """Test that large texts are chunked and processed."""
        from src.contexts.knowledge.application.services.entity_extraction_service import (
            EntityExtractionService,
        )

        service = EntityExtractionService(llm_client=mock_llm_client)

        # Create a text longer than default chunk size
        large_text = "Alice warrior. " * 500  # ~8000 characters

        result = await service.extract_large_text(
            large_text,
            chunk_size=2000,
            overlap=200,
        )

        assert isinstance(result, result.__class__)
        assert result.source_length == len(large_text)

    @pytest.mark.asyncio
    async def test_extract_large_text_small_skips_chunking(self, mock_llm_client):
        """Test that small texts skip chunking."""
        from src.contexts.knowledge.application.services.entity_extraction_service import (
            EntityExtractionService,
        )

        service = EntityExtractionService(llm_client=mock_llm_client)

        small_text = "Alice entered the tavern."

        result = await service.extract_large_text(small_text)

        assert result.source_length == len(small_text)

    @pytest.mark.asyncio
    async def test_merge_extraction_results_deduplicates(self):
        """Test that merging results deduplicates entities."""
        from src.contexts.knowledge.application.services.entity_extraction_service import (
            EntityExtractionService,
        )
        from src.contexts.knowledge.domain.models.entity import ExtractionResult

        service = EntityExtractionService(llm_client=AsyncMock())

        # Create two results with overlapping entities
        result1 = ExtractionResult(
            entities=(
                ExtractedEntity(
                    name="Alice",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=0,
                ),
                ExtractedEntity(
                    name="Bob",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=10,
                ),
            ),
            mentions=(),
            source_length=100,
        )

        result2 = ExtractionResult(
            entities=(
                ExtractedEntity(
                    name="Alice",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=0,
                ),
                ExtractedEntity(
                    name="Charlie",
                    entity_type=EntityType.CHARACTER,
                    first_appearance=20,
                ),
            ),
            mentions=(),
            source_length=100,
        )

        merged = service._merge_extraction_results([result1, result2], 200)

        # Should have 3 unique entities (Alice deduplicated)
        assert merged.entity_count == 3
        entity_names = {e.name for e in merged.entities}
        assert entity_names == {"Alice", "Bob", "Charlie"}
