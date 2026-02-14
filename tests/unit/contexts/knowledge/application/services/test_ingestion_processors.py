"""
Unit Tests for Ingestion Processors

Tests the processor abstraction and factory for content-specific
ingestion behavior.

Constitution Compliance:
- Article III (TDD): Tests verify processor selection and behavior
- Article II (Hexagonal): Tests use no external dependencies
"""

import pytest

from src.contexts.knowledge.application.ports.i_ingestion_processor import (
    IIngestionProcessor,
)
from src.contexts.knowledge.application.services.ingestion_processor_factory import (
    IngestionProcessorFactory,
)
from src.contexts.knowledge.application.services.ingestion_processors import (
    CharacterProcessor,
    GenericProcessor,
    ItemProcessor,
    LocationProcessor,
    LoreProcessor,
    PlotlineProcessor,
    SceneProcessor,
)
from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


class TestIngestionProcessorInterface:
    """Tests for IIngestionProcessor interface compliance."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_processors_implement_interface(self):
        """Verify all processor classes implement IIngestionProcessor."""
        processors = [
            GenericProcessor(),
            LoreProcessor(),
            CharacterProcessor(),
            SceneProcessor(),
            PlotlineProcessor(),
            ItemProcessor(),
            LocationProcessor(),
        ]

        for processor in processors:
            assert isinstance(processor, IIngestionProcessor)
            assert hasattr(processor, "source_type")
            assert hasattr(processor, "get_chunking_strategy")
            assert hasattr(processor, "enrich_metadata")
            assert hasattr(processor, "supports_batching")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_processors_support_batching(self):
        """Verify all processors support batching by default."""
        processors = [
            GenericProcessor(),
            LoreProcessor(),
            CharacterProcessor(),
            SceneProcessor(),
            PlotlineProcessor(),
            ItemProcessor(),
            LocationProcessor(),
        ]

        for processor in processors:
            assert processor.supports_batching() is True


class TestGenericProcessor:
    """Tests for GenericProcessor fallback."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_lore(self):
        """Generic processor should return LORE as source type."""
        processor = GenericProcessor()
        assert processor.source_type == SourceType.LORE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_default_chunking_strategy(self):
        """Generic processor should return default strategy."""
        processor = GenericProcessor()
        strategy = processor.get_chunking_strategy()

        assert isinstance(strategy, ChunkingStrategy)
        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 500  # DEFAULT_CHUNK_SIZE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_custom_strategy_uses_override(self):
        """Generic processor should use custom strategy when provided."""
        processor = GenericProcessor()
        custom = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=200,
            overlap=20,
        )
        strategy = processor.get_chunking_strategy(custom)

        assert strategy.strategy == ChunkStrategyType.SENTENCE
        assert strategy.chunk_size == 200

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_adds_processor_marker(self):
        """Generic processor should add processor marker to metadata."""
        processor = GenericProcessor()
        base = {"key": "value"}

        enriched = processor.enrich_metadata(base, "Some content")

        assert enriched["key"] == "value"
        assert enriched["processor"] == "generic"


