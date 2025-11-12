#!/usr/bin/env python3
"""
Narrative Infrastructure Layer

This package contains the infrastructure layer for the Narrative bounded context,
providing concrete implementations for data persistence and external integrations.

Key Components:
- Repositories: Data persistence implementations using SQLAlchemy ORM
- Database Models: SQLAlchemy entity models for database mapping
- External Services: Integration with external systems and APIs

Architecture:
- Repository Interface (Domain) ← Repository Implementation (Infrastructure)
- Domain Aggregates ↔ SQLAlchemy Entities (via mapping)
- Database persistence with transaction management
"""

from .repositories.narrative_arc_repository import (
    INarrativeArcRepository,
    NarrativeArcRepository,
)

__all__ = ["NarrativeArcRepository", "INarrativeArcRepository"]

__version__ = "1.0.0"
