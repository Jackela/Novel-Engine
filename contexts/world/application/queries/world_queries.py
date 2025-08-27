#!/usr/bin/env python3
"""
World Context CQRS Query Objects and Handlers

This module implements the query side of CQRS for the World context.
All queries operate exclusively on the read model (WorldSliceReadModel)
for optimal performance and separation from the write model.

Design Principles:
- Query objects encapsulate all query parameters
- Query handlers contain the business logic for data retrieval
- All queries use the optimized read model only
- Sub-50ms response time targets through efficient querying
- Comprehensive validation and error handling
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from core_platform.persistence.database import get_db_session
from ...infrastructure.projections.world_read_model import WorldSliceReadModel

logger = logging.getLogger(__name__)


class QueryException(Exception):
    """Base exception for query operations."""
    pass


class QueryValidationException(QueryException):
    """Raised when query parameters are invalid."""
    pass


class QueryExecutionException(QueryException):
    """Raised when query execution fails."""
    pass


# Query Objects (Command Pattern for Queries)

@dataclass
class GetWorldSlice:
    """
    Query to retrieve a spatial slice of world data.
    
    This is the primary query for fetching world state data within
    specified geographic bounds, optimized for real-time applications
    like game engines, simulations, and interactive maps.
    
    Parameters support both circular and rectangular area queries
    with optional entity type filtering for maximum flexibility.
    """
    
    world_id: str
    
    # Spatial query parameters (mutually exclusive: use either circle or bounds)
    # Circular area query
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    radius: Optional[float] = None
    
    # Rectangular bounds query
    min_x: Optional[float] = None
    max_x: Optional[float] = None
    min_y: Optional[float] = None
    max_y: Optional[float] = None
    min_z: Optional[float] = None
    max_z: Optional[float] = None
    
    # Filtering options
    entity_types: Optional[List[str]] = None
    include_environment: bool = True
    include_metadata: bool = False
    
    # Pagination for large result sets
    limit: Optional[int] = None
    offset: int = 0
    
    # Output options
    include_world_summary: bool = True
    include_spatial_index: bool = False
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.world_id:
            raise QueryValidationException("world_id is required")
        
        # Check that we have either circular or rectangular query parameters
        has_circle = all(x is not None for x in [self.center_x, self.center_y, self.radius])
        has_bounds = any(x is not None for x in [self.min_x, self.max_x, self.min_y, self.max_y])
        
        if not has_circle and not has_bounds:
            raise QueryValidationException("Either circular (center_x, center_y, radius) or rectangular bounds must be specified")
        
        if has_circle and has_bounds:
            raise QueryValidationException("Cannot specify both circular and rectangular query parameters")
        
        # Validate circular parameters
        if has_circle:
            if self.radius <= 0:
                raise QueryValidationException("radius must be positive")
        
        # Validate rectangular parameters
        if has_bounds:
            if self.min_x is not None and self.max_x is not None and self.min_x >= self.max_x:
                raise QueryValidationException("min_x must be less than max_x")
            if self.min_y is not None and self.max_y is not None and self.min_y >= self.max_y:
                raise QueryValidationException("min_y must be less than max_y")
            if self.min_z is not None and self.max_z is not None and self.min_z >= self.max_z:
                raise QueryValidationException("min_z must be less than max_z")
        
        # Validate pagination
        if self.limit is not None and self.limit <= 0:
            raise QueryValidationException("limit must be positive")
        if self.offset < 0:
            raise QueryValidationException("offset cannot be negative")
        
        # Validate entity types
        if self.entity_types is not None and not self.entity_types:
            raise QueryValidationException("entity_types cannot be empty list")
    
    def is_circular_query(self) -> bool:
        """Check if this is a circular area query."""
        return all(x is not None for x in [self.center_x, self.center_y, self.radius])
    
    def is_bounded_query(self) -> bool:
        """Check if this is a rectangular bounds query."""
        return any(x is not None for x in [self.min_x, self.max_x, self.min_y, self.max_y])


@dataclass  
class GetWorldSummary:
    """Query to retrieve summary statistics for a world."""
    
    world_id: str
    include_entity_details: bool = False
    include_spatial_bounds: bool = True
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.world_id:
            raise QueryValidationException("world_id is required")


@dataclass
class GetEntitiesInArea:
    """Query to retrieve entities within a specific geographic area."""
    
    world_id: str
    center_x: float
    center_y: float
    radius: float
    entity_types: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: int = 0
    include_distance: bool = True
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.world_id:
            raise QueryValidationException("world_id is required")
        if self.radius <= 0:
            raise QueryValidationException("radius must be positive")
        if self.limit is not None and self.limit <= 0:
            raise QueryValidationException("limit must be positive")
        if self.offset < 0:
            raise QueryValidationException("offset cannot be negative")


@dataclass
class GetEntitiesByType:
    """Query to retrieve entities filtered by type."""
    
    world_id: str
    entity_type: str
    limit: Optional[int] = None
    offset: int = 0
    include_coordinates: bool = True
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.world_id:
            raise QueryValidationException("world_id is required")
        if not self.entity_type:
            raise QueryValidationException("entity_type is required")
        if self.limit is not None and self.limit <= 0:
            raise QueryValidationException("limit must be positive")
        if self.offset < 0:
            raise QueryValidationException("offset cannot be negative")


@dataclass
class SearchWorlds:
    """Query to search worlds by name, description, or content."""
    
    search_term: str
    limit: Optional[int] = 50
    offset: int = 0
    include_entity_counts: bool = True
    status_filter: Optional[str] = None
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.search_term or not self.search_term.strip():
            raise QueryValidationException("search_term is required")
        if self.limit is not None and self.limit <= 0:
            raise QueryValidationException("limit must be positive")
        if self.offset < 0:
            raise QueryValidationException("offset cannot be negative")


# Query Handlers (Implementation of Query Logic)

class GetWorldSliceQueryHandler:
    """
    Handler for GetWorldSlice queries.
    
    This handler implements the core logic for retrieving spatial slices
    of world data using the optimized read model. It supports both
    circular and rectangular area queries with high performance.
    
    Performance targets:
    - Sub-50ms response times for typical queries
    - Efficient spatial filtering using pre-computed bounds
    - Minimal data transfer through selective field inclusion
    """
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def handle(self, query: GetWorldSlice) -> Dict[str, Any]:
        """
        Execute the GetWorldSlice query and return results.
        
        Args:
            query: The GetWorldSlice query object
            
        Returns:
            Dictionary containing the world slice data
            
        Raises:
            QueryExecutionException: If query execution fails
        """
        start_time = datetime.now()
        
        try:
            with get_db_session() as session:
                # Get the read model for this world
                read_model = session.query(WorldSliceReadModel).filter(
                    WorldSliceReadModel.world_state_id == UUID(query.world_id)
                ).first()
                
                if not read_model:
                    return {
                        'world_id': query.world_id,
                        'found': False,
                        'error': 'World not found'
                    }
                
                # Pre-filter based on spatial bounds to optimize query
                if not self._is_query_within_world_bounds(query, read_model):
                    return {
                        'world_id': query.world_id,
                        'found': True,
                        'entities': [],
                        'entity_count': 0,
                        'world_summary': read_model.get_world_summary() if query.include_world_summary else None,
                        'query_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                    }
                
                # Execute spatial query based on query type
                if query.is_circular_query():
                    entities = read_model.get_entities_in_area(
                        center_x=query.center_x,
                        center_y=query.center_y,
                        radius=query.radius,
                        entity_types=query.entity_types
                    )
                else:
                    entities = read_model.get_entities_in_bounds(
                        min_x=query.min_x or float('-inf'),
                        max_x=query.max_x or float('inf'),
                        min_y=query.min_y or float('-inf'),
                        max_y=query.max_y or float('inf'),
                        entity_types=query.entity_types
                    )
                
                # Apply pagination
                total_count = len(entities)
                if query.limit:
                    entities = entities[query.offset:query.offset + query.limit]
                elif query.offset > 0:
                    entities = entities[query.offset:]
                
                # Build response
                response = {
                    'world_id': query.world_id,
                    'found': True,
                    'entities': entities,
                    'entity_count': len(entities),
                    'total_entities': total_count,
                    'query_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                }
                
                # Add optional data
                if query.include_world_summary:
                    response['world_summary'] = read_model.get_world_summary()
                
                if query.include_environment and read_model.environment_summary:
                    response['environment'] = read_model.environment_summary
                
                if query.include_metadata and read_model.world_metadata:
                    response['metadata'] = read_model.world_metadata
                
                if query.include_spatial_index:
                    response['spatial_bounds'] = {
                        'min_x': read_model.min_x,
                        'max_x': read_model.max_x,
                        'min_y': read_model.min_y,
                        'max_y': read_model.max_y,
                        'min_z': read_model.min_z,
                        'max_z': read_model.max_z
                    }
                
                # Add query metadata
                response['query_metadata'] = {
                    'query_type': 'circular' if query.is_circular_query() else 'bounded',
                    'filtered_by_type': query.entity_types is not None,
                    'pagination_applied': query.limit is not None or query.offset > 0,
                    'world_version': read_model.world_version,
                    'projection_version': read_model.projection_version
                }
                
                self.logger.debug(f"GetWorldSlice query completed in {response['query_time_ms']:.1f}ms")
                return response
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in GetWorldSlice query: {e}")
            raise QueryExecutionException(f"Database error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in GetWorldSlice query: {e}")
            raise QueryExecutionException(f"Query execution failed: {e}")
    
    def _is_query_within_world_bounds(self, query: GetWorldSlice, read_model: WorldSliceReadModel) -> bool:
        """
        Check if the query area intersects with the world's entity bounds.
        
        This optimization allows us to quickly return empty results
        for queries that don't intersect with any entities.
        """
        # If world has no spatial bounds, assume query is valid
        if read_model.min_x is None:
            return True
        
        if query.is_circular_query():
            # Check if circle intersects with world bounds
            circle_min_x = query.center_x - query.radius
            circle_max_x = query.center_x + query.radius
            circle_min_y = query.center_y - query.radius
            circle_max_y = query.center_y + query.radius
            
            # Simple bounding box intersection check
            return not (circle_max_x < read_model.min_x or 
                       circle_min_x > read_model.max_x or
                       circle_max_y < read_model.min_y or 
                       circle_min_y > read_model.max_y)
        else:
            # Check if rectangular bounds intersect
            query_min_x = query.min_x if query.min_x is not None else float('-inf')
            query_max_x = query.max_x if query.max_x is not None else float('inf')
            query_min_y = query.min_y if query.min_y is not None else float('-inf')
            query_max_y = query.max_y if query.max_y is not None else float('inf')
            
            return not (query_max_x < read_model.min_x or 
                       query_min_x > read_model.max_x or
                       query_max_y < read_model.min_y or 
                       query_min_y > read_model.max_y)


class GetWorldSummaryQueryHandler:
    """Handler for GetWorldSummary queries."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def handle(self, query: GetWorldSummary) -> Dict[str, Any]:
        """Execute the GetWorldSummary query."""
        try:
            with get_db_session() as session:
                read_model = session.query(WorldSliceReadModel).filter(
                    WorldSliceReadModel.world_state_id == UUID(query.world_id)
                ).first()
                
                if not read_model:
                    return {
                        'world_id': query.world_id,
                        'found': False,
                        'error': 'World not found'
                    }
                
                summary = read_model.get_world_summary()
                
                # Add optional details
                if query.include_entity_details and read_model.entity_type_counts:
                    summary['entity_type_details'] = read_model.entity_type_counts
                
                if not query.include_spatial_bounds:
                    summary.pop('spatial_bounds', None)
                
                return summary
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in GetWorldSummary query: {e}")
            raise QueryExecutionException(f"Database error: {e}")


