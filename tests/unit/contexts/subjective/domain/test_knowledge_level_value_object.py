#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Knowledge Level Value Objects

Test suite covering knowledge items, knowledge bases, certainty levels,
and knowledge management business logic in the Subjective Context.
"""

from datetime import datetime, timedelta

import pytest
from contexts.subjective.domain.value_objects.knowledge_level import (
    CertaintyLevel,
    KnowledgeBase,
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeType,
)


class TestKnowledgeItemCreation:
    """Test suite for KnowledgeItem value object creation and validation."""

    def test_minimal_knowledge_item_creation(self):
        """Test creating knowledge item with minimal required fields."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="enemy_position",
            information="Enemy seen at north gate",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
        )

        assert item.subject == "enemy_position"
        assert item.information == "Enemy seen at north gate"
        assert item.knowledge_type == KnowledgeType.FACTUAL
        assert item.certainty_level == CertaintyLevel.HIGH
        assert item.source == KnowledgeSource.DIRECT_OBSERVATION
        assert item.acquired_at == acquired_time
        assert item.expires_at is None
        assert item.tags == set()

    def test_full_knowledge_item_creation(self):
        """Test creating knowledge item with all fields populated."""
        acquired_time = datetime.now()
        expires_time = acquired_time + timedelta(hours=2)
        tags = {"combat", "urgent"}

        item = KnowledgeItem(
            subject="guard_patrol",
            information="Guards change shifts every 4 hours",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_ALLY,
            acquired_at=acquired_time,
            expires_at=expires_time,
            tags=tags,
        )

        assert item.subject == "guard_patrol"
        assert item.information == "Guards change shifts every 4 hours"
        assert item.knowledge_type == KnowledgeType.TACTICAL
        assert item.certainty_level == CertaintyLevel.MEDIUM
        assert item.source == KnowledgeSource.REPORTED_BY_ALLY
        assert item.acquired_at == acquired_time
        assert item.expires_at == expires_time
        assert item.tags == tags

    def test_tags_none_initialization(self):
        """Test that None tags are properly initialized to empty set."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            tags=None,
        )

        assert isinstance(item.tags, set)
        assert item.tags == set()

    def test_tags_list_conversion(self):
        """Test that tag lists are converted to sets."""
        acquired_time = datetime.now()
        tags_list = ["combat", "urgent", "combat"]  # Duplicate to test set conversion

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            tags=tags_list,
        )

        assert isinstance(item.tags, set)
        assert item.tags == {"combat", "urgent"}  # Duplicates removed


class TestKnowledgeItemValidation:
    """Test suite for KnowledgeItem validation logic."""

    def test_empty_subject_validation(self):
        """Test validation fails with empty subject."""
        acquired_time = datetime.now()

        with pytest.raises(ValueError, match="Knowledge subject cannot be empty"):
            KnowledgeItem(
                subject="",
                information="test_info",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired_time,
            )

    def test_whitespace_subject_validation(self):
        """Test validation fails with whitespace-only subject."""
        acquired_time = datetime.now()

        with pytest.raises(ValueError, match="Knowledge subject cannot be empty"):
            KnowledgeItem(
                subject="   \t\n  ",
                information="test_info",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired_time,
            )

    def test_empty_information_validation(self):
        """Test validation fails with empty information."""
        acquired_time = datetime.now()

        with pytest.raises(ValueError, match="Knowledge information cannot be empty"):
            KnowledgeItem(
                subject="test_subject",
                information="",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired_time,
            )

    def test_whitespace_information_validation(self):
        """Test validation fails with whitespace-only information."""
        acquired_time = datetime.now()

        with pytest.raises(ValueError, match="Knowledge information cannot be empty"):
            KnowledgeItem(
                subject="test_subject",
                information="   \t\n  ",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired_time,
            )

    def test_expiration_before_acquisition_validation(self):
        """Test validation fails when expiration time is before acquisition time."""
        acquired_time = datetime.now()
        expires_time = acquired_time - timedelta(hours=1)  # Before acquisition

        with pytest.raises(
            ValueError, match="Expiration time must be after acquisition time"
        ):
            KnowledgeItem(
                subject="test_subject",
                information="test_info",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired_time,
                expires_at=expires_time,
            )

    def test_expiration_equal_to_acquisition_validation(self):
        """Test validation fails when expiration time equals acquisition time."""
        acquired_time = datetime.now()
        expires_time = acquired_time  # Same time

        with pytest.raises(
            ValueError, match="Expiration time must be after acquisition time"
        ):
            KnowledgeItem(
                subject="test_subject",
                information="test_info",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=acquired_time,
                expires_at=expires_time,
            )


class TestKnowledgeItemBusinessLogic:
    """Test suite for KnowledgeItem business logic methods."""

    def test_is_current_no_expiration(self):
        """Test that knowledge without expiration is always current."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            expires_at=None,
        )

        # Should be current regardless of check time
        assert item.is_current()
        assert item.is_current(datetime.now() + timedelta(days=365))

    def test_is_current_before_expiration(self):
        """Test that knowledge is current before expiration time."""
        acquired_time = datetime.now()
        expires_time = acquired_time + timedelta(hours=2)

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            expires_at=expires_time,
        )

        # Should be current before expiration
        check_time = expires_time - timedelta(minutes=30)
        assert item.is_current(check_time)

    def test_is_current_after_expiration(self):
        """Test that knowledge is not current after expiration time."""
        acquired_time = datetime.now()
        expires_time = acquired_time + timedelta(hours=2)

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            expires_at=expires_time,
        )

        # Should not be current after expiration
        check_time = expires_time + timedelta(minutes=1)
        assert not item.is_current(check_time)

    def test_is_current_default_time(self):
        """Test is_current uses current time when no time provided."""
        acquired_time = datetime.now()
        expires_time = acquired_time + timedelta(hours=2)

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            expires_at=expires_time,
        )

        # Should be current now
        assert item.is_current()

    def test_get_reliability_score_absolute_direct(self):
        """Test reliability score for absolute certainty with direct observation."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
        )

        # Absolute certainty (1.0) * Direct observation (1.0) = 1.0
        assert item.get_reliability_score() == 1.0

    def test_get_reliability_score_high_certainty_ally_report(self):
        """Test reliability score for high certainty from ally report."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.REPORTED_BY_ALLY,
            acquired_at=acquired_time,
        )

        # High certainty (0.85) * Ally report (0.9) = 0.765
        expected_score = 0.85 * 0.9
        assert item.get_reliability_score() == expected_score

    def test_get_reliability_score_low_certainty_enemy_report(self):
        """Test reliability score for low certainty from enemy report."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_ENEMY,
            acquired_at=acquired_time,
        )

        # Low certainty (0.40) * Enemy report (0.5) = 0.20
        expected_score = 0.40 * 0.5
        assert item.get_reliability_score() == expected_score

    def test_get_reliability_score_unknown_certainty(self):
        """Test reliability score for unknown certainty."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.SPECULATION,
            certainty_level=CertaintyLevel.UNKNOWN,
            source=KnowledgeSource.SPECULATION,
            acquired_at=acquired_time,
        )

        # Unknown certainty (0.0) * Speculation (0.3) = 0.0
        assert item.get_reliability_score() == 0.0

    def test_has_tag_existing(self):
        """Test has_tag returns True for existing tags."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            tags={"combat", "urgent", "tactical"},
        )

        assert item.has_tag("combat")
        assert item.has_tag("urgent")
        assert item.has_tag("tactical")

    def test_has_tag_nonexistent(self):
        """Test has_tag returns False for non-existent tags."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            tags={"combat"},
        )

        assert not item.has_tag("peaceful")
        assert not item.has_tag("unknown")
        assert not item.has_tag("")

    def test_has_tag_empty_tags(self):
        """Test has_tag with empty tag set."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
            tags=set(),
        )

        assert not item.has_tag("any_tag")


class TestKnowledgeItemImmutableOperations:
    """Test suite for KnowledgeItem immutable operations."""

    def test_with_updated_certainty_creates_new_instance(self):
        """Test with_updated_certainty creates new instance with updated certainty."""
        acquired_time = datetime.now()

        original = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=acquired_time,
            tags={"test"},
        )

        updated = original.with_updated_certainty(CertaintyLevel.HIGH)

        # Original unchanged
        assert original.certainty_level == CertaintyLevel.LOW
        assert original.source == KnowledgeSource.REPORTED_BY_NEUTRAL

        # New instance has changes
        assert updated.certainty_level == CertaintyLevel.HIGH
        assert updated.source == KnowledgeSource.REPORTED_BY_NEUTRAL  # Unchanged
        assert updated.subject == original.subject  # Other fields unchanged
        assert updated.information == original.information
        assert updated.knowledge_type == original.knowledge_type
        assert updated.acquired_at == original.acquired_at
        assert updated.tags == original.tags

        # Different objects
        assert original is not updated

    def test_with_updated_certainty_and_source(self):
        """Test with_updated_certainty can also update source."""
        acquired_time = datetime.now()

        original = KnowledgeItem(
            subject="test_subject",
            information="test_info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=acquired_time,
        )

        updated = original.with_updated_certainty(
            CertaintyLevel.HIGH, KnowledgeSource.DIRECT_OBSERVATION
        )

        # Both certainty and source should be updated
        assert updated.certainty_level == CertaintyLevel.HIGH
        assert updated.source == KnowledgeSource.DIRECT_OBSERVATION

        # Original unchanged
        assert original.certainty_level == CertaintyLevel.LOW
        assert original.source == KnowledgeSource.REPORTED_BY_NEUTRAL


class TestKnowledgeBaseCreation:
    """Test suite for KnowledgeBase creation and validation."""

    def test_empty_knowledge_base_creation(self):
        """Test creating an empty knowledge base."""
        kb = KnowledgeBase(knowledge_items={})

        assert kb.knowledge_items == {}
        assert kb.get_total_knowledge_count() == 0
        assert kb.get_subjects_count() == 0

    def test_knowledge_base_with_items(self):
        """Test creating knowledge base with items."""
        acquired_time = datetime.now()

        item1 = KnowledgeItem(
            subject="enemy_position",
            information="Enemy at north gate",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
        )

        item2 = KnowledgeItem(
            subject="guard_patrol",
            information="Guards patrol every hour",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_ALLY,
            acquired_at=acquired_time,
        )

        knowledge_items = {"enemy_position": [item1], "guard_patrol": [item2]}

        kb = KnowledgeBase(knowledge_items=knowledge_items)

        assert kb.knowledge_items == knowledge_items
        assert kb.get_total_knowledge_count() == 2
        assert kb.get_subjects_count() == 2


class TestKnowledgeBaseValidation:
    """Test suite for KnowledgeBase validation logic."""

    def test_invalid_knowledge_items_type(self):
        """Test validation fails with non-dict knowledge_items."""
        with pytest.raises(ValueError, match="Knowledge items must be a dictionary"):
            KnowledgeBase(knowledge_items="invalid")

    def test_invalid_subject_items_type(self):
        """Test validation fails when subject items is not a list."""
        with pytest.raises(
            ValueError, match="Knowledge items for subject .* must be a list"
        ):
            KnowledgeBase(knowledge_items={"test_subject": "invalid"})

    def test_invalid_knowledge_item_type(self):
        """Test validation fails with invalid knowledge item type."""
        with pytest.raises(ValueError, match="Invalid knowledge item for subject"):
            KnowledgeBase(knowledge_items={"test_subject": ["invalid_item"]})

    def test_knowledge_item_subject_mismatch(self):
        """Test validation fails when knowledge item subject doesn't match key."""
        acquired_time = datetime.now()

        item = KnowledgeItem(
            subject="correct_subject",
            information="test_info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=acquired_time,
        )

        with pytest.raises(ValueError, match="Knowledge item subject mismatch"):
            KnowledgeBase(knowledge_items={"wrong_subject": [item]})


