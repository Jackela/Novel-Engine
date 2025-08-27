#!/usr/bin/env python3
"""
Narrative Application Layer

This package contains the application layer for the Narrative bounded context,
implementing CQRS pattern with commands, queries, handlers, and application services.

Key Components:
- Commands: Represent intent to change state
- Command Handlers: Process commands and coordinate with domain layer
- Queries: Represent requests for information
- Query Handlers: Process queries and return data
- Application Services: High-level orchestration and public interface

Architecture:
- Commands → Command Handlers → Domain Layer → Infrastructure Layer
- Queries → Query Handlers → Infrastructure Layer → Data
- Application Services orchestrate the above flows
"""

from .services.narrative_arc_application_service import NarrativeArcApplicationService

__all__ = [
    'NarrativeArcApplicationService'
]

__version__ = "1.0.0"