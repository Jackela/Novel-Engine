#!/usr/bin/env python3
"""
World State Repository Interface

This module defines the abstract repository interface for World State aggregates.
This follows Domain-Driven Design principles by keeping the domain layer
independent of infrastructure concerns while defining the contract for persistence.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime

from ..aggregates.world_state import WorldState
from ..value_objects.coordinates import Coordinates


class IWorldStateRepository(ABC):
    """
    Abstract repository interface for WorldState aggregates.
    
    This interface defines the contract for persisting and retrieving WorldState
    aggregates without coupling the domain layer to specific persistence
    implementations. Infrastructure layer implementations will provide the
    concrete implementation details.
    
    Following DDD principles:
    - Domain layer defines the interface
    - Infrastructure layer provides implementation
    - Repository handles aggregate roots only
    - Maintains aggregate boundaries and consistency
    """
    
    # Basic CRUD Operations
    
    @abstractmethod
    async def save(self, world_state: WorldState) -> WorldState:
        """
        Save a WorldState aggregate to persistent storage.
        
        This method handles both create and update operations based on
        whether the aggregate already exists in storage.
        
        Args:
            world_state: The WorldState aggregate to save
            
        Returns:
            The saved WorldState aggregate (may include generated IDs)
            
        Raises:
            RepositoryException: If save operation fails
            ConcurrencyException: If version conflict occurs
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, world_state_id: str) -> Optional[WorldState]:
        """
        Retrieve a WorldState aggregate by its unique identifier.
        
        Args:
            world_state_id: Unique identifier for the world state
            
        Returns:
            WorldState aggregate if found, None otherwise
            
        Raises:
            RepositoryException: If retrieval operation fails
        """
        pass
    
    @abstractmethod
    async def get_by_id_or_raise(self, world_state_id: str) -> WorldState:
        """
        Retrieve a WorldState aggregate by ID or raise exception if not found.
        
        Args:
            world_state_id: Unique identifier for the world state
            
        Returns:
            WorldState aggregate
            
        Raises:
            EntityNotFoundException: If world state not found
            RepositoryException: If retrieval operation fails
        """
        pass
    
    @abstractmethod
    async def delete(self, world_state_id: str) -> bool:
        """
        Delete a WorldState aggregate from persistent storage.
        
        Args:
            world_state_id: Unique identifier for the world state
            
        Returns:
            True if deletion was successful, False if not found
            
        Raises:
            RepositoryException: If deletion operation fails
        """
        pass
    
    @abstractmethod
    async def exists(self, world_state_id: str) -> bool:
        """
        Check if a WorldState aggregate exists in storage.
        
        Args:
            world_state_id: Unique identifier for the world state
            
        Returns:
            True if world state exists, False otherwise
            
        Raises:
            RepositoryException: If existence check fails
        """
        pass
    
    # Query Operations
    
    @abstractmethod
    async def get_all(self, offset: int = 0, limit: int = 100) -> List[WorldState]:
        """
        Retrieve all WorldState aggregates with pagination.
        
        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of WorldState aggregates
            
        Raises:
            RepositoryException: If query operation fails
        """
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[WorldState]:
        """
        Find a WorldState aggregate by its name.
        
        Args:
            name: Name of the world state to find
            
        Returns:
            WorldState aggregate if found, None otherwise
            
        Raises:
            RepositoryException: If query operation fails
        """
        pass
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any], 
                              offset: int = 0, limit: int = 100) -> List[WorldState]:
        """
        Find WorldState aggregates matching specific criteria.
        
        Args:
            criteria: Dictionary of search criteria
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching WorldState aggregates
            
        Raises:
            RepositoryException: If query operation fails
        """
        pass
    
    @abstractmethod
    async def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        Count WorldState aggregates matching optional criteria.
        
        Args:
            criteria: Optional dictionary of search criteria
            
        Returns:
            Number of matching world states
            
        Raises:
            RepositoryException: If count operation fails
        """
        pass
    
    # Entity-specific Operations
    
    @abstractmethod
    async def find_entities_by_type(self, world_state_id: str, entity_type: str,
                                   offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find entities within a world state by their type.
        
        Args:
            world_state_id: ID of the world state
            entity_type: Type of entities to find
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of entity data dictionaries
            
        Raises:
            RepositoryException: If query operation fails
        """
        pass
    
    @abstractmethod
    async def find_entities_in_area(self, world_state_id: str, 
                                   center: Coordinates, radius: float,
                                   entity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find entities within a specific geographical area.
        
        Args:
            world_state_id: ID of the world state
            center: Center coordinates for the search area
            radius: Search radius from the center point
            entity_types: Optional list of entity types to filter
            
        Returns:
            List of entity data dictionaries within the area
            
        Raises:
            RepositoryException: If spatial query operation fails
        """
        pass
    
    @abstractmethod
    async def find_entities_by_coordinates(self, world_state_id: str, 
                                          coordinates: Coordinates,
                                          tolerance: float = 0.0) -> List[Dict[str, Any]]:
        """
        Find entities at specific coordinates (with optional tolerance).
        
        Args:
            world_state_id: ID of the world state
            coordinates: Exact coordinates to search
            tolerance: Tolerance distance for coordinate matching
            
        Returns:
            List of entity data dictionaries at the coordinates
            
        Raises:
            RepositoryException: If coordinate query operation fails
        """
        pass
    
    # Versioning and History Operations
    
    @abstractmethod
    async def get_version(self, world_state_id: str, version: int) -> Optional[WorldState]:
        """
        Retrieve a specific version of a WorldState aggregate.
        
        Args:
            world_state_id: ID of the world state
            version: Version number to retrieve
            
        Returns:
            WorldState aggregate at the specified version, None if not found
            
        Raises:
            RepositoryException: If version query fails
        """
        pass
    
    @abstractmethod
    async def get_version_history(self, world_state_id: str, 
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get version history for a WorldState aggregate.
        
        Args:
            world_state_id: ID of the world state
            limit: Maximum number of versions to return
            
        Returns:
            List of version metadata dictionaries
            
        Raises:
            RepositoryException: If version history query fails
        """
        pass
    
    @abstractmethod
    async def rollback_to_version(self, world_state_id: str, version: int) -> WorldState:
        """
        Rollback a WorldState aggregate to a previous version.
        
        Args:
            world_state_id: ID of the world state
            version: Version number to rollback to
            
        Returns:
            WorldState aggregate after rollback
            
        Raises:
            EntityNotFoundException: If world state or version not found
            RepositoryException: If rollback operation fails
        """
        pass
    
    # Snapshot and Backup Operations
    
    @abstractmethod
    async def create_snapshot(self, world_state_id: str, 
                             snapshot_name: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a named snapshot of a WorldState aggregate.
        
        Args:
            world_state_id: ID of the world state
            snapshot_name: Name for the snapshot
            metadata: Optional metadata for the snapshot
            
        Returns:
            Snapshot ID
            
        Raises:
            RepositoryException: If snapshot creation fails
        """
        pass
    
    @abstractmethod
    async def restore_from_snapshot(self, world_state_id: str, 
                                   snapshot_id: str) -> WorldState:
        """
        Restore a WorldState aggregate from a snapshot.
        
        Args:
            world_state_id: ID of the world state
            snapshot_id: ID of the snapshot to restore from
            
        Returns:
            Restored WorldState aggregate
            
        Raises:
            EntityNotFoundException: If world state or snapshot not found
            RepositoryException: If restore operation fails
        """
        pass
    
    @abstractmethod
    async def list_snapshots(self, world_state_id: str) -> List[Dict[str, Any]]:
        """
        List all snapshots for a WorldState aggregate.
        
        Args:
            world_state_id: ID of the world state
            
        Returns:
            List of snapshot metadata dictionaries
            
        Raises:
            RepositoryException: If snapshot listing fails
        """
        pass
    
    @abstractmethod
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a WorldState snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to delete
            
        Returns:
            True if deletion was successful, False if not found
            
        Raises:
            RepositoryException: If deletion operation fails
        """
        pass
    
    # Batch Operations
    
    @abstractmethod
    async def save_batch(self, world_states: List[WorldState]) -> List[WorldState]:
        """
        Save multiple WorldState aggregates in a single transaction.
        
        Args:
            world_states: List of WorldState aggregates to save
            
        Returns:
            List of saved WorldState aggregates
            
        Raises:
            RepositoryException: If batch save operation fails
        """
        pass
    
    @abstractmethod
    async def delete_batch(self, world_state_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple WorldState aggregates in a single transaction.
        
        Args:
            world_state_ids: List of world state IDs to delete
            
        Returns:
            Dictionary mapping world state ID to deletion success status
            
        Raises:
            RepositoryException: If batch delete operation fails
        """
        pass
    
    # Performance and Optimization
    
    @abstractmethod
    async def optimize_storage(self, world_state_id: str) -> Dict[str, Any]:
        """
        Optimize storage for a WorldState aggregate.
        
        This might include operations like compacting version history,
        optimizing spatial indexes, or cleaning up orphaned data.
        
        Args:
            world_state_id: ID of the world state to optimize
            
        Returns:
            Dictionary with optimization results and statistics
            
        Raises:
            RepositoryException: If optimization fails
        """
        pass
    
    @abstractmethod
    async def get_statistics(self, world_state_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics for world states.
        
        Args:
            world_state_id: Optional specific world state ID, or None for global stats
            
        Returns:
            Dictionary with storage statistics
            
        Raises:
            RepositoryException: If statistics gathering fails
        """
        pass
    
    # Event Sourcing Support
    
    @abstractmethod
    async def get_events_since(self, world_state_id: str, since_version: int) -> List[Dict[str, Any]]:
        """
        Get domain events for a world state since a specific version.
        
        Args:
            world_state_id: ID of the world state
            since_version: Version number to start from
            
        Returns:
            List of domain event data
            
        Raises:
            RepositoryException: If event query fails
        """
        pass
    
    @abstractmethod
    async def replay_events(self, world_state_id: str, 
                           to_version: Optional[int] = None) -> WorldState:
        """
        Reconstruct a WorldState aggregate by replaying domain events.
        
        Args:
            world_state_id: ID of the world state
            to_version: Optional version to replay to (latest if None)
            
        Returns:
            Reconstructed WorldState aggregate
            
        Raises:
            RepositoryException: If event replay fails
        """
        pass


class RepositoryException(Exception):
    """Base exception for repository operations."""
    pass


class EntityNotFoundException(RepositoryException):
    """Raised when a requested entity is not found."""
    pass


class ConcurrencyException(RepositoryException):
    """Raised when a concurrency conflict occurs during save operations."""
    
    def __init__(self, message: str, expected_version: int, actual_version: int):
        super().__init__(message)
        self.expected_version = expected_version
        self.actual_version = actual_version