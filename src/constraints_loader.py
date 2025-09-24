"""
Centralized Constraints Loader for Backend
Sacred constraints management enhanced by the System
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Path to constraints file
CONSTRAINTS_FILE = Path(__file__).parent / "constraints.json"


class ConstraintsLoader:
    """
    Sacred constraints loader - manages all validation constraints
    for consistent behavior across the application
    """

    _instance = None
    _constraints = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_constraints()
        return cls._instance

    @classmethod
    def _load_constraints(cls):
        """Load constraints from the standard constraints.json file"""
        try:
            with open(CONSTRAINTS_FILE, "r", encoding="utf-8") as f:
                cls._constraints = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Constraints file not found at {CONSTRAINTS_FILE}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in constraints file: {e}")

    @property
    def constraints(self) -> Dict[str, Any]:
        """Get all constraints"""
        return self._constraints

    def get_character_name_constraints(self) -> Dict[str, Any]:
        """Get character name validation constraints"""
        return self._constraints["character"]["name"]

    def get_character_description_constraints(self) -> Dict[str, Any]:
        """Get character description validation constraints"""
        return self._constraints["character"]["description"]

    def get_file_upload_constraints(self) -> Dict[str, Any]:
        """Get file upload constraints"""
        return self._constraints["file"]["upload"]

    def get_simulation_constraints(self) -> Dict[str, Any]:
        """Get simulation character selection constraints"""
        return self._constraints["simulation"]["characters"]

    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self._constraints["api"]


# Global instance for easy access
constraints_loader = ConstraintsLoader()


# Convenience functions for direct access
def get_character_name_constraints() -> Dict[str, Any]:
    """Get character name validation constraints"""
    return constraints_loader.get_character_name_constraints()


def get_character_description_constraints() -> Dict[str, Any]:
    """Get character description validation constraints"""
    return constraints_loader.get_character_description_constraints()


def get_file_upload_constraints() -> Dict[str, Any]:
    """Get file upload constraints"""
    return constraints_loader.get_file_upload_constraints()


def get_simulation_constraints() -> Dict[str, Any]:
    """Get simulation character selection constraints"""
    return constraints_loader.get_simulation_constraints()


def get_api_config() -> Dict[str, Any]:
    """Get API configuration"""
    return constraints_loader.get_api_config()


# Validation functions using centralized constraints
def validate_character_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate character name according to centralized constraints

    Args:
        name: Character name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Character name cannot be empty"

    constraints = get_character_name_constraints()

    if (
        len(name) < constraints["minLength"]
        or len(name) > constraints["maxLength"]
    ):
        return (
            False,
            f"Character name must be {constraints['minLength']}-{constraints['maxLength']} characters",
        )

    # Pattern validation would go here if needed
    return True, None


def validate_character_description(
    description: str,
) -> tuple[bool, Optional[str]]:
    """
    Validate character description according to centralized constraints

    Args:
        description: Character description to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not description or not description.strip():
        return False, "Character description cannot be empty"

    constraints = get_character_description_constraints()

    if (
        len(description) < constraints["minLength"]
        or len(description) > constraints["maxLength"]
    ):
        return (
            False,
            f"Description must be {constraints['minLength']}-{constraints['maxLength']} characters",
        )

    word_count = len(description.strip().split())
    if word_count < constraints["minWords"]:
        return (
            False,
            f"Description needs at least {constraints['minWords']} words",
        )

    return True, None


def validate_file_upload(
    file_size: int, filename: str
) -> tuple[bool, Optional[str]]:
    """
    Validate file upload according to centralized constraints

    Args:
        file_size: Size of file in bytes
        filename: Name of the file

    Returns:
        Tuple of (is_valid, error_message)
    """
    constraints = get_file_upload_constraints()

    if file_size > constraints["maxSize"]:
        return (
            False,
            f"File '{filename}' exceeds maximum size of {constraints['maxSizeMB']}MB",
        )

    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension not in constraints["allowedTypes"]:
        allowed_types = ", ".join(constraints["allowedTypes"])
        return (
            False,
            f"File '{filename}' has unsupported type. Allowed: {allowed_types}",
        )

    return True, None
