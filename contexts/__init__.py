"""
Novel Engine M1 - Domain Contexts Layer
=======================================

This package contains the domain contexts organized following Domain-Driven Design
principles. Each context represents a distinct domain boundary with specific
business logic and clear interfaces with other contexts.

Contexts:
- characters: Character domain (personas, agents, lifecycle)
- narratives: Story generation domain (plots, events, content)
- campaigns: Campaign domain (sessions, world state, persistence)
- interactions: Interaction domain (dialogue, combat, cooperation)
- orchestration: Multi-agent coordination domain
- shared: Shared kernel and cross-context utilities

Architecture Pattern: Domain-Driven Design with bounded contexts and clear domain boundaries
"""

__version__ = "1.0.0"
__author__ = "Novel Engine Development Team"
__description__ = "Domain Contexts Layer for Novel Engine M1 Architecture"
