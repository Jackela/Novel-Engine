#!/usr/bin/env python3
"""
AI Gateway Domain Services

Domain services contain complex business logic that doesn't naturally fit
within a single entity or value object. These services coordinate between
multiple domain objects and implement core business rules.
"""

from .llm_provider import ILLMProvider

__all__ = [
    "ILLMProvider"
]