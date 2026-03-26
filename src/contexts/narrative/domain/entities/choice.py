"""
Choice Entity

Represents a choice option in a scene. Choices allow users to
influence the narrative direction.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class Choice:
    """
    A choice option presented to the user in a scene.

    AI注意:
    - Choices represent branching points in the narrative
    - Each choice can have conditions and consequences
    - Choices may lead to different scenes
    """

    id: UUID = field(default_factory=uuid4)
    scene_id: str = field(default="")
    text: str = field(default="")
    next_scene_id: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    consequences: Dict[str, Any] = field(default_factory=dict)
    order: int = field(default=0)
    is_hidden: bool = field(default=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate choice invariants."""
        if not self.text or len(self.text.strip()) == 0:
            raise ValueError("Choice text cannot be empty")

        if len(self.text) > 500:
            raise ValueError("Choice text cannot exceed 500 characters")

    def is_available(self, context: Dict[str, Any]) -> bool:
        """
        Check if this choice is available given the current context.

        Args:
            context: Current narrative context

        Returns:
            True if the choice can be presented to the user
        """
        if self.is_hidden:
            return False

        # Check all conditions
        for key, value in self.conditions.items():
            if key not in context or context[key] != value:
                return False

        return True

    def apply_consequences(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply the consequences of selecting this choice.

        Args:
            context: Current narrative context

        Returns:
            Updated context with consequences applied
        """
        updated_context = context.copy()
        updated_context.update(self.consequences)
        return updated_context

    def hide(self) -> None:
        """Hide this choice from the user."""
        self.is_hidden = True

    def show(self) -> None:
        """Show this choice to the user."""
        self.is_hidden = False

    def add_condition(self, key: str, value: Any) -> None:
        """Add a condition for this choice to be available."""
        self.conditions[key] = value

    def add_consequence(self, key: str, value: Any) -> None:
        """Add a consequence when this choice is selected."""
        self.consequences[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert choice to dictionary for serialization."""
        return {
            "id": str(self.id),
            "scene_id": self.scene_id,
            "text": self.text,
            "next_scene_id": self.next_scene_id,
            "conditions": self.conditions,
            "consequences": self.consequences,
            "order": self.order,
            "is_hidden": self.is_hidden,
            "metadata": self.metadata,
        }
