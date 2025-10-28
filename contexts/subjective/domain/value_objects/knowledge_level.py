#!/usr/bin/env python3
"""
Knowledge Level Value Object

This module implements value objects for managing knowledge states,
information certainty levels, and knowledge propagation in the subjective context.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set


class KnowledgeType(Enum):
    """Types of knowledge that can be possessed."""

    FACTUAL = "factual"  # Direct observation or confirmed information
    INFERENTIAL = "inferential"  # Deduced from available evidence
    RUMOR = "rumor"  # Unverified information from others
    SPECULATION = "speculation"  # Guessed or assumed information
    HISTORICAL = "historical"  # Past events or conditions
    TACTICAL = "tactical"  # Military/strategic information
    PERSONAL = "personal"  # Information about specific individuals
    ENVIRONMENTAL = "environmental"  # Information about locations/conditions


class CertaintyLevel(Enum):
    """Levels of certainty for knowledge."""

    ABSOLUTE = "absolute"  # 100% certain, directly observed
    HIGH = "high"  # 80-99% certain, strong evidence
    MEDIUM = "medium"  # 50-79% certain, some evidence
    LOW = "low"  # 20-49% certain, weak evidence
    MINIMAL = "minimal"  # 1-19% certain, very weak evidence
    UNKNOWN = "unknown"  # 0% certain, no reliable information


class KnowledgeSource(Enum):
    """Sources of knowledge acquisition."""

    DIRECT_OBSERVATION = "direct_observation"
    REPORTED_BY_ALLY = "reported_by_ally"
    REPORTED_BY_NEUTRAL = "reported_by_neutral"
    REPORTED_BY_ENEMY = "reported_by_enemy"
    INTERCEPTED_COMMUNICATION = "intercepted_communication"
    DEDUCTION = "deduction"
    SPECULATION = "speculation"
    HISTORICAL_RECORD = "historical_record"
    MAGICAL_DIVINATION = "magical_divination"
    PSYCHIC_READING = "psychic_reading"


@dataclass(frozen=True)
class KnowledgeItem:
    """
    Value object representing a single piece of knowledge.

    This encapsulates information along with metadata about its reliability,
    source, and temporal validity.
    """

    subject: str  # What this knowledge is about (entity ID, location, etc.)
    information: str  # The actual information content
    knowledge_type: KnowledgeType
    certainty_level: CertaintyLevel
    source: KnowledgeSource
    acquired_at: datetime
    expires_at: Optional[datetime] = None  # When this knowledge becomes stale
    tags: Set[str] = None  # Additional categorization tags

    def __post_init__(self):
        """Validate knowledge item parameters."""
        if not self.subject or not self.subject.strip():
            raise ValueError("Knowledge subject cannot be empty")

        if not self.information or not self.information.strip():
            raise ValueError("Knowledge information cannot be empty")

        if self.expires_at and self.expires_at <= self.acquired_at:
            raise ValueError("Expiration time must be after acquisition time")

        # Initialize empty set for tags if None
        if self.tags is None:
            object.__setattr__(self, "tags", set())
        elif not isinstance(self.tags, set):
            object.__setattr__(self, "tags", set(self.tags))

    def is_current(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this knowledge is still current/valid."""
        if not self.expires_at:
            return True  # No expiration, always current

        check_time = current_time or datetime.now()
        return check_time < self.expires_at

    def get_reliability_score(self) -> float:
        """Calculate a reliability score based on certainty and source."""
        # Base certainty scores
        certainty_scores = {
            CertaintyLevel.ABSOLUTE: 1.0,
            CertaintyLevel.HIGH: 0.85,
            CertaintyLevel.MEDIUM: 0.65,
            CertaintyLevel.LOW: 0.40,
            CertaintyLevel.MINIMAL: 0.20,
            CertaintyLevel.UNKNOWN: 0.0,
        }

        # Source reliability modifiers
        source_modifiers = {
            KnowledgeSource.DIRECT_OBSERVATION: 1.0,
            KnowledgeSource.REPORTED_BY_ALLY: 0.9,
            KnowledgeSource.REPORTED_BY_NEUTRAL: 0.7,
            KnowledgeSource.REPORTED_BY_ENEMY: 0.5,
            KnowledgeSource.INTERCEPTED_COMMUNICATION: 0.8,
            KnowledgeSource.DEDUCTION: 0.75,
            KnowledgeSource.SPECULATION: 0.3,
            KnowledgeSource.HISTORICAL_RECORD: 0.85,
            KnowledgeSource.MAGICAL_DIVINATION: 0.8,
            KnowledgeSource.PSYCHIC_READING: 0.7,
        }

        base_score = certainty_scores[self.certainty_level]
        source_modifier = source_modifiers[self.source]

        return base_score * source_modifier

    def has_tag(self, tag: str) -> bool:
        """Check if knowledge has a specific tag."""
        return tag in self.tags

    def with_updated_certainty(
        self,
        new_certainty: CertaintyLevel,
        new_source: Optional[KnowledgeSource] = None,
    ) -> "KnowledgeItem":
        """Create a new knowledge item with updated certainty level."""
        return KnowledgeItem(
            subject=self.subject,
            information=self.information,
            knowledge_type=self.knowledge_type,
            certainty_level=new_certainty,
            source=new_source or self.source,
            acquired_at=self.acquired_at,
            expires_at=self.expires_at,
            tags=self.tags,
        )


