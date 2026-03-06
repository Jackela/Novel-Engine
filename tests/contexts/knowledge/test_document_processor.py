"""
Test suite for Document Processors (Ingestion Processors).

Tests all processor implementations for different source types.
"""

import pytest
from typing import Any

from src.contexts.knowledge.application.services.ingestion_processors import (
    GenericProcessor,
    LoreProcessor,
    CharacterProcessor,
    SceneProcessor,
    PlotlineProcessor,
    ItemProcessor,
    LocationProcessor,
)
from src.contexts.knowledge.domain.models.chunking_strategy import ChunkingStrategy, ChunkStrategyType
from src.contexts.knowledge.domain.models.source_type import SourceType


class TestGenericProcessor:
    """Tests for GenericProcessor."""

    @pytest.fixture
    def processor(self):
        """Create generic processor."""
        return GenericProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.LORE

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        assert strategy.strategy == ChunkStrategyType.FIXED

    def test_get_chunking_strategy_custom(self, processor):
        """Test getting custom chunking strategy."""
        custom_strategy = ChunkingStrategy(strategy=ChunkStrategyType.SEMANTIC, chunk_size=500)
        strategy = processor.get_chunking_strategy(custom_strategy)
        
        assert strategy == custom_strategy

    def test_enrich_metadata(self, processor):
        """Test metadata enrichment."""
        base_metadata = {"tags": ["test"]}
        enriched = processor.enrich_metadata(base_metadata, "test content")
        
        assert enriched["processor"] == "generic"
        assert enriched["tags"] == ["test"]

    def test_enrich_metadata_preserves_existing(self, processor):
        """Test that enrichment preserves existing metadata."""
        base_metadata = {"existing_key": "existing_value", "tags": ["tag1"]}
        enriched = processor.enrich_metadata(base_metadata, "content")
        
        assert enriched["existing_key"] == "existing_value"
        assert enriched["tags"] == ["tag1"]


class TestLoreProcessor:
    """Tests for LoreProcessor."""

    @pytest.fixture
    def processor(self):
        """Create lore processor."""
        return LoreProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.LORE

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        # Should use lore-optimized settings
        assert strategy.chunk_size > 0

    def test_get_chunking_strategy_custom_override(self, processor):
        """Test that custom strategy overrides default."""
        custom_strategy = ChunkingStrategy(strategy=ChunkStrategyType.FIXED, chunk_size=200)
        strategy = processor.get_chunking_strategy(custom_strategy)
        
        assert strategy == custom_strategy

    def test_enrich_metadata_detects_history_category(self, processor):
        """Test detecting history category from content."""
        content = "The ancient history of the kingdom dates back millennia."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["category"] == "history"

    def test_enrich_metadata_detects_magic_category(self, processor):
        """Test detecting magic category from content."""
        content = "The spell requires precise incantation and magical focus."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["category"] == "magic"

    def test_enrich_metadata_detects_geography_category(self, processor):
        """Test detecting geography category from content."""
        content = "The region is characterized by mountainous terrain."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["category"] == "geography"

    def test_enrich_metadata_detects_culture_category(self, processor):
        """Test detecting culture category from content."""
        content = "The society has rich traditions and customs."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["category"] == "culture"

    def test_enrich_metadata_default_category(self, processor):
        """Test default category when no keywords match."""
        content = "This is just generic content without specific keywords."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["category"] == "general"

    def test_enrich_metadata_preserves_tags(self, processor):
        """Test that enrichment preserves tags."""
        base_metadata = {"tags": ["important", "verified"]}
        enriched = processor.enrich_metadata(base_metadata, "content")
        
        assert enriched["tags"] == ["important", "verified"]


