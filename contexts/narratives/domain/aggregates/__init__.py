#!/usr/bin/env python3
"""
Narrative Domain Aggregates Package

This package contains aggregate root entities for the Narrative bounded context.
Aggregates enforce business rules and maintain consistency boundaries.

Key Aggregates:
- NarrativeArc: Main aggregate root for story arcs and narrative structures
"""

from .narrative_arc import NarrativeArc

__all__ = [
    'NarrativeArc'
]

__version__ = "1.0.0"