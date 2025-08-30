#!/usr/bin/env python3
"""
Character Context Manager
========================

Manages character context loading, parsing, and maintenance.
Extracted from PersonaAgent for better separation of concerns.

Part of Wave 6.2 PersonaAgent Decomposition Strategy.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.persona_core import PersonaCore

logger = logging.getLogger(__name__)


class CharacterContextManager:
    """
    Manages character data loading and context management.

    Responsibilities:
    - Character sheet loading and parsing
    - Context extraction and processing
    - Character data validation and normalization
    - Personality trait extraction and quantification
    """

    def __init__(self, core: "PersonaCore"):
        """
        Initialize context manager.

        Args:
            core: PersonaCore instance for file operations
        """
        self.core = core
        self.logger = logging.getLogger(f"{__name__}.{core.agent_id}")

    def load_character_context(self) -> None:
        """
        Load and parse character context from character sheet.

        Loads character data from markdown character sheet and populates
        the character_data dictionary with structured information.
        """
        try:
            character_sheet_path = self.core.identity.character_sheet_path

            if not Path(character_sheet_path).exists():
                self.logger.error(f"Character sheet not found: {character_sheet_path}")
                return

            # Read character sheet content
            content = self.core._read_cached_file(character_sheet_path)
            if not content:
                self.logger.error(
                    f"Failed to read character sheet: {character_sheet_path}"
                )
                return

            # Parse character sheet
            parsed_data = self._parse_character_sheet_content(content)

            # Update core character data
            self.core.character_data = parsed_data

            # Extract core identity information
            self._extract_core_identity()

            self.logger.info(
                f"Character context loaded successfully for {self.core.identity.character_name}"
            )

        except Exception as e:
            self.logger.error(f"Failed to load character context: {e}")

    def _parse_character_sheet_content(self, content: str) -> Dict[str, Any]:
        """
        Parse character sheet markdown content into structured data.

        Args:
            content: Raw character sheet content

        Returns:
            Dict: Structured character data
        """
        parsed_data = {}

        # Extract major sections
        sections = {
            "identity": self._extract_section(content, "identity"),
            "psychological": self._extract_section(content, "psychological"),
            "behavioral": self._extract_section(content, "behavioral"),
            "knowledge": self._extract_section(content, "knowledge"),
            "social": self._extract_section(content, "social"),
            "capabilities": self._extract_section(content, "capabilities"),
        }

        # Parse each section
        for section_name, section_content in sections.items():
            if section_content:
                parser_method = getattr(self, f"_parse_{section_name}_section", None)
                if parser_method:
                    try:
                        parsed_data[section_name] = parser_method(section_content)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse {section_name} section: {e}"
                        )
                        parsed_data[section_name] = {}
                else:
                    # Fallback to simple parsing
                    parsed_data[section_name] = self._parse_simple_field_format(
                        section_content
                    )

        return parsed_data

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """
        Extract a section from character sheet content.

        Args:
            content: Full character sheet content
            section_name: Name of section to extract

        Returns:
            Optional[str]: Section content if found
        """
        # Try various section header patterns
        patterns = [
            rf"#{1,3}\s*{section_name}.*?\n(.*?)(?=\n#{1,3}\s*\w+|\Z)",
            rf"## {section_name}.*?\n(.*?)(?=\n## \w+|\Z)",
            rf"# {section_name}.*?\n(.*?)(?=\n# \w+|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        return None

    def _parse_identity_section(self, section_content: str) -> Dict[str, Any]:
        """Parse identity section from character sheet."""
        identity_data = {}

        # Extract basic identity fields
        fields = ["name", "faction", "rank", "age", "gender", "homeworld", "profession"]

        for field in fields:
            pattern = rf"(?:^|\n)\s*\*?\s*{field}:?\s*(.+?)(?=\n|$)"
            match = re.search(pattern, section_content, re.IGNORECASE | re.MULTILINE)
            if match:
                identity_data[field] = match.group(1).strip()

        # Extract backstory if present
        backstory_pattern = (
            r"(?:^|\n)\s*(?:backstory|background):\s*(.*?)(?=\n\s*\*|\Z)"
        )
        backstory_match = re.search(
            backstory_pattern, section_content, re.IGNORECASE | re.DOTALL
        )
        if backstory_match:
            identity_data["backstory"] = backstory_match.group(1).strip()

        return identity_data

    def _parse_psychological_section(self, section_content: str) -> Dict[str, Any]:
        """Parse psychological profile section."""
        psychological_data = {}

        # Extract personality traits with weights
        traits = self._extract_weighted_items(section_content)
        psychological_data["personality_traits"] = traits

        # Extract motivations and fears
        motivations = self._extract_bullet_points(section_content)
        psychological_data.update(motivations)

        return psychological_data

    def _parse_behavioral_section(self, section_content: str) -> Dict[str, Any]:
        """Parse behavioral patterns section."""
        behavioral_data = {}

        # Extract decision weights
        weights = self._extract_weighted_items(section_content)
        behavioral_data["decision_weights"] = weights

        # Extract behavioral patterns
        patterns = self._extract_bullet_points(section_content)
        behavioral_data.update(patterns)

        return behavioral_data

    def _extract_bullet_points(self, content: str) -> Dict[str, str]:
        """Extract bullet points from content."""
        bullet_points = {}

        # Find all bullet point patterns
        lines = content.split("\n")
        current_category = None

        for line in lines:
            line = line.strip()

            # Check for category headers
            if (
                line
                and line.endswith(":")
                and not line.startswith("*")
                and not line.startswith("-")
            ):
                current_category = line[:-1].lower().replace(" ", "_")
                bullet_points[current_category] = []
                continue

            # Check for bullet points
            if line.startswith("* ") or line.startswith("- "):
                bullet_text = line[2:].strip()
                if current_category and isinstance(
                    bullet_points.get(current_category), list
                ):
                    bullet_points[current_category].append(bullet_text)
                else:
                    # Store as general bullet point
                    if "general_points" not in bullet_points:
                        bullet_points["general_points"] = []
                    bullet_points["general_points"].append(bullet_text)

        return bullet_points

    def _extract_weighted_items(self, content: str) -> Dict[str, float]:
        """Extract weighted items (traits with numerical values)."""
        weighted_items = {}

        # Pattern for "Item: value" or "Item (value)" formats
        patterns = [
            r"(?:^|\n)\s*\*?\s*([^:\n]+?):\s*(\d*\.?\d+)",  # "Trait: 0.8"
            r"(?:^|\n)\s*\*?\s*([^(\n]+?)\s*\((\d*\.?\d+)\)",  # "Trait (0.8)"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            for trait, value_str in matches:
                trait_clean = trait.strip().lower().replace(" ", "_")
                try:
                    value = float(value_str)
                    weighted_items[trait_clean] = value
                except ValueError:
                    continue

        return weighted_items

    def _parse_simple_field_format(self, content: str) -> Dict[str, Any]:
        """Parse simple field: value format content."""
        parsed_data = {}

        # Extract field: value pairs
        field_pattern = r"(?:^|\n)\s*\*?\s*([^:\n]+):\s*([^\n]+)"
        matches = re.findall(field_pattern, content, re.MULTILINE)

        for field, value in matches:
            field_clean = field.strip().lower().replace(" ", "_")
            value_clean = value.strip()

            # Try to convert to number if possible
            try:
                if "." in value_clean:
                    parsed_data[field_clean] = float(value_clean)
                else:
                    parsed_data[field_clean] = int(value_clean)
            except ValueError:
                parsed_data[field_clean] = value_clean

        return parsed_data

    def _extract_core_identity(self) -> None:
        """Extract core identity information to PersonaCore."""
        try:
            identity_data = self.core.character_data.get("identity", {})

            # Update PersonaCore identity
            if "name" in identity_data:
                self.core.identity.character_name = identity_data["name"]

            if "faction" in identity_data:
                self.core.identity.primary_faction = identity_data["faction"]

            if "backstory" in identity_data:
                self.core.identity.backstory = identity_data["backstory"]

            self.logger.debug(
                f"Core identity extracted: {self.core.identity.character_name} ({self.core.identity.primary_faction})"
            )

        except Exception as e:
            self.logger.error(f"Failed to extract core identity: {e}")

    def get_character_summary(self) -> Dict[str, Any]:
        """Get summary of loaded character data."""
        return {
            "character_name": self.core.identity.character_name,
            "primary_faction": self.core.identity.primary_faction,
            "sections_loaded": list(self.core.character_data.keys()),
            "total_fields": sum(
                len(section) if isinstance(section, dict) else 1
                for section in self.core.character_data.values()
            ),
            "has_personality_traits": "psychological" in self.core.character_data,
            "has_decision_weights": "behavioral" in self.core.character_data,
        }
