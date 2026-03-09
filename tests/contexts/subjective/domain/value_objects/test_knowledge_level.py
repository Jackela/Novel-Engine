#!/usr/bin/env python3
"""
Knowledge Level Value Object Tests

Tests for KnowledgeType, CertaintyLevel, KnowledgeSource, KnowledgeItem, and KnowledgeBase.
Covers unit tests, integration tests, and boundary tests.
"""

from datetime import datetime, timedelta

import pytest

from src.contexts.subjective.domain.value_objects.knowledge_level import (
    CertaintyLevel,
    KnowledgeBase,
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeType,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Unit Tests (15 tests)
# ============================================================================


@pytest.mark.unit
class TestKnowledgeType:
    """Unit tests for KnowledgeType enum."""

    def test_knowledge_type_values(self):
        """Test knowledge type enum values."""
        assert KnowledgeType.FACTUAL.value == "factual"
        assert KnowledgeType.INFERENTIAL.value == "inferential"
        assert KnowledgeType.RUMOR.value == "rumor"
        assert KnowledgeType.SPECULATION.value == "speculation"
        assert KnowledgeType.HISTORICAL.value == "historical"
        assert KnowledgeType.TACTICAL.value == "tactical"
        assert KnowledgeType.PERSONAL.value == "personal"
        assert KnowledgeType.ENVIRONMENTAL.value == "environmental"


@pytest.mark.unit
class TestCertaintyLevel:
    """Unit tests for CertaintyLevel enum."""

    def test_certainty_level_values(self):
        """Test certainty level enum values."""
        assert CertaintyLevel.ABSOLUTE.value == "absolute"
        assert CertaintyLevel.HIGH.value == "high"
        assert CertaintyLevel.MEDIUM.value == "medium"
        assert CertaintyLevel.LOW.value == "low"
        assert CertaintyLevel.MINIMAL.value == "minimal"
        assert CertaintyLevel.UNKNOWN.value == "unknown"


@pytest.mark.unit
class TestKnowledgeSource:
    """Unit tests for KnowledgeSource enum."""

    def test_knowledge_source_values(self):
        """Test knowledge source enum values."""
        assert KnowledgeSource.DIRECT_OBSERVATION.value == "direct_observation"
        assert KnowledgeSource.REPORTED_BY_ALLY.value == "reported_by_ally"
        assert KnowledgeSource.REPORTED_BY_NEUTRAL.value == "reported_by_neutral"
        assert KnowledgeSource.REPORTED_BY_ENEMY.value == "reported_by_enemy"
        assert (
            KnowledgeSource.INTERCEPTED_COMMUNICATION.value
            == "intercepted_communication"
        )
        assert KnowledgeSource.DEDUCTION.value == "deduction"
        assert KnowledgeSource.SPECULATION.value == "speculation"
        assert KnowledgeSource.HISTORICAL_RECORD.value == "historical_record"
        assert KnowledgeSource.MAGICAL_DIVINATION.value == "magical_divination"
        assert KnowledgeSource.PSYCHIC_READING.value == "psychic_reading"


@pytest.mark.unit
class TestKnowledgeItem:
    """Unit tests for KnowledgeItem."""

    def test_create_basic_knowledge(self):
        """Test creating basic knowledge item."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Test information",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        assert item.subject == "subject_1"
        assert item.information == "Test information"
        assert item.knowledge_type == KnowledgeType.FACTUAL

    def test_knowledge_with_tags(self):
        """Test knowledge item with tags."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Test information",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
            tags={"urgent", "combat"},
        )
        assert "urgent" in item.tags
        assert "combat" in item.tags

    def test_knowledge_with_expiration(self):
        """Test knowledge item with expiration."""
        acquired = datetime.now()
        expires = acquired + timedelta(hours=1)

        item = KnowledgeItem(
            subject="subject_1",
            information="Time-sensitive info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=acquired,
            expires_at=expires,
        )
        assert item.expires_at == expires
        assert item.is_current()

    def test_knowledge_not_current_when_expired(self):
        """Test that expired knowledge is not current."""
        acquired = datetime.now() - timedelta(hours=2)
        expires = acquired + timedelta(hours=1)

        item = KnowledgeItem(
            subject="subject_1",
            information="Expired info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=acquired,
            expires_at=expires,
        )
        assert not item.is_current()

    def test_get_reliability_score_direct_observation(self):
        """Test reliability score for direct observation."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Direct observation",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        score = item.get_reliability_score()
        # ABSOLUTE (1.0) * DIRECT_OBSERVATION (1.0) = 1.0
        assert score == 1.0

    def test_get_reliability_score_rumor(self):
        """Test reliability score for rumor."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Rumor info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.SPECULATION,
            acquired_at=datetime.now(),
        )
        score = item.get_reliability_score()
        # LOW (0.40) * SPECULATION (0.3) = 0.12
        assert score < 0.2

    def test_has_tag(self):
        """Test tag checking."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Tagged info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
            tags={"important", "verified"},
        )
        assert item.has_tag("important")
        assert not item.has_tag("missing")

    def test_with_updated_certainty(self):
        """Test creating item with updated certainty."""
        original = KnowledgeItem(
            subject="subject_1",
            information="Original info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=datetime.now(),
        )

        updated = original.with_updated_certainty(
            CertaintyLevel.HIGH,
            new_source=KnowledgeSource.DIRECT_OBSERVATION,
        )

        assert updated.certainty_level == CertaintyLevel.HIGH
        assert updated.source == KnowledgeSource.DIRECT_OBSERVATION
        assert updated.information == original.information  # Unchanged


@pytest.mark.unit
class TestKnowledgeBase:
    """Unit tests for KnowledgeBase."""

    def test_create_empty_knowledge_base(self):
        """Test creating empty knowledge base."""
        base = KnowledgeBase(knowledge_items={})
        assert base.knowledge_items == {}
        assert base.get_total_knowledge_count() == 0

    def test_create_knowledge_base_with_items(self):
        """Test creating knowledge base with items."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        base = KnowledgeBase(knowledge_items={"subject_1": [item]})
        assert base.get_total_knowledge_count() == 1
        assert base.get_subjects_count() == 1

    def test_get_knowledge_about(self):
        """Test getting knowledge about a subject."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        base = KnowledgeBase(knowledge_items={"subject_1": [item]})
        knowledge = base.get_knowledge_about("subject_1")
        assert len(knowledge) == 1
        assert knowledge[0] == item

    def test_get_knowledge_about_empty(self):
        """Test getting knowledge about unknown subject."""
        base = KnowledgeBase(knowledge_items={})
        knowledge = base.get_knowledge_about("unknown")
        assert knowledge == []

    def test_has_knowledge_about(self):
        """Test checking if has knowledge about subject."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        base = KnowledgeBase(knowledge_items={"subject_1": [item]})
        assert base.has_knowledge_about("subject_1")
        assert not base.has_knowledge_about("unknown")