class TestKnowledgeBaseQuerying:
    """Test suite for KnowledgeBase querying methods."""

    @pytest.fixture
    def sample_knowledge_base(self):
        """Create a sample knowledge base for testing."""
        now = datetime.now()

        # Current knowledge
        item1 = KnowledgeItem(
            subject="enemy_position",
            information="Enemy at north gate",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
            expires_at=now + timedelta(hours=1),
        )

        # Expired knowledge
        item2 = KnowledgeItem(
            subject="enemy_position",
            information="Enemy was at south gate",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now - timedelta(hours=2),
            expires_at=now - timedelta(minutes=30),  # Expired
        )

        # Low reliability knowledge
        item3 = KnowledgeItem(
            subject="guard_patrol",
            information="Guards might change shifts soon",
            knowledge_type=KnowledgeType.SPECULATION,
            certainty_level=CertaintyLevel.MINIMAL,
            source=KnowledgeSource.SPECULATION,
            acquired_at=now,
        )

        # High reliability knowledge
        item4 = KnowledgeItem(
            subject="guard_patrol",
            information="Guards change every 4 hours",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.REPORTED_BY_ALLY,
            acquired_at=now,
        )

        knowledge_items = {
            "enemy_position": [item1, item2],
            "guard_patrol": [item3, item4],
        }

        return KnowledgeBase(knowledge_items=knowledge_items)

    def test_get_knowledge_about_existing_subject(self, sample_knowledge_base):
        """Test getting knowledge about an existing subject."""
        knowledge = sample_knowledge_base.get_knowledge_about("enemy_position")

        # Should return current knowledge, sorted by reliability
        assert len(knowledge) == 1  # Only current knowledge
        assert knowledge[0].information == "Enemy at north gate"
        assert knowledge[0].certainty_level == CertaintyLevel.ABSOLUTE

    def test_get_knowledge_about_nonexistent_subject(self, sample_knowledge_base):
        """Test getting knowledge about a non-existent subject."""
        knowledge = sample_knowledge_base.get_knowledge_about("nonexistent_subject")
        assert knowledge == []

    def test_get_knowledge_about_with_min_reliability(self, sample_knowledge_base):
        """Test getting knowledge with minimum reliability threshold."""
        # High reliability threshold should exclude speculative knowledge
        knowledge = sample_knowledge_base.get_knowledge_about(
            "guard_patrol", min_reliability=0.5
        )

        assert len(knowledge) == 1
        assert knowledge[0].information == "Guards change every 4 hours"
        assert knowledge[0].certainty_level == CertaintyLevel.HIGH

    def test_get_knowledge_about_sorting(self, sample_knowledge_base):
        """Test that knowledge is sorted by reliability then by acquisition time."""
        # Get all current guard patrol knowledge
        knowledge = sample_knowledge_base.get_knowledge_about(
            "guard_patrol", min_reliability=0.0
        )

        assert len(knowledge) == 2
        # First item should have higher reliability
        assert (
            knowledge[0].get_reliability_score() > knowledge[1].get_reliability_score()
        )

    def test_get_most_reliable_knowledge_existing(self, sample_knowledge_base):
        """Test getting most reliable knowledge for existing subject."""
        most_reliable = sample_knowledge_base.get_most_reliable_knowledge(
            "guard_patrol"
        )

        assert most_reliable is not None
        assert most_reliable.information == "Guards change every 4 hours"
        assert most_reliable.certainty_level == CertaintyLevel.HIGH

    def test_get_most_reliable_knowledge_nonexistent(self, sample_knowledge_base):
        """Test getting most reliable knowledge for non-existent subject."""
        most_reliable = sample_knowledge_base.get_most_reliable_knowledge("nonexistent")
        assert most_reliable is None

    def test_has_knowledge_about_with_sufficient_certainty(self, sample_knowledge_base):
        """Test has_knowledge_about with sufficient certainty."""
        # Should have knowledge about enemy position with high certainty
        assert sample_knowledge_base.has_knowledge_about(
            "enemy_position", CertaintyLevel.HIGH
        )

        # Should have knowledge about guard patrol with minimal certainty
        assert sample_knowledge_base.has_knowledge_about(
            "guard_patrol", CertaintyLevel.MINIMAL
        )

    def test_has_knowledge_about_insufficient_certainty(self, sample_knowledge_base):
        """Test has_knowledge_about with insufficient certainty."""
        # Guard patrol knowledge might not meet absolute certainty requirement
        guard_knowledge = sample_knowledge_base.get_knowledge_about("guard_patrol")
        absolute_knowledge = [
            k for k in guard_knowledge if k.certainty_level == CertaintyLevel.ABSOLUTE
        ]

        if not absolute_knowledge:
            assert not sample_knowledge_base.has_knowledge_about(
                "guard_patrol", CertaintyLevel.ABSOLUTE
            )

    def test_has_knowledge_about_nonexistent(self, sample_knowledge_base):
        """Test has_knowledge_about for non-existent subject."""
        assert not sample_knowledge_base.has_knowledge_about(
            "nonexistent", CertaintyLevel.MINIMAL
        )


