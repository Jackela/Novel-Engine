"""Tests for Chunking Strategy Factory module.

Tests cover:
- Strategy registration
- Dynamic strategy selection
- Auto-select strategy
- Error handling for missing dependencies
- Strategy descriptions
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.contexts.knowledge.infrastructure.chunking.factory import ChunkingStrategyFactory
from src.contexts.knowledge.infrastructure.chunking.base import BaseChunkingStrategy
from src.contexts.knowledge.domain.models.chunking_strategy import ChunkStrategyType
from src.contexts.knowledge.application.ports.i_chunking_strategy import ChunkingError


class TestChunkingStrategyFactoryInit:
    """Test ChunkingStrategyFactory initialization."""

    def test_factory_creation_without_embedding_service(self) -> None:
        """Test creating factory without embedding service."""
        factory = ChunkingStrategyFactory()
        
        assert factory._embedding_service is None

    def test_factory_creation_with_embedding_service(self) -> None:
        """Test creating factory with embedding service."""
        mock_service = MagicMock()
        factory = ChunkingStrategyFactory(embedding_service=mock_service)
        
        assert factory._embedding_service == mock_service


class TestCreateFixedStrategy:
    """Test creating fixed-size strategy."""

    def test_create_fixed_strategy(self) -> None:
        """Test creating a fixed-size chunking strategy."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create(ChunkStrategyType.FIXED)
        
        assert isinstance(strategy, BaseChunkingStrategy)
        assert strategy.supports_strategy_type("fixed")

    def test_create_fixed_strategy_by_string(self) -> None:
        """Test creating fixed strategy by string."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create("fixed")
        
        assert isinstance(strategy, BaseChunkingStrategy)


class TestCreateSentenceStrategy:
    """Test creating sentence boundary strategy."""

    def test_create_sentence_strategy(self) -> None:
        """Test creating a sentence boundary chunking strategy."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create(ChunkStrategyType.SENTENCE)
        
        assert isinstance(strategy, BaseChunkingStrategy)
        assert strategy.supports_strategy_type("sentence")

    def test_create_sentence_strategy_by_string(self) -> None:
        """Test creating sentence strategy by string."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create("sentence")
        
        assert isinstance(strategy, BaseChunkingStrategy)


class TestCreateParagraphStrategy:
    """Test creating paragraph boundary strategy."""

    def test_create_paragraph_strategy(self) -> None:
        """Test creating a paragraph boundary chunking strategy."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create(ChunkStrategyType.PARAGRAPH)
        
        assert isinstance(strategy, BaseChunkingStrategy)
        assert strategy.supports_strategy_type("paragraph")

    def test_create_paragraph_strategy_by_string(self) -> None:
        """Test creating paragraph strategy by string."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create("paragraph")
        
        assert isinstance(strategy, BaseChunkingStrategy)


class TestCreateSemanticStrategy:
    """Test creating semantic similarity strategy."""

    def test_create_semantic_strategy_with_embedding_service(self) -> None:
        """Test creating semantic strategy with embedding service."""
        mock_service = MagicMock()
        factory = ChunkingStrategyFactory(embedding_service=mock_service)
        
        strategy = factory.create(ChunkStrategyType.SEMANTIC)
        
        assert isinstance(strategy, BaseChunkingStrategy)
        assert strategy.supports_strategy_type("semantic")

    def test_create_semantic_strategy_without_embedding_service_raises(self) -> None:
        """Test creating semantic strategy without embedding service raises error."""
        factory = ChunkingStrategyFactory()  # No embedding service
        
        with pytest.raises(ChunkingError) as exc_info:
            factory.create(ChunkStrategyType.SEMANTIC)
        
        assert "embedding service" in str(exc_info.value).lower()
        assert exc_info.value.code == "MISSING_EMBEDDING_SERVICE"


class TestCreateNarrativeStrategy:
    """Test creating narrative structure strategy."""

    def test_create_narrative_strategy(self) -> None:
        """Test creating a narrative structure chunking strategy."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create(ChunkStrategyType.NARRATIVE_FLOW)
        
        assert isinstance(strategy, BaseChunkingStrategy)
        assert strategy.supports_strategy_type("narrative_flow")

    def test_create_narrative_strategy_by_string(self) -> None:
        """Test creating narrative strategy by string."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create("narrative_flow")
        
        assert isinstance(strategy, BaseChunkingStrategy)


class TestCreateAutoStrategy:
    """Test creating auto-select strategy."""

    def test_create_auto_strategy(self) -> None:
        """Test creating an auto-select chunking strategy."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create(ChunkStrategyType.AUTO)
        
        assert isinstance(strategy, BaseChunkingStrategy)
        assert strategy.supports_strategy_type("auto")

    def test_create_auto_strategy_by_string(self) -> None:
        """Test creating auto strategy by string."""
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create("auto")
        
        assert isinstance(strategy, BaseChunkingStrategy)


class TestCreateForContent:
    """Test create_for_content method."""

    def test_create_for_document_content(self) -> None:
        """Test creating strategy for document content."""
        from src.contexts.knowledge.infrastructure.chunking.strategies.auto import ContentType
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create_for_content(ContentType.DOCUMENT)
        
        assert isinstance(strategy, BaseChunkingStrategy)

    def test_create_for_scene_content(self) -> None:
        """Test creating strategy for scene content."""
        from src.contexts.knowledge.infrastructure.chunking.strategies.auto import ContentType
        # Scene content may need embedding service, so we use a factory with it
        mock_service = MagicMock()
        factory = ChunkingStrategyFactory(embedding_service=mock_service)
        
        strategy = factory.create_for_content(ContentType.SCENE)
        
        assert isinstance(strategy, BaseChunkingStrategy)

    def test_create_for_dialogue_content(self) -> None:
        """Test creating strategy for dialogue content."""
        from src.contexts.knowledge.infrastructure.chunking.strategies.auto import ContentType
        factory = ChunkingStrategyFactory()
        
        strategy = factory.create_for_content(ContentType.DIALOGUE)
        
        assert isinstance(strategy, BaseChunkingStrategy)

    def test_create_for_unknown_content_uses_auto(self) -> None:
        """Test that unknown content type falls back to auto strategy."""
        from src.contexts.knowledge.infrastructure.chunking.strategies.auto import ContentType
        factory = ChunkingStrategyFactory()
        
        # Using UNKNOWN content type falls back to auto strategy
        strategy = factory.create_for_content(ContentType.UNKNOWN)
        
        assert isinstance(strategy, BaseChunkingStrategy)