class TestLoreProcessor:
    """Tests for LoreProcessor."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_lore(self):
        """Lore processor should return LORE source type."""
        processor = LoreProcessor()
        assert processor.source_type == SourceType.LORE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_default_chunking_strategy(self):
        """Lore processor should use 400-word fixed chunks."""
        processor = LoreProcessor()
        strategy = processor.get_chunking_strategy()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 400

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_history(self):
        """Lore processor should detect history-related content."""
        processor = LoreProcessor()
        content = "The ancient history of the kingdom spans centuries."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "lore"
        assert enriched["category"] == "history"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_magic(self):
        """Lore processor should detect magic-related content."""
        processor = LoreProcessor()
        content = "The spell requires rare magical reagents."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "lore"
        assert enriched["category"] == "magic"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_defaults_to_general(self):
        """Lore processor should default to general category."""
        processor = LoreProcessor()
        content = "Some generic information with no specific keywords."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "lore"
        assert enriched["category"] == "general"


class TestCharacterProcessor:
    """Tests for CharacterProcessor."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_character(self):
        """Character processor should return CHARACTER source type."""
        processor = CharacterProcessor()
        assert processor.source_type == SourceType.CHARACTER

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_default_chunking_strategy(self):
        """Character processor should use 200-word semantic chunks."""
        processor = CharacterProcessor()
        strategy = processor.get_chunking_strategy()

        assert strategy.strategy == ChunkStrategyType.SEMANTIC
        assert strategy.chunk_size == 200

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_extracts_name_hint(self):
        """Character processor should extract name from first line."""
        processor = CharacterProcessor()
        content = """Sir Aldric the Brave

        A legendary knight known for honor."""

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "character"
        assert "Sir Aldric the Brave" in enriched["name_hint"]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_protagonist(self):
        """Character processor should detect protagonist keywords."""
        processor = CharacterProcessor()
        content = "The hero of our story is a brave main character."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "character"
        assert enriched["role_hint"] == "protagonist"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_antagonist(self):
        """Character processor should detect antagonist keywords."""
        processor = CharacterProcessor()
        # Use content without protagonist keywords to avoid false match
        content = "A dark sorcerer spreads fear across the kingdom as a terrible enemy."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "character"
        assert enriched["role_hint"] == "antagonist"


