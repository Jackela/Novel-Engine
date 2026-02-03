"""Narrative Application Ports Package.

This package contains the port interfaces (abstract repositories and services)
that define how the application layer interacts with external infrastructure.

Why ports:
    Ports represent the boundaries of the hexagonal architecture. They define
    contracts that infrastructure adapters must fulfill, allowing the domain
    and application layers to remain independent of specific technologies.
"""

from .narrative_repository_port import INarrativeRepository

__all__ = ["INarrativeRepository"]