class TestKnowledgeBaseFiltering:
    """Test suite for KnowledgeBase filtering methods."""

    @pytest.fixture
    def diverse_knowledge_base(self):
        """Create a knowledge base with diverse knowledge types and sources."""
        now = datetime.now()

        items = [
            KnowledgeItem(
                subject="location_a",
                information="Location A is secure",
                knowledge_type=KnowledgeType.TACTICAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=now,
                tags={"security", "tactical"},
            ),
            KnowledgeItem(
                subject="location_b",
                information="Location B has enemies",
                knowledge_type=KnowledgeType.FACTUAL,
                certainty_level=CertaintyLevel.ABSOLUTE,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=now,
                tags={"enemy", "combat"},
            ),
            KnowledgeItem(
                subject="character_x",
                information="Character X is trustworthy",
                knowledge_type=KnowledgeType.PERSONAL,
                certainty_level=CertaintyLevel.MEDIUM,
                source=KnowledgeSource.HISTORICAL_RECORD,
                acquired_at=now,
                tags={"personality", "trust"},
            ),
            KnowledgeItem(
                subject="weather",
                information="Storm approaching",
                knowledge_type=KnowledgeType.ENVIRONMENTAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.MAGICAL_DIVINATION,
                acquired_at=now,
                expires_at=now + timedelta(hours=6),
            ),
        ]

        knowledge_items = {}
        for item in items:
            if item.subject not in knowledge_items:
                knowledge_items[item.subject] = []
            knowledge_items[item.subject].append(item)

        return KnowledgeBase(knowledge_items=knowledge_items)

    def test_get_subjects_by_type(self, diverse_knowledge_base):
        """Test filtering subjects by knowledge type."""
        tactical_subjects = diverse_knowledge_base.get_subjects_by_type(
            KnowledgeType.TACTICAL
        )
        assert tactical_subjects == ["location_a"]

        factual_subjects = diverse_knowledge_base.get_subjects_by_type(
            KnowledgeType.FACTUAL
        )
        assert factual_subjects == ["location_b"]

        personal_subjects = diverse_knowledge_base.get_subjects_by_type(
            KnowledgeType.PERSONAL
        )
        assert personal_subjects == ["character_x"]

        nonexistent_subjects = diverse_knowledge_base.get_subjects_by_type(
            KnowledgeType.RUMOR
        )
        assert nonexistent_subjects == []

    def test_get_subjects_by_tag(self, diverse_knowledge_base):
        """Test filtering subjects by tag."""
        security_subjects = diverse_knowledge_base.get_subjects_by_tag("security")
        assert security_subjects == ["location_a"]

        combat_subjects = diverse_knowledge_base.get_subjects_by_tag("combat")
        assert combat_subjects == ["location_b"]

        nonexistent_tag_subjects = diverse_knowledge_base.get_subjects_by_tag(
            "nonexistent"
        )
        assert nonexistent_tag_subjects == []

    def test_get_knowledge_by_source(self, diverse_knowledge_base):
        """Test filtering knowledge by source."""
        direct_obs_knowledge = diverse_knowledge_base.get_knowledge_by_source(
            KnowledgeSource.DIRECT_OBSERVATION
        )

        assert len(direct_obs_knowledge) == 2  # location_a and location_b
        assert "location_a" in direct_obs_knowledge
        assert "location_b" in direct_obs_knowledge

        historical_knowledge = diverse_knowledge_base.get_knowledge_by_source(
            KnowledgeSource.HISTORICAL_RECORD
        )
        assert len(historical_knowledge) == 1
        assert "character_x" in historical_knowledge

        nonexistent_source_knowledge = diverse_knowledge_base.get_knowledge_by_source(
            KnowledgeSource.PSYCHIC_READING
        )
        assert nonexistent_source_knowledge == {}

    def test_get_stale_knowledge(self):
        """Test getting stale/expired knowledge."""
        now = datetime.now()

        current_item = KnowledgeItem(
            subject="current_info",
            information="Still valid",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
            expires_at=now + timedelta(hours=1),  # Still valid
        )

        stale_item = KnowledgeItem(
            subject="stale_info",
            information="No longer valid",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now - timedelta(hours=2),
            expires_at=now - timedelta(minutes=30),  # Expired
        )

        knowledge_items = {"current_info": [current_item], "stale_info": [stale_item]}

        kb = KnowledgeBase(knowledge_items=knowledge_items)
        stale_knowledge = kb.get_stale_knowledge(now)

        assert len(stale_knowledge) == 1
        assert "stale_info" in stale_knowledge
        assert stale_knowledge["stale_info"][0] == stale_item


