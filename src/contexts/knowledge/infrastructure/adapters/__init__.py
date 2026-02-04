"""
Knowledge Infrastructure Adapters

Adapters for integrating knowledge system with external systems.
"""

from .in_memory_prompt_repository import InMemoryPromptRepository
from .neo4j_graph_store import Neo4jGraphStore
from .networkx_graph_store import NetworkXGraphStore

__all__ = [
    "InMemoryPromptRepository",
    "NetworkXGraphStore",
    "Neo4jGraphStore",
]
