"""Neo4j Graph Store Adapter (Backward Compatibility Shim).

.. deprecated::
    Use modular imports from `knowledge.infrastructure.adapters.neo4j` instead.
    This module is kept for backward compatibility.

"""

import warnings

# Emit deprecation warning
warnings.warn(
    "Importing from 'knowledge.infrastructure.adapters.neo4j_graph_store' is deprecated. "
    "Use modular imports from 'knowledge.infrastructure.adapters.neo4j' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all public symbols from the new module
from .neo4j import (
    ConnectionManager,
    EntityRepository,
    Neo4jGraphStore,
    QueryBuilder,
    RelationshipRepository,
)

__all__ = [
    "Neo4jGraphStore",
    "ConnectionManager",
    "QueryBuilder",
    "EntityRepository",
    "RelationshipRepository",
]