class TestKnowledgeBaseImmutableOperations:
    """Test suite for KnowledgeBase immutable operations."""

    def test_add_knowledge_creates_new_instance(self):
        """Test add_knowledge creates new instance with additional knowledge."""
        now = datetime.now()

        original_item = KnowledgeItem(
            subject="original_subject",
            information="Original info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
        )

        new_item = KnowledgeItem(
            subject="new_subject",
            information="New info",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_ALLY,
            acquired_at=now,
        )

        original_kb = KnowledgeBase(
            knowledge_items={"original_subject": [original_item]}
        )
        updated_kb = original_kb.add_knowledge(new_item)

        # Original unchanged
        assert original_kb.get_subjects_count() == 1
        assert "new_subject" not in original_kb.knowledge_items

        # New instance has additional knowledge
        assert updated_kb.get_subjects_count() == 2
        assert "original_subject" in updated_kb.knowledge_items
        assert "new_subject" in updated_kb.knowledge_items

        # Different objects
        assert original_kb is not updated_kb

    def test_add_knowledge_to_existing_subject(self):
        """Test adding knowledge to existing subject."""
        now = datetime.now()

        original_item = KnowledgeItem(
            subject="test_subject",
            information="Original info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
        )

        additional_item = KnowledgeItem(
            subject="test_subject",
            information="Additional info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=now,
        )

        original_kb = KnowledgeBase(knowledge_items={"test_subject": [original_item]})
        updated_kb = original_kb.add_knowledge(additional_item)

        # Should have both items for the same subject
        test_knowledge = updated_kb.get_knowledge_about(
            "test_subject", min_reliability=0.0
        )
        assert len(test_knowledge) == 2

        # Original should be unchanged
        original_knowledge = original_kb.get_knowledge_about(
            "test_subject", min_reliability=0.0
        )
        assert len(original_knowledge) == 1

    def test_update_knowledge(self):
        """Test update_knowledge method."""
        now = datetime.now()

        original_item = KnowledgeItem(
            subject="test_subject",
            information="Original info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=now,
        )

        updated_item = KnowledgeItem(
            subject="test_subject",
            information="Updated info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
        )

        original_kb = KnowledgeBase(knowledge_items={"test_subject": [original_item]})
        updated_kb = original_kb.update_knowledge("test_subject", updated_item)

        # Should add the updated item (not replace)
        test_knowledge = updated_kb.get_knowledge_about(
            "test_subject", min_reliability=0.0
        )
        assert len(test_knowledge) == 2

    def test_update_knowledge_subject_mismatch(self):
        """Test update_knowledge validates subject match."""
        now = datetime.now()

        original_item = KnowledgeItem(
            subject="test_subject",
            information="Original info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
        )

        wrong_subject_item = KnowledgeItem(
            subject="wrong_subject",
            information="Wrong subject info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
        )

        kb = KnowledgeBase(knowledge_items={"test_subject": [original_item]})

        with pytest.raises(
            ValueError, match="Updated knowledge item subject must match"
        ):
            kb.update_knowledge("test_subject", wrong_subject_item)