@dataclass(frozen=True)
class KnowledgeBase:
    """
    Value object representing a collection of knowledge items.

    This manages the complete knowledge state of an entity, providing
    methods for querying, filtering, and analyzing available information.
    """

    knowledge_items: Dict[str, List[KnowledgeItem]]  # subject -> knowledge items

    def __post_init__(self):
        """Validate and organize knowledge base."""
        if not isinstance(self.knowledge_items, dict):
            raise ValueError("Knowledge items must be a dictionary")

        # Validate all knowledge items
        for subject, items in self.knowledge_items.items():
            if not isinstance(items, list):
                raise ValueError(
                    f"Knowledge items for subject '{subject}' must be a list"
                )

            for item in items:
                if not isinstance(item, KnowledgeItem):
                    raise ValueError(f"Invalid knowledge item for subject '{subject}'")
                if item.subject != subject:
                    raise ValueError(
                        f"Knowledge item subject mismatch: expected '{subject}', got '{item.subject}'"
                    )

    def get_knowledge_about(
        self,
        subject: str,
        current_time: Optional[datetime] = None,
        min_reliability: float = 0.0,
    ) -> List[KnowledgeItem]:
        """Get all current knowledge about a specific subject."""
        if subject not in self.knowledge_items:
            return []

        items = self.knowledge_items[subject]
        filtered_items = []

        for item in items:
            if (
                item.is_current(current_time)
                and item.get_reliability_score() >= min_reliability
            ):
                filtered_items.append(item)

        # Sort by reliability score (descending) then by acquisition time (descending)
        return sorted(
            filtered_items,
            key=lambda x: (x.get_reliability_score(), x.acquired_at),
            reverse=True,
        )

    def get_most_reliable_knowledge(
        self, subject: str, current_time: Optional[datetime] = None
    ) -> Optional[KnowledgeItem]:
        """Get the most reliable current knowledge about a subject."""
        knowledge = self.get_knowledge_about(subject, current_time)
        return knowledge[0] if knowledge else None

    def has_knowledge_about(
        self, subject: str, min_certainty: CertaintyLevel = CertaintyLevel.MINIMAL
    ) -> bool:
        """Check if entity has any knowledge about a subject (including expired knowledge)."""
        if subject not in self.knowledge_items:
            return False

        # Create certainty level ordering (higher number = more certain)
        certainty_order = {
            CertaintyLevel.UNKNOWN: 0,
            CertaintyLevel.MINIMAL: 1,
            CertaintyLevel.LOW: 2,
            CertaintyLevel.MEDIUM: 3,
            CertaintyLevel.HIGH: 4,
            CertaintyLevel.ABSOLUTE: 5,
        }

        min_level = certainty_order[min_certainty]
        items = self.knowledge_items[subject]
        return any(certainty_order[item.certainty_level] >= min_level for item in items)

    def get_subjects_by_type(self, knowledge_type: KnowledgeType) -> List[str]:
        """Get all subjects that have knowledge of a specific type."""
        subjects = []
        for subject, items in self.knowledge_items.items():
            if any(item.knowledge_type == knowledge_type for item in items):
                subjects.append(subject)
        return subjects

    def get_subjects_by_tag(self, tag: str) -> List[str]:
        """Get all subjects that have knowledge with a specific tag."""
        subjects = []
        for subject, items in self.knowledge_items.items():
            if any(item.has_tag(tag) for item in items):
                subjects.append(subject)
        return subjects

    def get_stale_knowledge(
        self, current_time: Optional[datetime] = None
    ) -> Dict[str, List[KnowledgeItem]]:
        """Get all knowledge that has become stale/expired."""
        check_time = current_time or datetime.now()
        stale_knowledge = {}

        for subject, items in self.knowledge_items.items():
            stale_items = [item for item in items if not item.is_current(check_time)]
            if stale_items:
                stale_knowledge[subject] = stale_items

        return stale_knowledge

    def get_knowledge_by_source(
        self, source: KnowledgeSource
    ) -> Dict[str, List[KnowledgeItem]]:
        """Get all knowledge from a specific source."""
        filtered_knowledge = {}

        for subject, items in self.knowledge_items.items():
            source_items = [item for item in items if item.source == source]
            if source_items:
                filtered_knowledge[subject] = source_items

        return filtered_knowledge

    def add_knowledge(self, knowledge_item: KnowledgeItem) -> "KnowledgeBase":
        """Create a new knowledge base with an additional knowledge item."""
        new_knowledge_items = dict(self.knowledge_items)

        subject = knowledge_item.subject
        if subject not in new_knowledge_items:
            new_knowledge_items[subject] = []
        else:
            new_knowledge_items[subject] = list(new_knowledge_items[subject])

        new_knowledge_items[subject].append(knowledge_item)

        return KnowledgeBase(knowledge_items=new_knowledge_items)

    def update_knowledge(
        self, subject: str, updated_item: KnowledgeItem
    ) -> "KnowledgeBase":
        """Create a new knowledge base with updated knowledge about a subject."""
        if updated_item.subject != subject:
            raise ValueError(
                "Updated knowledge item subject must match the specified subject"
            )

        return self.add_knowledge(updated_item)

    def get_total_knowledge_count(self) -> int:
        """Get the total number of knowledge items."""
        return sum(len(items) for items in self.knowledge_items.values())

    def get_subjects_count(self) -> int:
        """Get the number of subjects with knowledge."""
        return len(self.knowledge_items)
