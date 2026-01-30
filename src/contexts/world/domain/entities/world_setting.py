#!/usr/bin/env python3
"""
WorldSetting Domain Entity

Represents the foundational setting/configuration for a world including
genre, themes, era, and core narrative elements.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from .entity import Entity


class Genre(Enum):
    """Genre classifications for world settings."""

    FANTASY = "fantasy"
    SCIENCE_FICTION = "science_fiction"
    HORROR = "horror"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    HISTORICAL = "historical"
    CONTEMPORARY = "contemporary"
    POST_APOCALYPTIC = "post_apocalyptic"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    URBAN_FANTASY = "urban_fantasy"
    EPIC_FANTASY = "epic_fantasy"
    SPACE_OPERA = "space_opera"
    MILITARY = "military"
    SUPERNATURAL = "supernatural"


class Era(Enum):
    """Historical/temporal era for the world setting."""

    PREHISTORIC = "prehistoric"
    ANCIENT = "ancient"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    NEAR_FUTURE = "near_future"
    FAR_FUTURE = "far_future"
    TIMELESS = "timeless"


class ToneType(Enum):
    """Narrative tone for the world."""

    DARK = "dark"
    LIGHT = "light"
    GRITTY = "gritty"
    HOPEFUL = "hopeful"
    SATIRICAL = "satirical"
    HEROIC = "heroic"
    TRAGIC = "tragic"
    COMEDIC = "comedic"
    EPIC = "epic"
    INTIMATE = "intimate"


@dataclass
class WorldSetting(Entity):
    """
    WorldSetting Entity

    Defines the foundational characteristics of a world, including its genre,
    themes, era, and core narrative elements. This entity contains domain logic
    for validating setting consistency and theme compatibility.

    Attributes:
        name: The name of the world/setting
        description: Detailed description of the world
        genre: Primary genre classification
        secondary_genres: Additional genre elements
        era: Temporal era of the setting
        themes: Core thematic elements
        tone: Overall narrative tone
        magic_level: Level of magic/supernatural elements (0-10)
        technology_level: Level of technology (0-10)
        world_rules: Key rules/constraints of the world
        cultural_influences: Real-world cultural inspirations
    """

    name: str = ""
    description: str = ""
    genre: Genre = Genre.FANTASY
    secondary_genres: List[Genre] = field(default_factory=list)
    era: Era = Era.MEDIEVAL
    themes: List[str] = field(default_factory=list)
    tone: ToneType = ToneType.HEROIC
    magic_level: int = 5
    technology_level: int = 3
    world_rules: List[str] = field(default_factory=list)
    cultural_influences: List[str] = field(default_factory=list)

    def _validate_business_rules(self) -> List[str]:
        """Validate WorldSetting-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("World name cannot be empty")

        if len(self.name) > 200:
            errors.append("World name cannot exceed 200 characters")

        if self.magic_level < 0 or self.magic_level > 10:
            errors.append("Magic level must be between 0 and 10")

        if self.technology_level < 0 or self.technology_level > 10:
            errors.append("Technology level must be between 0 and 10")

        if len(self.themes) > 10:
            errors.append("Cannot have more than 10 themes")

        if len(self.secondary_genres) > 5:
            errors.append("Cannot have more than 5 secondary genres")

        # Validate genre/era compatibility
        errors.extend(self._validate_genre_era_compatibility())

        # Validate theme consistency
        errors.extend(self._validate_theme_consistency())

        return errors

    def _validate_genre_era_compatibility(self) -> List[str]:
        """Validate that genre and era are compatible."""
        errors = []

        # Science fiction requires appropriate era
        sci_fi_genres = {
            Genre.SCIENCE_FICTION,
            Genre.CYBERPUNK,
            Genre.SPACE_OPERA,
        }
        sci_fi_eras = {Era.MODERN, Era.NEAR_FUTURE, Era.FAR_FUTURE}

        if self.genre in sci_fi_genres and self.era not in sci_fi_eras:
            errors.append(
                f"{self.genre.value} genre typically requires "
                f"a modern or future era, not {self.era.value}"
            )

        # Historical genre requires appropriate era
        if self.genre == Genre.HISTORICAL and self.era in {
            Era.NEAR_FUTURE,
            Era.FAR_FUTURE,
        }:
            errors.append("Historical genre cannot have a future era")

        # Steampunk has specific era requirements
        if self.genre == Genre.STEAMPUNK and self.era not in {
            Era.INDUSTRIAL,
            Era.TIMELESS,
        }:
            errors.append("Steampunk genre typically requires industrial era")

        return errors

    def _validate_theme_consistency(self) -> List[str]:
        """Validate theme consistency with tone."""
        errors = []

        dark_themes = {"death", "corruption", "despair", "betrayal", "tragedy"}
        light_themes = {"hope", "redemption", "love", "friendship", "triumph"}

        themes_lower = {t.lower() for t in self.themes}

        if self.tone == ToneType.DARK and themes_lower & light_themes:
            # Warning but not error - dark worlds can have hope
            pass

        if self.tone == ToneType.LIGHT and len(themes_lower & dark_themes) > 2:
            errors.append(
                "Light tone setting has too many dark themes - "
                "consider adjusting tone or themes"
            )

        return errors

    def add_theme(self, theme: str) -> None:
        """
        Add a theme to the world setting.

        Args:
            theme: The theme to add

        Raises:
            ValueError: If theme limit exceeded or theme is invalid
        """
        if not theme or not theme.strip():
            raise ValueError("Theme cannot be empty")

        theme = theme.strip().lower()

        if theme in self.themes:
            return  # Theme already exists

        if len(self.themes) >= 10:
            raise ValueError("Cannot have more than 10 themes")

        self.themes.append(theme)
        self.touch()

    def remove_theme(self, theme: str) -> bool:
        """
        Remove a theme from the world setting.

        Args:
            theme: The theme to remove

        Returns:
            True if theme was removed, False if not found
        """
        theme = theme.strip().lower()
        if theme in self.themes:
            self.themes.remove(theme)
            self.touch()
            return True
        return False

    def add_secondary_genre(self, genre: Genre) -> None:
        """
        Add a secondary genre to the world setting.

        Args:
            genre: The genre to add

        Raises:
            ValueError: If genre limit exceeded or genre conflicts
        """
        if genre == self.genre:
            raise ValueError("Secondary genre cannot be same as primary genre")

        if genre in self.secondary_genres:
            return  # Genre already exists

        if len(self.secondary_genres) >= 5:
            raise ValueError("Cannot have more than 5 secondary genres")

        self.secondary_genres.append(genre)
        self.touch()
        self.validate()

    def update_magic_level(self, level: int) -> None:
        """
        Update the magic level of the world.

        Args:
            level: New magic level (0-10)

        Raises:
            ValueError: If level is out of range
        """
        if level < 0 or level > 10:
            raise ValueError("Magic level must be between 0 and 10")

        self.magic_level = level
        self.touch()

    def update_technology_level(self, level: int) -> None:
        """
        Update the technology level of the world.

        Args:
            level: New technology level (0-10)

        Raises:
            ValueError: If level is out of range
        """
        if level < 0 or level > 10:
            raise ValueError("Technology level must be between 0 and 10")

        self.technology_level = level
        self.touch()

    def is_high_magic(self) -> bool:
        """Check if this is a high-magic world."""
        return self.magic_level >= 7

    def is_high_tech(self) -> bool:
        """Check if this is a high-technology world."""
        return self.technology_level >= 7

    def is_low_fantasy(self) -> bool:
        """Check if this is a low-fantasy setting."""
        return self.genre == Genre.FANTASY and self.magic_level <= 3

    def get_setting_profile(self) -> str:
        """
        Generate a brief profile description of the setting.

        Returns:
            A string describing the world setting profile
        """
        magic_desc = "high-magic" if self.is_high_magic() else (
            "low-magic" if self.magic_level <= 3 else "moderate-magic"
        )
        tech_desc = "high-tech" if self.is_high_tech() else (
            "low-tech" if self.technology_level <= 3 else "moderate-tech"
        )

        themes_str = ", ".join(self.themes[:3]) if self.themes else "unspecified"

        return (
            f"{self.tone.value.title()} {self.era.value} {self.genre.value} "
            f"({magic_desc}, {tech_desc}) exploring {themes_str}"
        )

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert WorldSetting-specific data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "genre": self.genre.value,
            "secondary_genres": [g.value for g in self.secondary_genres],
            "era": self.era.value,
            "themes": self.themes,
            "tone": self.tone.value,
            "magic_level": self.magic_level,
            "technology_level": self.technology_level,
            "world_rules": self.world_rules,
            "cultural_influences": self.cultural_influences,
        }

    @classmethod
    def create_fantasy_world(
        cls,
        name: str,
        description: str = "",
        magic_level: int = 7,
        themes: List[str] | None = None,
    ) -> "WorldSetting":
        """Factory method to create a standard fantasy world setting."""
        return cls(
            name=name,
            description=description,
            genre=Genre.FANTASY,
            era=Era.MEDIEVAL,
            themes=themes or ["adventure", "magic", "heroism"],
            tone=ToneType.HEROIC,
            magic_level=magic_level,
            technology_level=2,
        )

    @classmethod
    def create_scifi_world(
        cls,
        name: str,
        description: str = "",
        technology_level: int = 8,
        themes: List[str] | None = None,
    ) -> "WorldSetting":
        """Factory method to create a science fiction world setting."""
        return cls(
            name=name,
            description=description,
            genre=Genre.SCIENCE_FICTION,
            era=Era.FAR_FUTURE,
            themes=themes or ["exploration", "technology", "humanity"],
            tone=ToneType.EPIC,
            magic_level=0,
            technology_level=technology_level,
        )