class TestCharacterProcessor:
    """Tests for CharacterProcessor."""

    @pytest.fixture
    def processor(self):
        """Create character processor."""
        return CharacterProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.CHARACTER

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        # Character strategy should use semantic chunking with smaller chunks
        assert strategy.chunk_size > 0

    def test_enrich_metadata_extracts_name_hint(self, processor):
        """Test extracting name hint from first line."""
        content = "Aragorn\nSon of Arathorn, King of Gondor"
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["name_hint"] == "Aragorn"

    def test_enrich_metadata_no_name_hint_for_long_first_line(self, processor):
        """Test that long first lines are not treated as name hints."""
        content = "This is a very long first line that goes on and on and should not be treated as a name."
        enriched = processor.enrich_metadata({}, content)
        
        assert "name_hint" not in enriched

    def test_enrich_metadata_no_name_hint_for_sentence(self, processor):
        """Test that sentences are not treated as name hints."""
        content = "This is a sentence.\nMore content here."
        enriched = processor.enrich_metadata({}, content)
        
        assert "name_hint" not in enriched

    def test_enrich_metadata_detects_protagonist_role(self, processor):
        """Test detecting protagonist role."""
        content = "The hero of our story fights for justice."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["role_hint"] == "protagonist"

    def test_enrich_metadata_detects_antagonist_role(self, processor):
        """Test detecting antagonist role."""
        content = "The villain plots against the kingdom."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["role_hint"] == "antagonist"

    def test_enrich_metadata_detects_mentor_role(self, processor):
        """Test detecting mentor role."""
        content = "The old master teaches the young apprentice."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["role_hint"] == "mentor"

    def test_enrich_metadata_detects_ally_role(self, processor):
        """Test detecting ally role."""
        content = "The friend provides support and companionship."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["role_hint"] == "ally"

    def test_enrich_metadata_detects_neutral_role(self, processor):
        """Test detecting neutral/NPC role."""
        content = "The background NPC provides information."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched["role_hint"] == "neutral"

    def test_enrich_metadata_no_role_hint_for_no_match(self, processor):
        """Test that no role hint is added when no keywords match."""
        content = "Generic character description without role keywords."
        enriched = processor.enrich_metadata({}, content)
        
        assert "role_hint" not in enriched


class TestSceneProcessor:
    """Tests for SceneProcessor."""

    @pytest.fixture
    def processor(self):
        """Create scene processor."""
        return SceneProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.SCENE

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        assert strategy.chunk_size > 0

    def test_enrich_metadata_calculates_dialogue_ratio(self, processor):
        """Test calculating dialogue ratio."""
        content = '"Hello there," said John. "How are you?"'
        enriched = processor.enrich_metadata({}, content)
        
        assert "dialogue_ratio" in enriched
        assert isinstance(enriched["dialogue_ratio"], float)

    def test_enrich_metadata_classifies_dialogue_heavy(self, processor):
        """Test classifying dialogue-heavy scenes."""
        # Content with >50% dialogue
        content = '"Hello!" "Hi there!" "How are you?" "Great!"'
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("scene_type") == "dialogue_heavy"

    def test_enrich_metadata_classifies_narration_heavy(self, processor):
        """Test classifying narration-heavy scenes."""
        # Content with <10% dialogue
        content = "The sun rose over the mountains. Birds chirped in the trees."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("scene_type") == "narration_heavy"

    def test_enrich_metadata_classifies_balanced(self, processor):
        """Test classifying balanced scenes."""
        # Content with 10-50% dialogue
        content = 'The sun rose. "Good morning," said John. The birds chirped.'
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("scene_type") == "balanced"

    def test_enrich_metadata_detects_indoor_setting(self, processor):
        """Test detecting indoor setting."""
        content = "The room was dark. The hall echoed with footsteps."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("setting_hint") == "indoor"

    def test_enrich_metadata_detects_outdoor_setting(self, processor):
        """Test detecting outdoor setting."""
        content = "The forest was dense. The mountain loomed ahead."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("setting_hint") == "outdoor"

    def test_enrich_metadata_detects_urban_setting(self, processor):
        """Test detecting urban setting."""
        content = "The city streets were crowded. The market was busy."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("setting_hint") == "urban"

    def test_enrich_metadata_detects_travel_setting(self, processor):
        """Test detecting travel setting."""
        content = "They journeyed across the land, riding for days."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("setting_hint") == "travel"


class TestPlotlineProcessor:
    """Tests for PlotlineProcessor."""

    @pytest.fixture
    def processor(self):
        """Create plotline processor."""
        return PlotlineProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.PLOTLINE

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        assert strategy.strategy == ChunkStrategyType.SEMANTIC

    def test_enrich_metadata_detects_setup_phase(self, processor):
        """Test detecting setup plot phase."""
        content = "The story begins with an introduction to the characters."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("plot_phase") == "setup"

    def test_enrich_metadata_detects_rising_action_phase(self, processor):
        """Test detecting rising action phase."""
        content = "The conflict escalates as tension rises."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("plot_phase") == "rising_action"

    def test_enrich_metadata_detects_climax_phase(self, processor):
        """Test detecting climax phase."""
        content = "The battle reached its peak in a dramatic showdown."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("plot_phase") == "climax"

    def test_enrich_metadata_detects_falling_action_phase(self, processor):
        """Test detecting falling action phase."""
        content = "The aftermath of the resolution led to consequences."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("plot_phase") == "falling_action"

    def test_enrich_metadata_detects_resolution_phase(self, processor):
        """Test detecting resolution phase."""
        content = "The ending concluded with a finale and epilogue."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("plot_phase") == "resolution"


