"""
Character Data Manager
======================

Handles loading, parsing, and validation of character data from markdown files.
Manages character traits, attributes, and personality configurations.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class CharacterDataManager:
    """
    Manages character data loading and validation.

    Responsibilities:
    - Load character data from markdown files
    - Parse YAML frontmatter and character sheets
    - Validate character data structure
    - Provide access to character traits and attributes
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._character_data: Dict[str, Any] = {}
        self._cached_traits: Dict[str, Any] = {}

    async def load_character_data(
        self, character_directory_path: str
    ) -> Dict[str, Any]:
        """
        Load character data from directory containing character files.

        Args:
            character_directory_path: Path to character directory

        Returns:
            Dict containing all character data
        """
        try:
            character_path = Path(character_directory_path)

            if not character_path.exists():
                raise FileNotFoundError(
                    f"Character directory not found: {character_directory_path}"
                )

            # Initialize character data structure
            character_data = {
                "basic_info": {},
                "attributes": {},
                "personality": {},
                "faction_info": {},
                "equipment": {},
                "history": {},
                "goals": [],
                "relationships": {},
                "decision_weights": self._get_default_decision_weights(),
            }

            # Load all markdown files in directory
            for md_file in character_path.glob("*.md"):
                file_data = await self._load_markdown_file(md_file)
                character_data = self._merge_character_data(character_data, file_data)

            # Load any JSON/YAML configuration files
            for config_file in character_path.glob("*.{json,yaml,yml}"):
                if config_file.suffix.lower() == ".json":
                    config_data = await self._load_json_file(config_file)
                else:
                    config_data = await self._load_yaml_file(config_file)
                character_data = self._merge_character_data(character_data, config_data)

            # Validate loaded data
            if not await self.validate_character_data(character_data):
                raise ValueError("Character data validation failed")

            # Cache the loaded data
            self._character_data = character_data
            self._cache_traits()

            # Publish character update event for cache invalidation (best-effort)
            try:
                from src.caching.invalidation import invalidate_event

                char_id = (
                    character_data.get("basic_info", {}).get("name") or "character"
                )
                invalidate_event(
                    {
                        "type": "CharacterUpdated",
                        "character_id": str(char_id),
                    }
                )
            except Exception:
                # Non-fatal: event bus may be unavailable in some contexts
                pass

            self.logger.info(
                f"Character data loaded successfully from {character_directory_path}"
            )
            return character_data

        except Exception as e:
            self.logger.error(
                f"Failed to load character data from {character_directory_path}: {e}"
            )
            raise

    async def validate_character_data(self, character_data: Dict[str, Any]) -> bool:
        """
        Validate character data structure and required fields.

        Args:
            character_data: Character data to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            required_sections = ["basic_info", "attributes", "personality"]

            # Check required sections exist
            for section in required_sections:
                if section not in character_data:
                    self.logger.error(f"Missing required section: {section}")
                    return False

            # Validate basic info
            basic_info = character_data["basic_info"]
            if not basic_info.get("name"):
                self.logger.error("Character name is required")
                return False

            # Validate attributes (if present)
            attributes = character_data.get("attributes", {})
            if attributes:
                numeric_attrs = ["strength", "intelligence", "charisma", "constitution"]
                for attr in numeric_attrs:
                    if attr in attributes:
                        try:
                            float(attributes[attr])
                        except (ValueError, TypeError):
                            self.logger.warning(
                                f"Invalid numeric value for {attr}: {attributes[attr]}"
                            )

            # Validate personality traits
            personality = character_data["personality"]
            if not isinstance(personality, dict):
                self.logger.error("Personality section must be a dictionary")
                return False

            # Validate decision weights
            decision_weights = character_data.get("decision_weights", {})
            for weight_name, weight_value in decision_weights.items():
                try:
                    weight_val = float(weight_value)
                    if not -1.0 <= weight_val <= 1.0:
                        self.logger.warning(
                            f"Decision weight {weight_name} out of range [-1.0, 1.0]: {weight_val}"
                        )
                except (ValueError, TypeError):
                    self.logger.warning(
                        f"Invalid decision weight value for {weight_name}: {weight_value}"
                    )

            return True

        except Exception as e:
            self.logger.error(f"Character data validation error: {e}")
            return False

    async def get_character_trait(self, trait_name: str) -> Any:
        """
        Get specific character trait value with dot notation support.

        Args:
            trait_name: Name of trait (supports dot notation like 'personality.aggression')

        Returns:
            Trait value or None if not found
        """
        try:
            # Check cache first
            if trait_name in self._cached_traits:
                return self._cached_traits[trait_name]

            # Navigate through nested structure
            parts = trait_name.split(".")
            current = self._character_data

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None

            # Cache the result
            self._cached_traits[trait_name] = current
            return current

        except Exception as e:
            self.logger.debug(f"Error getting trait {trait_name}: {e}")
            return None

    def get_character_name(self) -> str:
        """Get character name."""
        return self._character_data.get("basic_info", {}).get("name", "Unknown")

    def get_faction(self) -> str:
        """Get character faction."""
        return self._character_data.get("faction_info", {}).get(
            "faction", "Independent"
        )

    def get_personality_traits(self) -> Dict[str, Any]:
        """Get all personality traits."""
        return self._character_data.get("personality", {})

    def get_decision_weights(self) -> Dict[str, float]:
        """Get decision making weights."""
        return self._character_data.get(
            "decision_weights", self._get_default_decision_weights()
        )

    def get_current_goals(self) -> List[Dict[str, Any]]:
        """Get character's current goals."""
        return self._character_data.get("goals", [])

    def get_relationships(self) -> Dict[str, float]:
        """Get character relationships."""
        return self._character_data.get("relationships", {})

    async def _load_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """Load data from a markdown file with YAML frontmatter."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse YAML frontmatter
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
            )
            if frontmatter_match:
                yaml_content = frontmatter_match.group(1)
                try:
                    frontmatter_data = yaml.safe_load(yaml_content)
                    if frontmatter_data:
                        return frontmatter_data
                except yaml.YAMLError as e:
                    self.logger.warning(f"Invalid YAML frontmatter in {file_path}: {e}")

            # If no frontmatter, try to extract structured data from markdown
            return await self._parse_markdown_structure(content, file_path.stem)

        except Exception as e:
            self.logger.error(f"Failed to load markdown file {file_path}: {e}")
            return {}

    async def _parse_markdown_structure(
        self, content: str, filename: str
    ) -> Dict[str, Any]:
        """Parse structured data from markdown content."""
        try:
            data = {}

            # Basic pattern matching for common character sheet sections
            sections = {
                "name": r"(?:name|character):\s*(.+)",
                "faction": r"(?:faction|allegiance):\s*(.+)",
                "personality": r"personality:\s*(.+)",
                "goals": r"(?:goals|objectives):\s*(.+)",
            }

            for section, pattern in sections.items():
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()

                    # Try to parse as structured data
                    if section in ["goals"]:
                        # Split goals by comma or newline
                        goals = [
                            g.strip() for g in re.split(r"[,\n]", value) if g.strip()
                        ]
                        data[section] = [
                            {"description": goal, "priority": 0.5} for goal in goals
                        ]
                    else:
                        data[section] = value

            # If we found name data, structure it properly
            if data:
                structured_data = {"basic_info": {}}
                if "name" in data:
                    structured_data["basic_info"]["name"] = data["name"]
                if "faction" in data:
                    structured_data["faction_info"] = {"faction": data["faction"]}
                if "personality" in data:
                    structured_data["personality"] = {
                        "description": data["personality"]
                    }
                if "goals" in data:
                    structured_data["goals"] = data["goals"]

                return structured_data

            return {}

        except Exception as e:
            self.logger.warning(
                f"Failed to parse markdown structure for {filename}: {e}"
            )
            return {}

    async def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load data from JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            return {}

    async def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load data from YAML file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Failed to load YAML file {file_path}: {e}")
            return {}

    def _merge_character_data(
        self, base_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge new character data into base data."""

        def deep_merge(base: dict, update: dict) -> dict:
            for key, value in update.items():
                if (
                    key in base
                    and isinstance(base[key], dict)
                    and isinstance(value, dict)
                ):
                    deep_merge(base[key], value)
                elif key == "goals" and isinstance(value, list):
                    # Merge goals lists
                    base_goals = base.get("goals", [])
                    for goal in value:
                        if goal not in base_goals:
                            base_goals.append(goal)
                    base["goals"] = base_goals
                else:
                    base[key] = value
            return base

        return deep_merge(base_data, new_data)

    def _cache_traits(self) -> None:
        """Cache commonly accessed traits for performance."""
        common_traits = [
            "basic_info.name",
            "faction_info.faction",
            "personality.aggression",
            "personality.loyalty",
            "personality.intelligence",
            "attributes.strength",
            "attributes.charisma",
        ]

        for trait in common_traits:
            parts = trait.split(".")
            current = self._character_data

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    current = None
                    break

            if current is not None:
                self._cached_traits[trait] = current

    def _get_default_decision_weights(self) -> Dict[str, float]:
        """Get default decision making weights."""
        return {
            "self_preservation": 0.5,
            "faction_loyalty": 0.7,
            "personal_relationships": 0.6,
            "mission_success": 0.8,
            "moral_principles": 0.4,
            "resource_acquisition": 0.3,
            "knowledge_seeking": 0.4,
            "status_advancement": 0.5,
        }

    def get_all_data(self) -> Dict[str, Any]:
        """Get all character data."""
        return self._character_data.copy()

    def clear_cache(self) -> None:
        """Clear trait cache."""
        self._cached_traits.clear()
