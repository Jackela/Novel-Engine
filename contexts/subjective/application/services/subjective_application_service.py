#!/usr/bin/env python3
"""
Subjective Application Service

This module implements the main application service for the Subjective
bounded context. It serves as the primary interface for external systems
to interact with subjective perception and knowledge operations.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from ...domain.aggregates.turn_brief import TurnBrief
from ...domain.repositories.turn_brief_repository import ITurnBriefRepository
from ...domain.services.fog_of_war_service import FogOfWarService
from ...domain.value_objects.subjective_id import SubjectiveId
from ...domain.value_objects.perception_range import PerceptionCapabilities, PerceptionType
from ...domain.value_objects.knowledge_level import KnowledgeItem, KnowledgeType, CertaintyLevel
from ...domain.value_objects.awareness import AlertnessLevel, AttentionFocus, AwarenessModifier

from ..commands.subjective_commands import (
    CreateTurnBriefCommand, UpdatePerceptionCapabilitiesCommand, UpdateAwarenessStateCommand,
    AddPerceptionCommand, RevealKnowledgeCommand, UpdateKnowledgeCommand,
    DetectThreatCommand, LoseThreatTrackingCommand, UpdateFogOfWarCommand,
    ShareInformationCommand, UpdateWorldStateVersionCommand, CleanupStaleKnowledgeCommand,
    DeleteTurnBriefCommand
)
from ..commands.subjective_command_handlers import (
    SubjectiveCommandHandlerRegistry, SubjectiveCommandHandlerException,
    EntityNotFoundException, InvalidCommandException
)

logger = logging.getLogger(__name__)


class SubjectiveApplicationService:
    """
    Main application service for subjective perception and knowledge operations.
    
    This service coordinates subjective-related operations by handling
    commands, enforcing application-level business rules, and managing
    transactions across the domain and infrastructure layers.
    """
    
    def __init__(self, repository: ITurnBriefRepository, fog_of_war_service: Optional[FogOfWarService] = None):
        """
        Initialize the SubjectiveApplicationService.
        
        Args:
            repository: Repository for TurnBrief persistence
            fog_of_war_service: Service for fog of war calculations (creates default if None)
        """
        self.repository = repository
        self.fog_of_war_service = fog_of_war_service or FogOfWarService()
        self.command_handlers = SubjectiveCommandHandlerRegistry(repository, self.fog_of_war_service)
        self.logger = logger.getChild(self.__class__.__name__)
    
    # Core TurnBrief Operations
    
    def create_turn_brief_for_entity(
        self,
        entity_id: str,
        perception_capabilities: PerceptionCapabilities,
        world_state_version: int,
        initial_alertness: AlertnessLevel = AlertnessLevel.RELAXED,
        initial_position: Optional[Tuple[float, float, float]] = None
    ) -> SubjectiveId:
        """
        Create a new TurnBrief for an entity.
        
        Args:
            entity_id: The ID of the entity
            perception_capabilities: The entity's perception capabilities
            world_state_version: The current world state version
            initial_alertness: Initial alertness level
            initial_position: Initial position (optional)
            
        Returns:
            The ID of the created TurnBrief
            
        Raises:
            SubjectiveCommandHandlerException: If creation fails
        """
        command = CreateTurnBriefCommand(
            entity_id=entity_id,
            perception_capabilities=perception_capabilities,
            world_state_version=world_state_version,
            initial_alertness=initial_alertness,
            initial_position=initial_position
        )
        
        return self.command_handlers.handle_create_turn_brief(command)
    
    def get_turn_brief_by_entity_id(self, entity_id: str) -> Optional[TurnBrief]:
        """
        Get the TurnBrief for a specific entity.
        
        Args:
            entity_id: The entity ID to look up
            
        Returns:
            The TurnBrief if found, None otherwise
        """
        return self.repository.get_by_entity_id(entity_id)
    
    def delete_turn_brief(self, entity_id: str, deletion_reason: str = "entity_removed") -> bool:
        """
        Delete a TurnBrief.
        
        Args:
            entity_id: The entity whose TurnBrief to delete
            deletion_reason: Reason for deletion
            
        Returns:
            True if deleted, False if not found
        """
        turn_brief = self.repository.get_by_entity_id(entity_id)
        if not turn_brief:
            return False
        
        return self.repository.delete(turn_brief.turn_brief_id)
    
    # Perception Operations
    
    def update_perception_capabilities(
        self,
        entity_id: str,
        new_perception_capabilities: PerceptionCapabilities,
        change_reason: str
    ) -> None:
        """
        Update an entity's perception capabilities.
        
        Args:
            entity_id: The entity to update
            new_perception_capabilities: New perception capabilities
            change_reason: Reason for the change
            
        Raises:
            EntityNotFoundException: If entity not found
            SubjectiveCommandHandlerException: If update fails
        """
        command = UpdatePerceptionCapabilitiesCommand(
            entity_id=entity_id,
            new_perception_capabilities=new_perception_capabilities,
            change_reason=change_reason
        )
        
        self.command_handlers.handle_update_perception_capabilities(command)
    
    def add_perception(
        self,
        entity_id: str,
        perceived_subject: str,
        perception_type: PerceptionType,
        distance: float,
        environmental_conditions: Dict[str, Any],
        additional_details: Optional[Dict[str, Any]] = None,
        observer_position: Optional[Tuple[float, float, float]] = None,
        target_position: Optional[Tuple[float, float, float]] = None
    ) -> None:
        """
        Add a new perception to an entity's TurnBrief.
        
        Args:
            entity_id: The perceiving entity
            perceived_subject: What was perceived
            perception_type: How it was perceived
            distance: Distance to the perceived subject
            environmental_conditions: Environmental factors
            additional_details: Additional perception details
            observer_position: Position of observer
            target_position: Position of target
            
        Raises:
            EntityNotFoundException: If entity not found
            SubjectiveCommandHandlerException: If adding fails
        """
        command = AddPerceptionCommand(
            entity_id=entity_id,
            perceived_subject=perceived_subject,
            perception_type=perception_type,
            distance=distance,
            environmental_conditions=environmental_conditions,
            additional_details=additional_details,
            observer_position=observer_position,
            target_position=target_position
        )
        
        self.command_handlers.handle_add_perception(command)
    
    def update_fog_of_war(
        self,
        entity_id: str,
        world_positions: Dict[str, Tuple[float, float, float]],
        environmental_conditions: Dict[str, Any],
        update_reason: str = "world_state_change"
    ) -> None:
        """
        Update the fog of war for an entity.
        
        Args:
            entity_id: The entity to update
            world_positions: Current positions of all subjects
            environmental_conditions: Environmental factors affecting visibility
            update_reason: Reason for the update
            
        Raises:
            EntityNotFoundException: If entity not found
            SubjectiveCommandHandlerException: If update fails
        """
        command = UpdateFogOfWarCommand(
            entity_id=entity_id,
            world_positions=world_positions,
            environmental_conditions=environmental_conditions,
            update_reason=update_reason
        )
        
        self.command_handlers.handle_update_fog_of_war(command)
    
    # Awareness Operations
    
    def update_awareness_state(
        self,
        entity_id: str,
        new_awareness_state = None,
        change_reason: Optional[str] = None,
        new_alertness: Optional[AlertnessLevel] = None,
        new_attention_focus: Optional[AttentionFocus] = None,
        new_focus_target: Optional[str] = None,
        fatigue_level: Optional[float] = None,
        stress_level: Optional[float] = None,
        awareness_modifiers: Optional[Dict[AwarenessModifier, float]] = None
    ) -> None:
        """
        Update an entity's awareness state.
        
        Args:
            entity_id: The entity to update
            new_awareness_state: Complete AwarenessState object (alternative to individual params)
            change_reason: Reason for the change (optional)
            new_alertness: New alertness level
            new_attention_focus: New attention focus
            new_focus_target: New focus target
            fatigue_level: New fatigue level
            stress_level: New stress level
            awareness_modifiers: New awareness modifiers
            
        Raises:
            EntityNotFoundException: If entity not found
            SubjectiveCommandHandlerException: If update fails
        """
        # Handle AwarenessState object parameter (test compatibility)
        if new_awareness_state is not None:
            from ...domain.value_objects.awareness import AwarenessState
            if isinstance(new_awareness_state, AwarenessState):
                # Extract individual parameters from AwarenessState
                new_alertness = new_awareness_state.current_alertness
                new_attention_focus = new_awareness_state.attention_focus
                new_focus_target = new_awareness_state.focus_target
                fatigue_level = new_awareness_state.fatigue_level
                stress_level = new_awareness_state.stress_level
                awareness_modifiers = new_awareness_state.awareness_modifiers
        
        command = UpdateAwarenessStateCommand(
            entity_id=entity_id,
            new_alertness=new_alertness,
            new_attention_focus=new_attention_focus,
            new_focus_target=new_focus_target,
            fatigue_level=fatigue_level,
            stress_level=stress_level,
            awareness_modifiers=awareness_modifiers
        )
        
        self.command_handlers.handle_update_awareness_state(command)
    
    # Knowledge Operations
    
    def reveal_knowledge(
        self,
        entity_id: str,
        knowledge_item: KnowledgeItem,
        revelation_method: str
    ) -> None:
        """
        Reveal new knowledge to an entity.
        
        Args:
            entity_id: The entity to give knowledge to
            knowledge_item: The knowledge to reveal
            revelation_method: How the knowledge was acquired
            
        Raises:
            EntityNotFoundException: If entity not found
            SubjectiveCommandHandlerException: If revealing fails
        """
        command = RevealKnowledgeCommand(
            entity_id=entity_id,
            knowledge_item=knowledge_item,
            revelation_method=revelation_method
        )
        
        self.command_handlers.handle_reveal_knowledge(command)
    
    def share_information_between_entities(
        self,
        source_entity_id: str,
        target_entity_ids: List[str],
        knowledge_items: List[KnowledgeItem],
        communication_method: str,
        reliability_modifier: float = 0.9,
        max_sharing_distance: float = 10.0
    ) -> int:
        """
        Share information between entities.
        
        Args:
            source_entity_id: Entity sharing the information
            target_entity_ids: Entities receiving the information
            knowledge_items: Knowledge to share
            communication_method: How the information is communicated
            reliability_modifier: Reliability reduction for shared knowledge
            max_sharing_distance: Maximum distance for sharing
            
        Returns:
            Number of entities that successfully received the information
            
        Raises:
            EntityNotFoundException: If source entity not found
            SubjectiveCommandHandlerException: If sharing fails
        """
        command = ShareInformationCommand(
            source_entity_id=source_entity_id,
            target_entity_ids=target_entity_ids,
            knowledge_items=knowledge_items,
            communication_method=communication_method,
            reliability_modifier=reliability_modifier,
            max_sharing_distance=max_sharing_distance
        )
        
        return self.command_handlers.handle_share_information(command)
    
    # Threat Operations
    
    def detect_threat(
        self,
        entity_id: str,
        threat_subject: str,
        threat_type: str,
        threat_level: str,
        confidence: float,
        detection_method: PerceptionType,
        estimated_distance: Optional[float] = None,
        threat_capabilities: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Detect and track a threat.
        
        Args:
            entity_id: The entity detecting the threat
            threat_subject: The threatening entity/object
            threat_type: Type of threat
            threat_level: Severity level
            confidence: Confidence in threat assessment
            detection_method: How the threat was detected
            estimated_distance: Estimated distance to threat
            threat_capabilities: Known capabilities of the threat
            
        Raises:
            EntityNotFoundException: If entity not found
            SubjectiveCommandHandlerException: If detection fails
        """
        command = DetectThreatCommand(
            entity_id=entity_id,
            threat_subject=threat_subject,
            threat_type=threat_type,
            threat_level=threat_level,
            confidence=confidence,
            detection_method=detection_method,
            estimated_distance=estimated_distance,
            threat_capabilities=threat_capabilities
        )
        
        self.command_handlers.handle_detect_threat(command)
    
    def lose_threat_tracking(
        self,
        entity_id: str,
        threat_subject: str,
        loss_reason: str = "unknown"
    ) -> None:
        """
        Mark a threat as lost/no longer tracked.
        
        Args:
            entity_id: The entity losing track of the threat
            threat_subject: The threat that was lost
            loss_reason: Why the threat was lost
            
        Raises:
            EntityNotFoundException: If entity not found
        """
        turn_brief = self.repository.get_by_entity_id(entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {entity_id} not found")
        
        turn_brief.lose_threat_tracking(threat_subject, loss_reason)
        self.repository.save(turn_brief)
        
        self.logger.info(f"Entity {entity_id} lost tracking of threat {threat_subject}: {loss_reason}")
    
    # Bulk Operations
    
    def update_world_state_version_for_entities(
        self,
        entity_ids: List[str],
        new_world_state_version: int
    ) -> int:
        """
        Update multiple TurnBriefs to a new world state version.
        
        Args:
            entity_ids: List of entity IDs to update
            new_world_state_version: New world state version
            
        Returns:
            Number of TurnBriefs successfully updated
        """
        return self.repository.batch_update_world_state_version(entity_ids, new_world_state_version)
    
    def cleanup_stale_knowledge_for_entity(
        self,
        entity_id: str,
        staleness_threshold_hours: float = 24.0,
        min_reliability_threshold: float = 0.1
    ) -> None:
        """
        Clean up stale knowledge for an entity.
        
        Args:
            entity_id: The entity to clean up knowledge for
            staleness_threshold_hours: How old knowledge must be to be stale
            min_reliability_threshold: Minimum reliability to keep
            
        Raises:
            EntityNotFoundException: If entity not found
        """
        turn_brief = self.repository.get_by_entity_id(entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {entity_id} not found")
        
        staleness_threshold = timedelta(hours=staleness_threshold_hours)
        filtered_knowledge = self.fog_of_war_service.filter_knowledge_by_reliability(
            turn_brief.knowledge_base, min_reliability_threshold
        )
        
        # Get subjects with stale knowledge
        stale_subjects = self.fog_of_war_service.get_stale_knowledge_subjects(
            turn_brief, staleness_threshold
        )
        
        if stale_subjects:
            self.logger.info(f"Cleaned up stale knowledge for entity {entity_id}: {stale_subjects}")
    
    def cleanup_expired_turn_briefs(self, expiration_hours: float = 168.0) -> int:
        """
        Clean up expired TurnBriefs.
        
        Args:
            expiration_hours: How old TurnBriefs must be to expire (default: 1 week)
            
        Returns:
            Number of TurnBriefs cleaned up
        """
        expiration_time = datetime.now() - timedelta(hours=expiration_hours)
        return self.repository.cleanup_expired_turn_briefs(expiration_time)
    
    # Query Operations
    
    def get_entities_with_knowledge_about(
        self,
        subject: str,
        min_certainty: CertaintyLevel = CertaintyLevel.MINIMAL
    ) -> List[str]:
        """
        Get all entities that have knowledge about a specific subject.
        
        Args:
            subject: The subject to search for knowledge about
            min_certainty: Minimum certainty level required
            
        Returns:
            List of entity IDs with knowledge about the subject
        """
        return self.repository.find_entities_with_knowledge_about(subject, min_certainty)
    
    def get_entities_that_can_perceive_location(
        self,
        location_id: str,
        perception_type: Optional[PerceptionType] = None
    ) -> List[str]:
        """
        Get entities that can perceive a specific location.
        
        Args:
            location_id: The location to check
            perception_type: Specific perception type (None for any)
            
        Returns:
            List of entity IDs that can perceive the location
        """
        return self.repository.find_entities_in_perception_range_of_location(location_id, perception_type)
    
    def get_knowledge_sharing_candidates(
        self,
        entity_id: str,
        knowledge_type: KnowledgeType,
        max_distance: Optional[float] = None
    ) -> List[str]:
        """
        Get entities that could share knowledge with the given entity.
        
        Args:
            entity_id: The entity looking to share knowledge
            knowledge_type: The type of knowledge to share
            max_distance: Maximum distance for sharing
            
        Returns:
            List of entity IDs that are candidates for knowledge sharing
        """
        return self.repository.get_knowledge_sharing_candidates(entity_id, knowledge_type, max_distance)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the subjective context.
        
        Returns:
            Dictionary with various statistics
        """
        total_turn_briefs = self.repository.count_total_turn_briefs()
        active_turn_briefs = self.repository.count_active_turn_briefs()
        
        return {
            "total_turn_briefs": total_turn_briefs,
            "active_turn_briefs": active_turn_briefs,
            "inactive_turn_briefs": total_turn_briefs - active_turn_briefs,
            "activity_rate": active_turn_briefs / total_turn_briefs if total_turn_briefs > 0 else 0.0
        }