class TestItemProcessor:
    """Tests for ItemProcessor."""

    @pytest.fixture
    def processor(self):
        """Create item processor."""
        return ItemProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.ITEM

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        # Items should use smaller chunks
        assert strategy.chunk_size <= 200

    def test_enrich_metadata_detects_weapon_type(self, processor):
        """Test detecting weapon item type."""
        content = "The sword was sharp and deadly."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("item_type_hint") == "weapon"

    def test_enrich_metadata_detects_armor_type(self, processor):
        """Test detecting armor item type."""
        content = "The armor provided excellent defense with its plate and mail."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("item_type_hint") == "armor"

    def test_enrich_metadata_detects_consumable_type(self, processor):
        """Test detecting consumable item type."""
        content = "The potion restored health when consumed."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("item_type_hint") == "consumable"

    def test_enrich_metadata_detects_artifact_type(self, processor):
        """Test detecting artifact item type."""
        content = "The ancient artifact was a legendary relic."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("item_type_hint") == "artifact"

    def test_enrich_metadata_detects_tool_type(self, processor):
        """Test detecting tool item type."""
        content = "The lockpick tool was essential for opening doors."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("item_type_hint") == "tool"


class TestLocationProcessor:
    """Tests for LocationProcessor."""

    @pytest.fixture
    def processor(self):
        """Create location processor."""
        return LocationProcessor()

    def test_source_type(self, processor):
        """Test processor source type."""
        assert processor.source_type == SourceType.LOCATION

    def test_get_chunking_strategy_default(self, processor):
        """Test getting default chunking strategy."""
        strategy = processor.get_chunking_strategy()
        
        assert isinstance(strategy, ChunkingStrategy)
        assert strategy.chunk_size > 0

    def test_enrich_metadata_detects_settlement_type(self, processor):
        """Test detecting settlement location type."""
        content = "The city was a bustling town with a busy village nearby."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("location_type_hint") == "settlement"

    def test_enrich_metadata_detects_natural_type(self, processor):
        """Test detecting natural location type."""
        content = "The forest stretched to the mountain with a river running through."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("location_type_hint") == "natural"

    def test_enrich_metadata_detects_structure_type(self, processor):
        """Test detecting structure location type."""
        content = "The castle was built near ancient temple ruins."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("location_type_hint") == "structure"

    def test_enrich_metadata_detects_region_type(self, processor):
        """Test detecting region location type."""
        content = "The kingdom spanned across the realm and territory."
        enriched = processor.enrich_metadata({}, content)
        
        assert enriched.get("location_type_hint") == "region"


class TestProcessorEdgeCases:
    """Tests for edge cases across all processors."""

    def test_all_processors_implement_source_type(self):
        """Test that all processors implement source_type property."""
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
            assert processor.source_type is not None
            assert isinstance(processor.source_type, SourceType)

    def test_all_processors_return_chunking_strategy(self):
        """Test that all processors return a valid chunking strategy."""
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
            strategy = processor.get_chunking_strategy()
            assert isinstance(strategy, ChunkingStrategy)
            assert strategy.chunk_size > 0

    def test_all_processors_enrich_metadata(self):
        """Test that all processors enrich metadata."""
        processors = [
            GenericProcessor(),
            LoreProcessor(),
            CharacterProcessor(),
            SceneProcessor(),
            PlotlineProcessor(),
            ItemProcessor(),
            LocationProcessor(),
        ]
        
        base_metadata = {"tags": ["test"]}
        content = "Test content for processing."
        
        for processor in processors:
            enriched = processor.enrich_metadata(base_metadata, content)
            assert "processor" in enriched
            assert enriched["tags"] == ["test"]

    def test_processors_handle_empty_content(self):
        """Test that processors handle empty content gracefully."""
        processors = [
            LoreProcessor(),
            CharacterProcessor(),
            SceneProcessor(),
            PlotlineProcessor(),
            ItemProcessor(),
            LocationProcessor(),
        ]
        
        for processor in processors:
            enriched = processor.enrich_metadata({}, "")
            assert "processor" in enriched

    def test_chunking_strategy_caching(self):
        """Test that processors return consistent chunking strategies."""
        processor = LoreProcessor()
        
        strategy1 = processor.get_chunking_strategy()
        strategy2 = processor.get_chunking_strategy()
        
        assert strategy1 == strategy2
