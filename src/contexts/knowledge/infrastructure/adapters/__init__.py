"""
Knowledge Infrastructure Adapters

Adapters for integrating knowledge system with external systems.
"""

from .in_memory_prompt_repository import InMemoryPromptRepository
from .networkx_graph_store import NetworkXGraphStore

__all__ = [
    "InMemoryPromptRepository",
    "NetworkXGraphStore",
]