class TestKnowledgeBaseStatistics:
    """Test suite for KnowledgeBase statistics methods."""

    def test_get_total_knowledge_count(self):
        """Test getting total knowledge count."""
        now = datetime.now()

        items = []
        for i in range(5):
            items.append(
                KnowledgeItem(
                    subject=f"subject_{i}",
                    information=f"Info {i}",
                    knowledge_type=KnowledgeType.FACTUAL,
                    certainty_level=CertaintyLevel.HIGH,
                    source=KnowledgeSource.DIRECT_OBSERVATION,
                    acquired_at=now,
                )
            )

        knowledge_items = {}
        for item in items:
            knowledge_items[item.subject] = [item]

        # Add multiple items for one subject
        knowledge_items["subject_0"].append(
            KnowledgeItem(
                subject="subject_0",
                information="Additional info",
                knowledge_type=KnowledgeType.RUMOR,
                certainty_level=CertaintyLevel.LOW,
                source=KnowledgeSource.REPORTED_BY_NEUTRAL,
                acquired_at=now,
            )
        )

        kb = KnowledgeBase(knowledge_items=knowledge_items)

        # Should count all items, including multiple per subject
        assert kb.get_total_knowledge_count() == 6

    def test_get_subjects_count(self):
        """Test getting subjects count."""
        now = datetime.now()

        items = []
        for i in range(3):
            items.append(
                KnowledgeItem(
                    subject=f"subject_{i}",
                    information=f"Info {i}",
                    knowledge_type=KnowledgeType.FACTUAL,
                    certainty_level=CertaintyLevel.HIGH,
                    source=KnowledgeSource.DIRECT_OBSERVATION,
                    acquired_at=now,
                )
            )

        knowledge_items = {}
        for item in items:
            knowledge_items[item.subject] = [item]

        kb = KnowledgeBase(knowledge_items=knowledge_items)

        assert kb.get_subjects_count() == 3

    def test_empty_knowledge_base_statistics(self):
        """Test statistics for empty knowledge base."""
        kb = KnowledgeBase(knowledge_items={})

        assert kb.get_total_knowledge_count() == 0
        assert kb.get_subjects_count() == 0


