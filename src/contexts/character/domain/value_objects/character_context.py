"""Character context value object for scene generation.

This is a domain-level representation of character data needed for
scene generation. It exists to avoid importing API schemas from the
domain layer, maintaining hexagonal architecture boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CharacterContext:
    """Domain value object containing essential character data for generation.

    This captures the minimum character information needed for scene
    generation without depending on API layer schemas.

    Attributes:
        name: The character's name.
        tagline: A short memorable phrase associated with the character.
        bio: The character's background story and description.
        visual_prompt: Text description for generating character visuals.
        traits: List of personality traits that define the character.
    """

    name: str
    tagline: str
    bio: str
    visual_prompt: str
    traits: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate the character context after initialization."""
        if not self.name:
            raise ValueError("Character name cannot be empty")
        if not self.tagline:
            raise ValueError("Character tagline cannot be empty")

    @classmethod
    def from_dict(cls, data: dict) -> CharacterContext:
        """Create a CharacterContext from a dictionary.

        Args:
            data: Dictionary with keys: name, tagline, bio, visual_prompt, traits.

        Returns:
            A new CharacterContext instance.
        """
        traits = data.get("traits", [])
        return cls(
            name=str(data.get("name", "")),
            tagline=str(data.get("tagline", "")),
            bio=str(data.get("bio", "")),
            visual_prompt=str(data.get("visual_prompt", "")),
            traits=tuple(str(t) for t in traits) if traits else tuple(),
        )
