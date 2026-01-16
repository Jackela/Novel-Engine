#!/usr/bin/env python3
"""
Narrative Application Command Handlers

This package contains command handlers for narrative operations.
Command handlers process commands and coordinate between application and domain layers.
"""

from .narrative_arc_command_handlers import NarrativeArcCommandHandler

__all__ = ["NarrativeArcCommandHandler"]

__version__ = "1.0.0"