class TestComplexScenarios:
    """Test suite for complex knowledge management scenarios."""

    def test_intelligence_gathering_scenario(self):
        """Test a complex intelligence gathering scenario."""
        now = datetime.now()

        # Initial rumor from unreliable source
        initial_rumor = KnowledgeItem(
            subject="enemy_base",
            information="Enemy base might be in the mountains",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=now - timedelta(days=2),
            tags={"unconfirmed", "strategic"},
        )

        # Ally report confirming general area
        ally_confirmation = KnowledgeItem(
            subject="enemy_base",
            information="Enemy activity spotted in mountain region",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_ALLY,
            acquired_at=now - timedelta(days=1),
            tags={"confirmed", "strategic"},
        )

        # Direct observation of exact location
        direct_observation = KnowledgeItem(
            subject="enemy_base",
            information="Enemy base located at coordinates X,Y",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=now,
            expires_at=now + timedelta(hours=12),  # Tactical info becomes stale
            tags={"confirmed", "tactical", "current"},
        )

        # Build knowledge base progressively
        kb = KnowledgeBase(knowledge_items={})
        kb = kb.add_knowledge(initial_rumor)
        kb = kb.add_knowledge(ally_confirmation)
        kb = kb.add_knowledge(direct_observation)

        # Most reliable knowledge should be direct observation
        most_reliable = kb.get_most_reliable_knowledge("enemy_base")
        assert most_reliable == direct_observation
        assert most_reliable.get_reliability_score() == 1.0

        # Should have knowledge about enemy base with high confidence
        assert kb.has_knowledge_about("enemy_base", CertaintyLevel.HIGH)

        # Should be able to filter by tags
        current_subjects = kb.get_subjects_by_tag("current")
        assert current_subjects == ["enemy_base"]

        # Knowledge should be sorted by reliability
        all_knowledge = kb.get_knowledge_about("enemy_base", min_reliability=0.0)
        assert len(all_knowledge) == 3
        assert all_knowledge[0] == direct_observation  # Highest reliability
        assert (
            all_knowledge[0].get_reliability_score()
            >= all_knowledge[1].get_reliability_score()
        )
        assert (
            all_knowledge[1].get_reliability_score()
            >= all_knowledge[2].get_reliability_score()
        )

    def test_information_expiry_scenario(self):
        """Test scenario where information becomes stale over time."""
        base_time = datetime.now()

        # Short-term tactical information
        troop_movement = KnowledgeItem(
            subject="enemy_troops",
            information="Enemy troops moving south",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=base_time,
            expires_at=base_time + timedelta(hours=2),
        )

        # Long-term strategic information
        base_location = KnowledgeItem(
            subject="enemy_base",
            information="Enemy base in northern mountains",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=base_time,
            expires_at=base_time + timedelta(days=7),
        )

        # Permanent historical information
        battle_outcome = KnowledgeItem(
            subject="last_battle",
            information="Won decisive victory at River Crossing",
            knowledge_type=KnowledgeType.HISTORICAL,
            certainty_level=CertaintyLevel.ABSOLUTE,
            source=KnowledgeSource.HISTORICAL_RECORD,
            acquired_at=base_time - timedelta(days=30),
            expires_at=None,  # Never expires
        )

        kb = KnowledgeBase(
            knowledge_items={
                "enemy_troops": [troop_movement],
                "enemy_base": [base_location],
                "last_battle": [battle_outcome],
            }
        )

        # Initially, all knowledge should be current
        assert troop_movement.is_current(base_time)
        assert base_location.is_current(base_time)
        assert battle_outcome.is_current(base_time)

        # After 3 hours, tactical info should be stale
        future_time = base_time + timedelta(hours=3)
        assert not troop_movement.is_current(future_time)
        assert base_location.is_current(future_time)
        assert battle_outcome.is_current(future_time)

        # Check stale knowledge detection
        stale_knowledge = kb.get_stale_knowledge(future_time)
        assert len(stale_knowledge) == 1
        assert "enemy_troops" in stale_knowledge

        # Current knowledge should exclude stale items
        current_knowledge = kb.get_knowledge_about("enemy_troops", future_time)
        assert len(current_knowledge) == 0