# ============================================================================
# Integration Tests (8 tests)
# ============================================================================


@pytest.mark.integration
class TestKnowledgeItemIntegration:
    """Integration tests for knowledge items."""

    def test_reliability_with_different_sources(self):
        """Test reliability with different sources."""
        sources_scores = [
            (KnowledgeSource.DIRECT_OBSERVATION, CertaintyLevel.HIGH, 0.85),
            (KnowledgeSource.REPORTED_BY_ALLY, CertaintyLevel.HIGH, 0.765),
            (KnowledgeSource.SPECULATION, CertaintyLevel.HIGH, 0.255),
        ]

        for source, certainty, expected_min in sources_scores:
            item = KnowledgeItem(
                subject="test",
                information="Test",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=certainty,
                source=source,
                acquired_at=datetime.now(),
            )
            score = item.get_reliability_score()
            assert score >= expected_min

    def test_knowledge_base_add_knowledge(self):
        """Test adding knowledge to base."""
        base = KnowledgeBase(knowledge_items={})

        item = KnowledgeItem(
            subject="new_subject",
            information="New info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )

        new_base = base.add_knowledge(item)
        assert new_base.has_knowledge_about("new_subject")
        assert base.get_total_knowledge_count() == 0  # Original unchanged


@pytest.mark.integration
class TestKnowledgeFilteringIntegration:
    """Integration tests for knowledge filtering."""

    def test_filter_by_type(self):
        """Test filtering knowledge by type."""
        factual = KnowledgeItem(
            subject="subject_1",
            information="Factual info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )

        rumor = KnowledgeItem(
            subject="subject_1",
            information="Rumor info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.SPECULATION,
            acquired_at=datetime.now(),
        )

        base = KnowledgeBase(knowledge_items={"subject_1": [factual, rumor]})

        subjects = base.get_subjects_by_type(KnowledgeType.FACTUAL)
        assert "subject_1" in subjects

    def test_filter_by_tag(self):
        """Test filtering knowledge by tag."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Tagged info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
            tags={"important"},
        )

        base = KnowledgeBase(knowledge_items={"subject_1": [item]})

        subjects = base.get_subjects_by_tag("important")
        assert "subject_1" in subjects


# ============================================================================
# Boundary Tests (7 tests)
# ============================================================================


@pytest.mark.unit
class TestKnowledgeBoundaryConditions:
    """Boundary tests for knowledge."""

    def test_empty_subject(self):
        """Test empty subject validation."""
        with pytest.raises(ValueError, match="Knowledge subject cannot be empty"):
            KnowledgeItem(
                subject="",
                information="Test info",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=datetime.now(),
            )

    def test_empty_information(self):
        """Test empty information validation."""
        with pytest.raises(ValueError, match="Knowledge information cannot be empty"):
            KnowledgeItem(
                subject="subject_1",
                information="",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=datetime.now(),
            )

    def test_expires_at_same_time_as_acquired(self):
        """Test expiration at same time as acquisition."""
        acquired = datetime.now()
        with pytest.raises(
            ValueError, match="Expiration time must be after acquisition time"
        ):
            KnowledgeItem(
                subject="subject_1",
                information="Test info",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired,
                expires_at=acquired,
            )

    def test_no_expiration(self):
        """Test knowledge with no expiration."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Permanent info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
            expires_at=None,
        )
        assert item.is_current()

    def test_empty_tags(self):
        """Test knowledge with empty tags."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Untagged info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
            tags=set(),
        )
        assert item.tags == set()
        assert not item.has_tag("anything")

    def test_minimum_certainty(self):
        """Test knowledge with minimum certainty."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Uncertain info",
            knowledge_type=KnowledgeType.SPECULATION,
            certainty_level=CertaintyLevel.UNKNOWN,
            source=KnowledgeSource.SPECULATION,
            acquired_at=datetime.now(),
        )
        score = item.get_reliability_score()
        assert score == 0.0

    def test_maximum_certainty_best_source(self):
        """Test knowledge with maximum certainty and best source."""
        item = KnowledgeItem(
            subject="subject_1",
            information="Certain info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        score = item.get_reliability_score()
        assert score == 1.0


# Total: 15 unit + 8 integration + 7 boundary = 30 tests for knowledge_level