class GetEntitiesInAreaQueryHandler:
    """Handler for GetEntitiesInArea queries."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def handle(self, query: GetEntitiesInArea) -> Dict[str, Any]:
        """Execute the GetEntitiesInArea query."""
        try:
            with get_db_session() as session:
                read_model = session.query(WorldSliceReadModel).filter(
                    WorldSliceReadModel.world_state_id == UUID(query.world_id)
                ).first()
                
                if not read_model:
                    return {
                        'world_id': query.world_id,
                        'found': False,
                        'error': 'World not found'
                    }
                
                entities = read_model.get_entities_in_area(
                    center_x=query.center_x,
                    center_y=query.center_y,
                    radius=query.radius,
                    entity_types=query.entity_types
                )
                
                # Apply pagination
                total_count = len(entities)
                if query.limit:
                    entities = entities[query.offset:query.offset + query.limit]
                elif query.offset > 0:
                    entities = entities[query.offset:]
                
                return {
                    'world_id': query.world_id,
                    'found': True,
                    'entities': entities,
                    'entity_count': len(entities),
                    'total_entities': total_count,
                    'search_area': {
                        'center_x': query.center_x,
                        'center_y': query.center_y,
                        'radius': query.radius
                    }
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in GetEntitiesInArea query: {e}")
            raise QueryExecutionException(f"Database error: {e}")


class GetEntitiesByTypeQueryHandler:
    """Handler for GetEntitiesByType queries."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def handle(self, query: GetEntitiesByType) -> Dict[str, Any]:
        """Execute the GetEntitiesByType query."""
        try:
            with get_db_session() as session:
                read_model = session.query(WorldSliceReadModel).filter(
                    WorldSliceReadModel.world_state_id == UUID(query.world_id)
                ).first()
                
                if not read_model:
                    return {
                        'world_id': query.world_id,
                        'found': False,
                        'error': 'World not found'
                    }
                
                entities = read_model.get_entities_by_type(query.entity_type)
                
                # Apply pagination
                total_count = len(entities)
                if query.limit:
                    entities = entities[query.offset:query.offset + query.limit]
                elif query.offset > 0:
                    entities = entities[query.offset:]
                
                # Filter coordinates if not requested
                if not query.include_coordinates:
                    for entity in entities:
                        entity.pop('coordinates', None)
                
                return {
                    'world_id': query.world_id,
                    'found': True,
                    'entity_type': query.entity_type,
                    'entities': entities,
                    'entity_count': len(entities),
                    'total_entities': total_count
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in GetEntitiesByType query: {e}")
            raise QueryExecutionException(f"Database error: {e}")


class SearchWorldsQueryHandler:
    """Handler for SearchWorlds queries."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def handle(self, query: SearchWorlds) -> Dict[str, Any]:
        """Execute the SearchWorlds query."""
        try:
            with get_db_session() as session:
                # Build search query
                search_filter = WorldSliceReadModel.searchable_content.ilike(f"%{query.search_term}%")
                
                if query.status_filter:
                    search_filter = and_(search_filter, WorldSliceReadModel.status == query.status_filter)
                
                # Execute query with pagination
                worlds_query = session.query(WorldSliceReadModel).filter(search_filter)
                
                total_count = worlds_query.count()
                
                if query.limit:
                    worlds_query = worlds_query.limit(query.limit)
                if query.offset > 0:
                    worlds_query = worlds_query.offset(query.offset)
                
                worlds = worlds_query.all()
                
                # Format results
                results = []
                for world in worlds:
                    result = {
                        'world_id': str(world.world_state_id),
                        'name': world.world_name,
                        'description': world.world_description,
                        'status': world.status,
                        'world_time': world.world_time.isoformat() if world.world_time else None
                    }
                    
                    if query.include_entity_counts:
                        result['total_entities'] = world.total_entities
                        result['entity_types'] = world.entity_type_counts
                    
                    results.append(result)
                
                return {
                    'search_term': query.search_term,
                    'worlds': results,
                    'world_count': len(results),
                    'total_worlds': total_count,
                    'status_filter': query.status_filter
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in SearchWorlds query: {e}")
            raise QueryExecutionException(f"Database error: {e}")


# Query Handler Registry and Factory

class QueryHandlerRegistry:
    """Registry for query handlers implementing the handler pattern."""
    
    def __init__(self):
        self._handlers = {
            GetWorldSlice: GetWorldSliceQueryHandler(),
            GetWorldSummary: GetWorldSummaryQueryHandler(),
            GetEntitiesInArea: GetEntitiesInAreaQueryHandler(),
            GetEntitiesByType: GetEntitiesByTypeQueryHandler(),
            SearchWorlds: SearchWorldsQueryHandler(),
        }
    
    async def execute_query(self, query: Union[GetWorldSlice, GetWorldSummary, GetEntitiesInArea, 
                                             GetEntitiesByType, SearchWorlds]) -> Dict[str, Any]:
        """
        Execute a query using the appropriate handler.
        
        Args:
            query: The query object to execute
            
        Returns:
            Query results as a dictionary
            
        Raises:
            QueryExecutionException: If no handler found or execution fails
        """
        query_type = type(query)
        handler = self._handlers.get(query_type)
        
        if not handler:
            raise QueryExecutionException(f"No handler registered for query type: {query_type}")
        
        return await handler.handle(query)


# Global registry instance
_query_registry = QueryHandlerRegistry()


async def execute_query(query: Union[GetWorldSlice, GetWorldSummary, GetEntitiesInArea, 
                                    GetEntitiesByType, SearchWorlds]) -> Dict[str, Any]:
    """
    Convenience function to execute a query using the global registry.
    
    Args:
        query: The query object to execute
        
    Returns:
        Query results as a dictionary
    """
    return await _query_registry.execute_query(query)