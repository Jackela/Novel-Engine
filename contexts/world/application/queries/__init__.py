#!/usr/bin/env python3
"""
World Context CQRS Query Layer

This package implements the query side of CQRS for the World context,
providing high-performance read operations through optimized query objects
and handlers that operate exclusively on the read model.
"""

from .world_queries import (  # Query Objects; Query Handlers; Registry and Execution; Exceptions
    GetEntitiesByType,
    GetEntitiesByTypeQueryHandler,
    GetEntitiesInArea,
    GetEntitiesInAreaQueryHandler,
    GetWorldSlice,
    GetWorldSliceQueryHandler,
    GetWorldSummary,
    GetWorldSummaryQueryHandler,
    QueryException,
    QueryExecutionException,
    QueryHandlerRegistry,
    QueryValidationException,
    SearchWorlds,
    SearchWorldsQueryHandler,
    execute_query,
)

__all__ = [
    # Query Objects
    "GetWorldSlice",
    "GetWorldSummary",
    "GetEntitiesInArea",
    "GetEntitiesByType",
    "SearchWorlds",
    # Query Handlers
    "GetWorldSliceQueryHandler",
    "GetWorldSummaryQueryHandler",
    "GetEntitiesInAreaQueryHandler",
    "GetEntitiesByTypeQueryHandler",
    "SearchWorldsQueryHandler",
    # Registry and Execution
    "QueryHandlerRegistry",
    "execute_query",
    # Exceptions
    "QueryException",
    "QueryValidationException",
    "QueryExecutionException",
]
