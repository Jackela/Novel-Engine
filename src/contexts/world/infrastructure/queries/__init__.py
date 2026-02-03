"""World infrastructure query handlers.

Query handlers are in infrastructure layer because they depend on
ORM models (WorldSliceReadModel) for data access.
"""

from .world_queries import (
    GetEntitiesByType,
    GetEntitiesInArea,
    GetWorldSlice,
    GetWorldSummary,
    QueryException,
    QueryExecutionException,
    QueryValidationException,
    SearchWorlds,
    execute_query,
)

__all__ = [
    "GetEntitiesByType",
    "GetEntitiesInArea",
    "GetWorldSlice",
    "GetWorldSummary",
    "QueryException",
    "QueryExecutionException",
    "QueryValidationException",
    "SearchWorlds",
    "execute_query",
]
