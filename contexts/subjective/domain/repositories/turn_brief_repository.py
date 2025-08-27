#!/usr/bin/env python3
"""
TurnBrief Repository Interface

This module defines the repository interface for TurnBrief aggregates,
following Domain-Driven Design patterns for persistence abstraction.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..value_objects.subjective_id import SubjectiveId
from ..value_objects.perception_range import PerceptionType
from ..value_objects.knowledge_level import KnowledgeType, CertaintyLevel
from ..value_objects.awareness import AlertnessLevel


# Repository Exceptions
class TurnBriefRepositoryException(Exception):
    """Base exception for TurnBrief repository operations."""
    pass


class TurnBriefNotFoundException(TurnBriefRepositoryException):
    """Raised when a requested TurnBrief is not found."""
    pass


class ConcurrencyException(TurnBriefRepositoryException):
    """Raised when a concurrency conflict occurs during save operations."""
    pass


class RepositoryException(TurnBriefRepositoryException):
    """Raised when a general repository error occurs."""
    pass


class ITurnBriefRepository(ABC):
    """
    Repository interface for TurnBrief aggregate persistence.
    
    This interface defines the contract for persisting and retrieving
    TurnBrief aggregates without exposing implementation details.
    Following DDD principles, this keeps the domain layer independent
    from infrastructure concerns.
    """
    
    @abstractmethod
    def get_by_id(self, turn_brief_id: SubjectiveId) -> Optional['TurnBrief']:
        """
        Retrieve a TurnBrief by its unique identifier.
        
        Args:
            turn_brief_id: The unique identifier for the TurnBrief
            
        Returns:
            The TurnBrief if found, None otherwise
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def get_by_entity_id(self, entity_id: str) -> Optional['TurnBrief']:
        """
        Retrieve the current TurnBrief for a specific entity.
        
        Args:
            entity_id: The ID of the entity whose TurnBrief to retrieve
            
        Returns:
            The current TurnBrief for the entity if found, None otherwise
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def save(self, turn_brief: 'TurnBrief') -> None:
        """
        Save a TurnBrief to persistent storage.
        
        Args:
            turn_brief: The TurnBrief to save
            
        Raises:
            ConcurrencyException: If a concurrency conflict occurs
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def delete(self, turn_brief_id: SubjectiveId) -> bool:
        """
        Delete a TurnBrief from persistent storage.
        
        Args:
            turn_brief_id: The unique identifier of the TurnBrief to delete
            
        Returns:
            True if the TurnBrief was deleted, False if it didn't exist
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def find_by_world_state_version(self, world_state_version: int) -> List['TurnBrief']:
        """
        Find all TurnBriefs associated with a specific world state version.
        
        Args:
            world_state_version: The world state version to search for
            
        Returns:
            List of TurnBriefs for that world state version
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def find_by_alertness_level(self, alertness: AlertnessLevel) -> List['TurnBrief']:
        """
        Find all TurnBriefs with entities at a specific alertness level.
        
        Args:
            alertness: The alertness level to search for
            
        Returns:
            List of TurnBriefs with entities at the specified alertness level
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def find_stale_turn_briefs(self, cutoff_time: datetime) -> List['TurnBrief']:
        """
        Find TurnBriefs that haven't been updated since the cutoff time.
        
        Args:
            cutoff_time: The cutoff time for staleness
            
        Returns:
            List of stale TurnBriefs
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def find_entities_with_knowledge_about(self, subject: str, 
                                          min_certainty: CertaintyLevel = CertaintyLevel.MINIMAL) -> List[str]:
        """
        Find all entities that have knowledge about a specific subject.
        
        Args:
            subject: The subject to search for knowledge about
            min_certainty: Minimum certainty level required
            
        Returns:
            List of entity IDs that have knowledge about the subject
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def find_entities_in_perception_range_of_location(self, location_id: str, 
                                                     perception_type: Optional[PerceptionType] = None) -> List[str]:
        """
        Find all entities that can perceive a specific location.
        
        Args:
            location_id: The location to check perception for
            perception_type: Specific perception type to check (None for any)
            
        Returns:
            List of entity IDs that can perceive the location
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def find_entities_with_perception_type(self, perception_type: PerceptionType) -> List[str]:
        """
        Find all entities that have a specific type of perception.
        
        Args:
            perception_type: The type of perception to search for
            
        Returns:
            List of entity IDs with that perception type
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def get_knowledge_sharing_candidates(self, entity_id: str, knowledge_type: KnowledgeType,
                                        max_distance: Optional[float] = None) -> List[str]:
        """
        Find entities that could potentially share or receive knowledge with the given entity.
        
        Args:
            entity_id: The entity looking to share knowledge
            knowledge_type: The type of knowledge to share
            max_distance: Maximum distance for sharing (None for unlimited)
            
        Returns:
            List of entity IDs that are candidates for knowledge sharing
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def count_total_turn_briefs(self) -> int:
        """
        Count the total number of TurnBriefs in the repository.
        
        Returns:
            The total count of TurnBriefs
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def count_active_turn_briefs(self, cutoff_time: Optional[datetime] = None) -> int:
        """
        Count TurnBriefs that have been updated recently (are considered active).
        
        Args:
            cutoff_time: The cutoff time for considering a TurnBrief active
                        (defaults to 1 hour ago if None)
            
        Returns:
            The count of active TurnBriefs
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def get_entities_needing_updates(self, world_state_version: int) -> List[str]:
        """
        Get entities whose TurnBriefs need updates for a new world state version.
        
        Args:
            world_state_version: The new world state version
            
        Returns:
            List of entity IDs that need TurnBrief updates
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def batch_update_world_state_version(self, entity_ids: List[str], 
                                        new_version: int) -> int:
        """
        Update the world state version for multiple TurnBriefs in a batch operation.
        
        Args:
            entity_ids: List of entity IDs to update
            new_version: The new world state version
            
        Returns:
            The number of TurnBriefs actually updated
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass
    
    @abstractmethod
    def cleanup_expired_turn_briefs(self, expiration_time: datetime) -> int:
        """
        Remove or mark as expired TurnBriefs older than the expiration time.
        
        Args:
            expiration_time: The time before which TurnBriefs should be expired
            
        Returns:
            The number of TurnBriefs cleaned up
            
        Raises:
            RepositoryException: If a repository error occurs
        """
        pass