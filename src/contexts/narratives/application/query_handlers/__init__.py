#!/usr/bin/env python3
"""
Narrative Application Query Handlers

This package contains query handlers for narrative read operations.
Query handlers process queries and return appropriate data without modifying state.
"""

from .narrative_arc_query_handlers import NarrativeArcQueryHandler

__all__ = ["NarrativeArcQueryHandler"]

__version__ = "1.0.0"
