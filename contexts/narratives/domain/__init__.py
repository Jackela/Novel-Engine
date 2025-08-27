#!/usr/bin/env python3
"""
Narrative Domain Package

This package contains the domain layer implementation for the Narrative
bounded context, including aggregates, entities, value objects, services,
events, and repository interfaces.

Key Domain Concepts:
- NarrativeArc: Main aggregate root for story arcs and narrative structures
- CausalGraph: Service for modeling cause-and-effect relationships
- Story Events: Domain events that represent narrative occurrences
- Plot Points: Value objects representing key story moments
- Narrative Flow: Services managing story progression and pacing

Domain Rules:
- Narrative arcs must maintain causal consistency
- Story events must be temporally ordered
- Plot points must advance the overall narrative
- Character actions must have narrative consequences
"""

__version__ = "1.0.0"