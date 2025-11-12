#!/usr/bin/env python3
"""
Story Element Entity

This module defines the StoryElement entity, which serves as a base
for narrative elements that have identity and can change over time.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from ..value_objects.narrative_id import NarrativeId


@dataclass
class StoryElement:
    """
    Base entity for narrative elements with identity.

    Story elements are entities that have identity and can change
    over time while maintaining that identity. This serves as a
    base class for more specific narrative entities.
    """

    element_id: NarrativeId
    element_type: str
    name: str
    description: str = ""

    # Identity and lifecycle
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    # Element state
    is_active: bool = True
    status: str = "draft"  # draft, active, completed, archived

    # Relationships
    parent_element_id: Optional[NarrativeId] = None
    child_element_ids: Set[NarrativeId] = field(default_factory=set)
    related_element_ids: Set[NarrativeId] = field(default_factory=set)

    # Tagging and categorization
    tags: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)

    # Metadata
    properties: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def update_element(self, **kwargs) -> None:
        """
        Update element properties and increment version.

        Args:
            **kwargs: Properties to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def add_child_element(self, child_id: NarrativeId) -> None:
        """Add a child element relationship."""
        self.child_element_ids.add(child_id)
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def remove_child_element(self, child_id: NarrativeId) -> None:
        """Remove a child element relationship."""
        self.child_element_ids.discard(child_id)
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def add_related_element(self, related_id: NarrativeId) -> None:
        """Add a related element relationship."""
        self.related_element_ids.add(related_id)
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def add_tag(self, tag: str) -> None:
        """Add a tag to this element."""
        self.tags.add(tag)
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this element."""
        self.tags.discard(tag)
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def add_category(self, category: str) -> None:
        """Add a category to this element."""
        self.categories.add(category)
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def has_tag(self, tag: str) -> bool:
        """Check if element has a specific tag."""
        return tag in self.tags

    def has_category(self, category: str) -> bool:
        """Check if element has a specific category."""
        return category in self.categories

    def get_property(self, key: str, default=None):
        """Get a property value with optional default."""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """Set a property value."""
        self.properties[key] = value
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def archive(self) -> None:
        """Archive this element."""
        self.status = "archived"
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def activate(self) -> None:
        """Activate this element."""
        self.is_active = True
        if self.status == "archived":
            self.status = "active"
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"StoryElement('{self.name}', type={self.element_type}, status={self.status})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"StoryElement(id={self.element_id}, "
            f"type='{self.element_type}', "
            f"name='{self.name}', "
            f"version={self.version})"
        )