class TestCreateErrorCases:
    """Test error cases in create method."""

    def test_create_with_unknown_string_raises(self) -> None:
        """Test creating with unknown strategy string raises error."""
        factory = ChunkingStrategyFactory()
        
        with pytest.raises(ChunkingError) as exc_info:
            factory.create("unknown_strategy")
        
        assert "unknown" in str(exc_info.value).lower()
        assert exc_info.value.code == "UNKNOWN_STRATEGY_TYPE"

    def test_create_with_invalid_enum_value(self) -> None:
        """Test creating with invalid enum value raises error."""
        factory = ChunkingStrategyFactory()
        
        # Create a mock strategy type that's not in the map
        class MockStrategyType:
            value = "mock"
        
        # This should raise an error since it's not in the strategy map
        with pytest.raises((ChunkingError, AttributeError)):
            factory.create(MockStrategyType())  # type: ignore


class TestGetSupportedStrategies:
    """Test get_supported_strategies static method."""

    def test_get_supported_strategies_returns_list(self) -> None:
        """Test that supported strategies returns a list."""
        strategies = ChunkingStrategyFactory.get_supported_strategies()
        
        assert isinstance(strategies, list)
        assert len(strategies) == 6

    def test_get_supported_strategies_contains_expected(self) -> None:
        """Test that supported strategies contains expected types."""
        strategies = ChunkingStrategyFactory.get_supported_strategies()
        
        assert ChunkStrategyType.FIXED in strategies
        assert ChunkStrategyType.SENTENCE in strategies
        assert ChunkStrategyType.PARAGRAPH in strategies
        assert ChunkStrategyType.SEMANTIC in strategies
        assert ChunkStrategyType.NARRATIVE_FLOW in strategies
        assert ChunkStrategyType.AUTO in strategies


class TestGetStrategyDescription:
    """Test get_strategy_description static method."""

    def test_get_description_for_fixed(self) -> None:
        """Test getting description for fixed strategy."""
        description = ChunkingStrategyFactory.get_strategy_description(
            ChunkStrategyType.FIXED
        )
        
        assert "fixed" in description.lower()
        assert len(description) > 0

    def test_get_description_for_sentence(self) -> None:
        """Test getting description for sentence strategy."""
        description = ChunkingStrategyFactory.get_strategy_description(
            ChunkStrategyType.SENTENCE
        )
        
        assert "sentence" in description.lower()

    def test_get_description_for_paragraph(self) -> None:
        """Test getting description for paragraph strategy."""
        description = ChunkingStrategyFactory.get_strategy_description(
            ChunkStrategyType.PARAGRAPH
        )
        
        assert "paragraph" in description.lower()

    def test_get_description_for_semantic(self) -> None:
        """Test getting description for semantic strategy."""
        description = ChunkingStrategyFactory.get_strategy_description(
            ChunkStrategyType.SEMANTIC
        )
        
        assert "semantic" in description.lower()

    def test_get_description_for_narrative(self) -> None:
        """Test getting description for narrative strategy."""
        description = ChunkingStrategyFactory.get_strategy_description(
            ChunkStrategyType.NARRATIVE_FLOW
        )
        
        assert "narrative" in description.lower()

    def test_get_description_for_auto(self) -> None:
        """Test getting description for auto strategy."""
        description = ChunkingStrategyFactory.get_strategy_description(
            ChunkStrategyType.AUTO
        )
        
        assert "auto" in description.lower()

    def test_get_description_for_unknown_returns_default(self) -> None:
        """Test getting description for unknown strategy returns default."""
        # Create a mock strategy type
        class MockType:
            pass
        
        description = ChunkingStrategyFactory.get_strategy_description(MockType())  # type: ignore
        
        assert "no description" in description.lower()


class TestStrategyTypeStringHandling:
    """Test string handling for strategy types."""

    def test_string_strategy_case_insensitive(self) -> None:
        """Test that strategy strings are case insensitive."""
        factory = ChunkingStrategyFactory()
        
        # All should work
        strategy1 = factory.create("FIXED")
        strategy2 = factory.create("Fixed")
        strategy3 = factory.create("fixed")
        
        assert isinstance(strategy1, BaseChunkingStrategy)
        assert isinstance(strategy2, BaseChunkingStrategy)
        assert isinstance(strategy3, BaseChunkingStrategy)

    @pytest.mark.parametrize("strategy_name", [
        "fixed",
        "sentence",
        "paragraph",
        "semantic",
        "narrative_flow",
        "auto",
    ])
    def test_all_strategy_strings(self, strategy_name: str) -> None:
        """Test that all strategy strings can be used to create strategies."""
        factory = ChunkingStrategyFactory()
        
        if strategy_name == "semantic":
            mock_service = MagicMock()
            factory = ChunkingStrategyFactory(embedding_service=mock_service)
        
        strategy = factory.create(strategy_name)
        
        assert isinstance(strategy, BaseChunkingStrategy)
