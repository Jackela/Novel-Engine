"""Enumeration describing knowledge access policies."""

from enum import Enum


class AccessLevel(str, Enum):
    PUBLIC = "public"
    ROLE_BASED = "role_based"
    CHARACTER_SPECIFIC = "character_specific"
