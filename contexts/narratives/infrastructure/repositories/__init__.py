#!/usr/bin/env python3
"""
Narrative Infrastructure Repositories

This package contains repository implementations for the Narrative bounded context,
providing concrete data persistence using SQLAlchemy ORM.
"""

from .narrative_arc_repository import NarrativeArcRepository, INarrativeArcRepository

__all__ = [
    'NarrativeArcRepository',
    'INarrativeArcRepository'
]

__version__ = "1.0.0"