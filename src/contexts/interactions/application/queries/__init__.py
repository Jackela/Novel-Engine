#!/usr/bin/env python3
"""
Queries Package for Interaction Application Layer

This package contains query objects and query handlers implementing the
read-side of CQRS for the Interaction bounded context.

Key Components:
- Query Objects: Immutable data structures representing read operations
- Query Handlers: Implementation of query processing and data retrieval
"""

from .interaction_query_handlers import InteractionQueryHandler

__all__ = ["InteractionQueryHandler"]

__version__ = "1.0.0"
