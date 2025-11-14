#!/usr/bin/env python3
"""
Shared Types - Backward Compatibility Interface

This module maintains backward compatibility by importing and exposing the
shared types from core types module.
"""

# Direct import from core types to avoid circular imports
from src.core.types import shared_types as _core_shared_types
from src.core.types.shared_types import *  # noqa: F401,F403

__all__ = getattr(_core_shared_types, "__all__", [])