class TestSceneProcessor:
    """Tests for SceneProcessor."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_scene(self):
        """Scene processor should return SCENE source type."""
        processor = SceneProcessor()
        assert processor.source_type == SourceType.SCENE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_default_chunking_strategy(self):
        """Scene processor should use 300-word paragraph chunks."""
        processor = SceneProcessor()
        strategy = processor.get_chunking_strategy()

        assert strategy.strategy == ChunkStrategyType.PARAGRAPH
        assert strategy.chunk_size == 300

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_calculates_dialogue_ratio(self):
        """Scene processor should calculate dialogue ratio."""
        processor = SceneProcessor()
        # Use pure dialogue to get high ratio
        content = '"Hello" "Hi" "How are you" "Fine thanks" "Goodbye"'

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "scene"
        assert "dialogue_ratio" in enriched
        assert enriched["dialogue_ratio"] == 1.0  # All dialogue

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_classifies_dialogue_heavy(self):
        """Scene processor should classify dialogue-heavy scenes."""
        processor = SceneProcessor()
        # Create content with mostly dialogue in quotes
        content = '"Hello" "Hi" "How are you" "Fine thanks" "Goodbye" "See you" "Welcome" "Cheers" "Thanks" "Please"'

        enriched = processor.enrich_metadata({}, content)

        assert enriched["scene_type"] == "dialogue_heavy"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_classifies_narration_heavy(self):
        """Scene processor should classify narration-heavy scenes."""
        processor = SceneProcessor()
        content = "He walked through the forest. The trees were tall. " * 50

        enriched = processor.enrich_metadata({}, content)

        assert enriched["scene_type"] == "narration_heavy"


class TestIngestionProcessorFactory:
    """Tests for IngestionProcessorFactory."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_for_lore_returns_lore_processor(self):
        """Factory should return LoreProcessor for LORE type."""
        factory = IngestionProcessorFactory()
        processor = factory.get_processor(SourceType.LORE)

        assert isinstance(processor, LoreProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_for_character_returns_character_processor(self):
        """Factory should return CharacterProcessor for CHARACTER type."""
        factory = IngestionProcessorFactory()
        processor = factory.get_processor(SourceType.CHARACTER)

        assert isinstance(processor, CharacterProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_for_scene_returns_scene_processor(self):
        """Factory should return SceneProcessor for SCENE type."""
        factory = IngestionProcessorFactory()
        processor = factory.get_processor(SourceType.SCENE)

        assert isinstance(processor, SceneProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_for_plotline_returns_plotline_processor(self):
        """Factory should return PlotlineProcessor for PLOTLINE type."""
        factory = IngestionProcessorFactory()
        processor = factory.get_processor(SourceType.PLOTLINE)

        assert isinstance(processor, PlotlineProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_for_item_returns_item_processor(self):
        """Factory should return ItemProcessor for ITEM type."""
        factory = IngestionProcessorFactory()
        processor = factory.get_processor(SourceType.ITEM)

        assert isinstance(processor, ItemProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_for_location_returns_location_processor(self):
        """Factory should return LocationProcessor for LOCATION type."""
        factory = IngestionProcessorFactory()
        processor = factory.get_processor(SourceType.LOCATION)

        assert isinstance(processor, LocationProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_processor_caches_instances(self):
        """Factory should cache processor instances."""
        factory = IngestionProcessorFactory()
        processor1 = factory.get_processor(SourceType.LORE)
        processor2 = factory.get_processor(SourceType.LORE)

        assert processor1 is processor2  # Same instance

    @pytest.mark.unit
    @pytest.mark.fast
    def test_register_processor_overrides_default(self):
        """Factory should use custom processor when registered."""
        factory = IngestionProcessorFactory()
        custom_processor = GenericProcessor()

        factory.register_processor(SourceType.CHARACTER, custom_processor)
        processor = factory.get_processor(SourceType.CHARACTER)

        assert processor is custom_processor
        assert not isinstance(processor, CharacterProcessor)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_processor_returns_true_for_registered_types(self):
        """Factory should report has_processor correctly."""
        factory = IngestionProcessorFactory()

        assert factory.has_processor(SourceType.LORE) is True
        assert factory.has_processor(SourceType.CHARACTER) is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_default_factory_creates_factory(self):
        """Default factory classmethod should create factory."""
        factory = IngestionProcessorFactory.get_default_factory()

        assert isinstance(factory, IngestionProcessorFactory)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_registered_types_returns_all_types(self):
        """Factory should list all registered source types."""
        factory = IngestionProcessorFactory()
        types = factory.get_registered_types()

        # Should include all default types
        assert SourceType.LORE in types
        assert SourceType.CHARACTER in types
        assert SourceType.SCENE in types
        assert SourceType.PLOTLINE in types
        assert SourceType.ITEM in types
        assert SourceType.LOCATION in types


class TestPlotlineProcessor:
    """Tests for PlotlineProcessor."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_plotline(self):
        """Plotline processor should return PLOTLINE source type."""
        processor = PlotlineProcessor()
        assert processor.source_type == SourceType.PLOTLINE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_chunking_strategy(self):
        """Plotline processor should use semantic chunking."""
        processor = PlotlineProcessor()
        strategy = processor.get_chunking_strategy()

        assert strategy.strategy == ChunkStrategyType.SEMANTIC
        assert strategy.chunk_size == 350

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_climax(self):
        """Plotline processor should detect climax phase."""
        processor = PlotlineProcessor()
        content = "The climax of the story involves a great battle."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "plotline"
        assert enriched["plot_phase"] == "climax"


class TestItemProcessor:
    """Tests for ItemProcessor."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_item(self):
        """Item processor should return ITEM source type."""
        processor = ItemProcessor()
        assert processor.source_type == SourceType.ITEM

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_chunking_strategy(self):
        """Item processor should use smaller chunks."""
        processor = ItemProcessor()
        strategy = processor.get_chunking_strategy()

        assert strategy.strategy == ChunkStrategyType.SEMANTIC
        assert strategy.chunk_size == 150

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_weapon(self):
        """Item processor should detect weapon type."""
        processor = ItemProcessor()
        content = "A legendary sword of great power."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "item"
        assert enriched["item_type_hint"] == "weapon"


class TestLocationProcessor:
    """Tests for LocationProcessor."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_location(self):
        """Location processor should return LOCATION source type."""
        processor = LocationProcessor()
        assert processor.source_type == SourceType.LOCATION

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_chunking_strategy(self):
        """Location processor should use 300-word chunks."""
        processor = LocationProcessor()
        strategy = processor.get_chunking_strategy()

        assert strategy.strategy == ChunkStrategyType.SEMANTIC
        assert strategy.chunk_size == 300

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enrich_metadata_detects_settlement(self):
        """Location processor should detect settlement type."""
        processor = LocationProcessor()
        content = "A bustling city with many inhabitants."

        enriched = processor.enrich_metadata({}, content)

        assert enriched["processor"] == "location"
        assert enriched["location_type_hint"] == "settlement"
