"""Enumeration describing the supported knowledge categories."""

from enum import Enum


class KnowledgeType(str, Enum):
    PROFILE = "profile"
    OBJECTIVE = "objective"
    MEMORY = "memory"
    LORE = "lore"
    RULES = "rules"
