"""
Test suite for Emotional Memory module.

Tests emotional state tracking, decay, and retrieval.
"""

import pytest
from unittest.mock import Mock

from src.memory.emotional_memory import (
    EmotionalIntensity,
    EmotionalValence,
    EmotionalMemoryItem,
    EmotionalMemory,
)
from src.core.data_models import MemoryItem, MemoryType


class TestEmotionalIntensity:
    """Test EmotionalIntensity enum."""

    def test_intensity_values(self):
        """Test emotional intensity values."""
        assert EmotionalIntensity.MINIMAL.value == "minimal"
        assert EmotionalIntensity.LOW.value == "low"
        assert EmotionalIntensity.MODERATE.value == "moderate"
        assert EmotionalIntensity.HIGH.value == "high"
        assert EmotionalIntensity.EXTREME.value == "extreme"


class TestEmotionalValence:
    """Test EmotionalValence enum."""

    def test_valence_values(self):
        """Test emotional valence values."""
        assert EmotionalValence.VERY_NEGATIVE.value == "very_negative"
        assert EmotionalValence.NEGATIVE.value == "negative"
        assert EmotionalValence.NEUTRAL.value == "neutral"
        assert EmotionalValence.POSITIVE.value == "positive"
        assert EmotionalValence.VERY_POSITIVE.value == "very_positive"


class TestEmotionalMemoryItem:
    """Test EmotionalMemoryItem dataclass."""

    def test_item_creation(self):
        """Test creating an emotional memory item."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="A beautiful sunset",
        )
        
        emotional_item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=0.8,
            arousal=0.5,
            dominance=0.6,
            emotional_tags=["happy", "peaceful"],
        )
        
        assert emotional_item.valence == 0.8
        assert emotional_item.arousal == 0.5
        assert emotional_item.dominance == 0.6

    def test_valence_clamping_high(self):
        """Test that valence is clamped to max 1.0."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=2.0,
        )
        assert item.valence == 1.0

    def test_valence_clamping_low(self):
        """Test that valence is clamped to min -1.0."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=-2.0,
        )
        assert item.valence == -1.0

    def test_arousal_clamping_high(self):
        """Test that arousal is clamped to max 1.0."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            arousal=2.0,
        )
        assert item.arousal == 1.0

    def test_arousal_clamping_low(self):
        """Test that arousal is clamped to min 0.0."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            arousal=-0.5,
        )
        assert item.arousal == 0.0

    def test_derive_emotional_tags_very_positive(self):
        """Test deriving tags for very positive valence."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=0.8,
            arousal=0.5,
        )
        
        tags = item._derive_emotional_tags()
        assert "very_positive" in tags

    def test_derive_emotional_tags_positive(self):
        """Test deriving tags for positive valence."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=0.4,
            arousal=0.5,
        )
        
        tags = item._derive_emotional_tags()
        assert "positive" in tags

    def test_derive_emotional_tags_negative(self):
        """Test deriving tags for negative valence."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=-0.4,
            arousal=0.5,
        )
        
        tags = item._derive_emotional_tags()
        assert "negative" in tags

    def test_derive_emotional_tags_neutral(self):
        """Test deriving tags for neutral valence."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=0.0,
            arousal=0.5,
        )
        
        tags = item._derive_emotional_tags()
        assert "neutral" in tags

    def test_derive_emotional_tags_high_arousal(self):
        """Test deriving tags for high arousal."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=0.0,
            arousal=0.8,
        )
        
        tags = item._derive_emotional_tags()
        assert "high_arousal" in tags

    def test_derive_emotional_tags_low_arousal(self):
        """Test deriving tags for low arousal."""
        memory_item = MemoryItem(
            agent_id="agent1",
            memory_type=MemoryType.EMOTIONAL,
            content="Test",
        )
        
        item = EmotionalMemoryItem(
            memory_item=memory_item,
            valence=0.0,
            arousal=0.2,
        )
        
        tags = item._derive_emotional_tags()
        assert "low_arousal" in tags


class TestEmotionalMemory:
    """Test EmotionalMemory implementation."""

    @pytest.fixture
    def mock_database(self):
        """Create mock database."""
        db = Mock()
        return db

    @pytest.fixture
    def emotional_memory(self, mock_database):
        """Create emotional memory system."""
        return EmotionalMemory(
            agent_id="agent1",
            database=mock_database,
            max_memories=100,
            threshold=0.3,
        )

    def test_initialization(self, mock_database):
        """Test emotional memory initialization."""
        em = EmotionalMemory(
            agent_id="test_agent",
            database=mock_database,
            max_memories=500,
            threshold=0.5,
        )
        
        assert em.agent_id == "test_agent"
        assert em.max_memories == 500
        assert em.threshold == 0.5
        assert em._emotional_memories == {}

    def test_initialization_defaults(self, mock_database):
        """Test emotional memory initialization with defaults."""
        em = EmotionalMemory(
            agent_id="test_agent",
            database=mock_database,
        )
        
        assert em.max_memories == 500
        assert em.threshold == 0.3
