#!/usr/bin/env python3
"""World Rule Domain Entity.

This module defines the WorldRule entity which represents the fundamental laws,
magic systems, and physics constraints of a world setting. World rules provide
the bedrock for consistent narrative generation by defining what is possible
and what consequences arise from actions.

Why World Rules matter: A well-defined rule system prevents narrative
contradictions. When a character attempts to use magic, the system can check
whether the action is valid, what costs apply, and what consequences follow.
This makes AI-generated narratives internally consistent.

Typical usage example:
    >>> from src.contexts.world.domain.entities import WorldRule
    >>> magic_rule = WorldRule(
    ...     name="The Law of Equivalent Exchange",
    ...     description="Magic requires equal sacrifice.",
    ...     consequence="The caster loses something of equal value.",
    ...     exceptions=["Divine magic ignores this law"]
    ... )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .entity import Entity


@dataclass(eq=False)
class WorldRule(Entity):
    """World Rule Entity.

    Represents a fundamental law or constraint of the world. World rules define
    what is possible, what costs are required, and what happens when rules are
    invoked or violated. This enables consistent world-building across narratives.

    Why track rules: Rules establish boundaries that make stories believable:
    - Magic systems need costs to prevent deus ex machina solutions
    - Physical laws create tension and stakes
    - Social rules define character expectations
    - Exceptions create narrative opportunities for special characters

    Attributes:
        name: Short, memorable name for the rule (e.g., "Law of Gravity").
        description: Full explanation of what the rule entails.
        consequence: What happens when this rule is invoked/violated.
        exceptions: Cases where this rule does not apply or is modified.
        category: Optional grouping (magic, physics, social, divine, etc.).
        severity: How strictly enforced (0=guideline, 100=absolute law).
        related_rule_ids: IDs of related or dependent rules.
        metadata: Additional flexible data for specific use cases.
    """

    name: str = ""
    description: str = ""
    consequence: str = ""
    exceptions: List[str] = field(default_factory=list)
    category: str = ""
    severity: int = 50
    related_rule_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def _validate_business_rules(self) -> List[str]:
        """Validate WorldRule-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("World rule name cannot be empty")

        if len(self.name) > 200:
            errors.append("World rule name cannot exceed 200 characters")

        if len(self.description) > 5000:
            errors.append("World rule description cannot exceed 5000 characters")

        if len(self.consequence) > 2000:
            errors.append("World rule consequence cannot exceed 2000 characters")

        if len(self.exceptions) > 20:
            errors.append("World rule cannot have more than 20 exceptions")

        for exception in self.exceptions:
            if not exception or not exception.strip():
                errors.append("Exceptions cannot be empty strings")
                break
            if len(exception) > 500:
                errors.append(
                    f"Exception '{exception[:30]}...' exceeds 500 character limit"
                )

        if self.severity < 0 or self.severity > 100:
            errors.append("Severity must be between 0 and 100")

        if len(self.category) > 50:
            errors.append("Category cannot exceed 50 characters")

        return errors

    def update_name(self, name: str) -> None:
        """Update the rule's name.

        Args:
            name: New name for the rule.

        Raises:
            ValueError: If name is empty or too long.
        """
        if not name or not name.strip():
            raise ValueError("World rule name cannot be empty")
        if len(name) > 200:
            raise ValueError("World rule name cannot exceed 200 characters")

        self.name = name.strip()
        self.touch()

    def update_description(self, description: str) -> None:
        """Update the rule's description.

        Args:
            description: New description explaining the rule.
        """
        if len(description) > 5000:
            raise ValueError("Description cannot exceed 5000 characters")
        self.description = description.strip() if description else ""
        self.touch()

    def update_consequence(self, consequence: str) -> None:
        """Update what happens when the rule is invoked/violated.

        Args:
            consequence: Description of the consequence.
        """
        if len(consequence) > 2000:
            raise ValueError("Consequence cannot exceed 2000 characters")
        self.consequence = consequence.strip() if consequence else ""
        self.touch()

    def set_category(self, category: str) -> None:
        """Set the rule's category.

        Args:
            category: Category string (e.g., "magic", "physics", "social").
        """
        if len(category) > 50:
            raise ValueError("Category cannot exceed 50 characters")
        self.category = category.strip().lower() if category else ""
        self.touch()

    def set_severity(self, severity: int) -> None:
        """Set how strictly this rule is enforced.

        Args:
            severity: Value from 0 (guideline) to 100 (absolute law).

        Raises:
            ValueError: If severity is out of range.
        """
        if severity < 0 or severity > 100:
            raise ValueError("Severity must be between 0 and 100")
        self.severity = severity
        self.touch()

    def add_exception(self, exception: str) -> bool:
        """Add an exception to this rule.

        Args:
            exception: Description of when the rule doesn't apply.

        Returns:
            True if exception was added, False if duplicate or invalid.

        Raises:
            ValueError: If exception limit would be exceeded or text too long.
        """
        if not exception or not exception.strip():
            return False

        exception_normalized = exception.strip()
        if len(exception_normalized) > 500:
            raise ValueError("Exception cannot exceed 500 characters")

        if len(self.exceptions) >= 20:
            raise ValueError("Cannot add more than 20 exceptions")

        # Check for duplicate (case-insensitive)
        if exception_normalized.lower() not in [e.lower() for e in self.exceptions]:
            self.exceptions.append(exception_normalized)
            self.touch()
            return True
        return False

    def remove_exception(self, exception: str) -> bool:
        """Remove an exception from this rule.

        Args:
            exception: Exception text to remove.

        Returns:
            True if exception was found and removed.
        """
        exception_lower = exception.strip().lower()
        for existing in self.exceptions:
            if existing.lower() == exception_lower:
                self.exceptions.remove(existing)
                self.touch()
                return True
        return False

    def has_exception(self, exception: str) -> bool:
        """Check if rule has a specific exception (case-insensitive).

        Args:
            exception: Exception text to check for.

        Returns:
            True if exception exists.
        """
        exception_lower = exception.strip().lower()
        return exception_lower in [e.lower() for e in self.exceptions]

    def add_related_rule(self, rule_id: str) -> bool:
        """Add a related rule reference.

        Args:
            rule_id: ID of the related rule.

        Returns:
            True if added, False if already linked or self-reference.
        """
        if not rule_id or rule_id == self.id:
            return False

        if rule_id not in self.related_rule_ids:
            self.related_rule_ids.append(rule_id)
            self.touch()
            return True
        return False

    def remove_related_rule(self, rule_id: str) -> bool:
        """Remove a related rule reference.

        Args:
            rule_id: ID of the rule to unlink.

        Returns:
            True if removed.
        """
        if rule_id in self.related_rule_ids:
            self.related_rule_ids.remove(rule_id)
            self.touch()
            return True
        return False

    def is_absolute(self) -> bool:
        """Check if this rule is an absolute law (severity 90+)."""
        return self.severity >= 90

    def is_flexible(self) -> bool:
        """Check if this rule is flexible/breakable (severity < 30)."""
        return self.severity < 30

    def is_magic_rule(self) -> bool:
        """Check if this is a magic-related rule."""
        return self.category.lower() == "magic" if self.category else False

    def is_physics_rule(self) -> bool:
        """Check if this is a physics-related rule."""
        return self.category.lower() == "physics" if self.category else False

    def get_summary(self) -> str:
        """Generate a brief summary of the rule.

        Returns:
            A one-line summary of the rule and its consequence.
        """
        consequence_preview = self.consequence[:100] if self.consequence else "No consequence defined"
        if len(self.consequence) > 100:
            consequence_preview += "..."
        return f"{self.name}: {consequence_preview}"

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert WorldRule-specific data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "consequence": self.consequence,
            "exceptions": self.exceptions.copy(),
            "category": self.category,
            "severity": self.severity,
            "related_rule_ids": self.related_rule_ids.copy(),
            "metadata": self.metadata.copy(),
        }

    @classmethod
    def create_magic_rule(
        cls,
        name: str,
        description: str = "",
        consequence: str = "",
        exceptions: List[str] | None = None,
    ) -> "WorldRule":
        """Factory method for creating magic system rules.

        Args:
            name: Rule name.
            description: Rule description.
            consequence: What happens when rule is invoked.
            exceptions: Optional list of exceptions.

        Returns:
            A new magic-category WorldRule.
        """
        return cls(
            name=name,
            description=description,
            consequence=consequence,
            exceptions=exceptions or [],
            category="magic",
            severity=75,  # Magic rules are usually fairly strict
        )

    @classmethod
    def create_physics_rule(
        cls,
        name: str,
        description: str = "",
        consequence: str = "",
        exceptions: List[str] | None = None,
    ) -> "WorldRule":
        """Factory method for creating physics/natural law rules.

        Args:
            name: Rule name.
            description: Rule description.
            consequence: What happens when rule is invoked.
            exceptions: Optional list of exceptions.

        Returns:
            A new physics-category WorldRule.
        """
        return cls(
            name=name,
            description=description,
            consequence=consequence,
            exceptions=exceptions or [],
            category="physics",
            severity=100,  # Physics rules are absolute
        )

    @classmethod
    def create_social_rule(
        cls,
        name: str,
        description: str = "",
        consequence: str = "",
        exceptions: List[str] | None = None,
    ) -> "WorldRule":
        """Factory method for creating social/cultural rules.

        Args:
            name: Rule name.
            description: Rule description.
            consequence: What happens when rule is violated.
            exceptions: Optional list of exceptions.

        Returns:
            A new social-category WorldRule.
        """
        return cls(
            name=name,
            description=description,
            consequence=consequence,
            exceptions=exceptions or [],
            category="social",
            severity=40,  # Social rules are more flexible
        )
