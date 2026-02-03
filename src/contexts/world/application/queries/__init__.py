#!/usr/bin/env python3
"""
World Context Application Query Layer

Note: Query handlers have been moved to the infrastructure layer because they
depend on ORM models (WorldSliceReadModel) for data access.

Import from `src.contexts.world.infrastructure.queries` instead.

This follows the DDD pattern where Query Handlers that depend on ORM models
should reside in the infrastructure layer.
"""

# This module is intentionally empty to maintain the hexagonal architecture.
# Query handlers are in:
#   src.contexts.world.infrastructure.queries.world_queries
