#!/usr/bin/env python3
"""
Subjective Context Command Handlers

This module implements command handlers for the Subjective bounded context.
Command handlers contain the application logic for processing commands
and coordinating between domain objects and infrastructure services.
"""

import logging

from ...domain.aggregates.turn_brief import TurnBrief
from ...domain.repositories.turn_brief_repository import (
    ConcurrencyException,
    ITurnBriefRepository,
)
from ...domain.services.fog_of_war_service import FogOfWarService
from ...domain.value_objects.awareness import AwarenessState
from ...domain.value_objects.subjective_id import SubjectiveId
from .subjective_commands import (
    AddPerceptionCommand,
    CreateTurnBriefCommand,
    DetectThreatCommand,
    RevealKnowledgeCommand,
    ShareInformationCommand,
    UpdateAwarenessStateCommand,
    UpdateFogOfWarCommand,
    UpdatePerceptionCapabilitiesCommand,
)

logger = logging.getLogger(__name__)


class SubjectiveCommandHandlerException(Exception):
    """Base exception for command handler errors."""

    pass


class EntityNotFoundException(SubjectiveCommandHandlerException):
    """Raised when an entity is not found."""

    pass


class InvalidCommandException(SubjectiveCommandHandlerException):
    """Raised when a command is invalid or cannot be processed."""

    pass


class CreateTurnBriefCommandHandler:
    """Handler for CreateTurnBriefCommand."""

    def __init__(self, repository: ITurnBriefRepository):
        self.repository = repository
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: CreateTurnBriefCommand) -> SubjectiveId:
        """
        Handle the creation of a new TurnBrief.

        Args:
            command: The command to process

        Returns:
            The ID of the created TurnBrief

        Raises:
            InvalidCommandException: If the command is invalid
            SubjectiveCommandHandlerException: If creation fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid CreateTurnBriefCommand: {e}")

        # Check if entity already has a TurnBrief
        existing = self.repository.get_by_entity_id(command.entity_id)
        if existing:
            self.logger.warning(f"Entity {command.entity_id} already has a TurnBrief")
            return existing.turn_brief_id

        try:
            # Create new TurnBrief
            turn_brief = TurnBrief.create_for_entity(
                entity_id=command.entity_id,
                perception_capabilities=command.perception_capabilities,
                world_state_version=command.world_state_version,
                initial_alertness=command.initial_alertness,
            )

            # Save to repository
            self.repository.save(turn_brief)

            self.logger.info(
                f"Created TurnBrief {turn_brief.turn_brief_id} for entity {command.entity_id}"
            )
            return turn_brief.turn_brief_id

        except Exception as e:
            self.logger.error(
                f"Failed to create TurnBrief for entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(f"TurnBrief creation failed: {e}")


class UpdatePerceptionCapabilitiesCommandHandler:
    """Handler for UpdatePerceptionCapabilitiesCommand."""

    def __init__(self, repository: ITurnBriefRepository):
        self.repository = repository
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: UpdatePerceptionCapabilitiesCommand) -> None:
        """
        Handle updating perception capabilities.

        Args:
            command: The command to process

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the entity is not found
            SubjectiveCommandHandlerException: If update fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(
                f"Invalid UpdatePerceptionCapabilitiesCommand: {e}"
            )

        turn_brief = self.repository.get_by_entity_id(command.entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {command.entity_id} not found")

        try:
            turn_brief.update_perception_capabilities(
                command.new_perception_capabilities, command.change_reason
            )

            self.repository.save(turn_brief)

            self.logger.info(
                f"Updated perception capabilities for entity {command.entity_id}"
            )

        except ConcurrencyException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to update perception capabilities for entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(
                f"Perception capabilities update failed: {e}"
            )


class UpdateAwarenessStateCommandHandler:
    """Handler for UpdateAwarenessStateCommand."""

    def __init__(self, repository: ITurnBriefRepository):
        self.repository = repository
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: UpdateAwarenessStateCommand) -> None:
        """
        Handle updating awareness state.

        Args:
            command: The command to process

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the entity is not found
            SubjectiveCommandHandlerException: If update fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid UpdateAwarenessStateCommand: {e}")

        turn_brief = self.repository.get_by_entity_id(command.entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {command.entity_id} not found")

        try:
            # Build new awareness state from current state and command updates
            current_awareness = turn_brief.awareness_state

            new_awareness = AwarenessState(
                base_alertness=current_awareness.base_alertness,
                current_alertness=command.new_alertness
                or current_awareness.current_alertness,
                attention_focus=command.new_attention_focus
                or current_awareness.attention_focus,
                focus_target=(
                    command.new_focus_target
                    if command.new_focus_target is not None
                    else current_awareness.focus_target
                ),
                awareness_modifiers=(
                    command.awareness_modifiers
                    if command.awareness_modifiers is not None
                    else current_awareness.awareness_modifiers
                ),
                fatigue_level=(
                    command.fatigue_level
                    if command.fatigue_level is not None
                    else current_awareness.fatigue_level
                ),
                stress_level=(
                    command.stress_level
                    if command.stress_level is not None
                    else current_awareness.stress_level
                ),
            )

            turn_brief.update_awareness_state(new_awareness)
            self.repository.save(turn_brief)

            self.logger.info(f"Updated awareness state for entity {command.entity_id}")

        except ConcurrencyException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to update awareness state for entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(
                f"Awareness state update failed: {e}"
            )


class AddPerceptionCommandHandler:
    """Handler for AddPerceptionCommand."""

    def __init__(
        self, repository: ITurnBriefRepository, fog_of_war_service: FogOfWarService
    ):
        self.repository = repository
        self.fog_of_war_service = fog_of_war_service
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: AddPerceptionCommand) -> None:
        """
        Handle adding a perception.

        Args:
            command: The command to process

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the entity is not found
            SubjectiveCommandHandlerException: If adding perception fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid AddPerceptionCommand: {e}")

        turn_brief = self.repository.get_by_entity_id(command.entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {command.entity_id} not found")

        try:
            # Calculate visibility level using fog of war service
            if command.observer_position and command.target_position:
                visibility_results = (
                    self.fog_of_war_service.calculate_visibility_between_positions(
                        turn_brief,
                        command.observer_position,
                        command.target_position,
                        command.environmental_conditions,
                    )
                )
                visibility_level = visibility_results.get(
                    command.perception_type,
                    turn_brief.can_perceive_at_distance(
                        command.distance, command.perception_type
                    ),
                )
            else:
                # Use TurnBrief's own perception calculation
                visibility_level = turn_brief.can_perceive_at_distance(
                    command.distance, command.perception_type
                )

            turn_brief.add_perception(
                subject=command.perceived_subject,
                perception_type=command.perception_type,
                visibility_level=visibility_level,
                distance=command.distance,
                additional_details=command.additional_details,
            )

            self.repository.save(turn_brief)

            self.logger.debug(
                f"Added {command.perception_type.value} perception of {command.perceived_subject} "
                f"for entity {command.entity_id}"
            )

        except ConcurrencyException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to add perception for entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(f"Add perception failed: {e}")


class RevealKnowledgeCommandHandler:
    """Handler for RevealKnowledgeCommand."""

    def __init__(self, repository: ITurnBriefRepository):
        self.repository = repository
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: RevealKnowledgeCommand) -> None:
        """
        Handle revealing knowledge.

        Args:
            command: The command to process

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the entity is not found
            SubjectiveCommandHandlerException: If revealing knowledge fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid RevealKnowledgeCommand: {e}")

        turn_brief = self.repository.get_by_entity_id(command.entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {command.entity_id} not found")

        try:
            turn_brief.add_knowledge(command.knowledge_item, command.revelation_method)
            self.repository.save(turn_brief)

            self.logger.info(
                f"Revealed knowledge about {command.knowledge_item.subject} "
                f"to entity {command.entity_id}"
            )

        except ConcurrencyException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to reveal knowledge to entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(f"Reveal knowledge failed: {e}")


class DetectThreatCommandHandler:
    """Handler for DetectThreatCommand."""

    def __init__(self, repository: ITurnBriefRepository):
        self.repository = repository
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: DetectThreatCommand) -> None:
        """
        Handle threat detection.

        Args:
            command: The command to process

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the entity is not found
            SubjectiveCommandHandlerException: If threat detection fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid DetectThreatCommand: {e}")

        turn_brief = self.repository.get_by_entity_id(command.entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {command.entity_id} not found")

        try:
            turn_brief.detect_threat(
                threat_subject=command.threat_subject,
                threat_type=command.threat_type,
                threat_level=command.threat_level,
                confidence=command.confidence,
                detection_method=command.detection_method,
                estimated_distance=command.estimated_distance,
            )

            self.repository.save(turn_brief)

            self.logger.info(
                f"Entity {command.entity_id} detected {command.threat_level} "
                f"threat: {command.threat_subject}"
            )

        except ConcurrencyException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to detect threat for entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(f"Threat detection failed: {e}")


class UpdateFogOfWarCommandHandler:
    """Handler for UpdateFogOfWarCommand."""

    def __init__(
        self, repository: ITurnBriefRepository, fog_of_war_service: FogOfWarService
    ):
        self.repository = repository
        self.fog_of_war_service = fog_of_war_service
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: UpdateFogOfWarCommand) -> None:
        """
        Handle fog of war updates.

        Args:
            command: The command to process

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the entity is not found
            SubjectiveCommandHandlerException: If fog of war update fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid UpdateFogOfWarCommand: {e}")

        turn_brief = self.repository.get_by_entity_id(command.entity_id)
        if not turn_brief:
            raise EntityNotFoundException(f"Entity {command.entity_id} not found")

        try:
            # Use fog of war service to calculate visibility changes
            (
                newly_revealed,
                newly_concealed,
                visibility_changes,
            ) = self.fog_of_war_service.update_visible_subjects_for_turn_brief(
                turn_brief,
                command.world_positions,
                command.environmental_conditions,
            )

            # Update the TurnBrief with the changes
            turn_brief.update_fog_of_war(
                newly_revealed,
                newly_concealed,
                visibility_changes,
                command.update_reason,
            )

            self.repository.save(turn_brief)

            self.logger.debug(
                f"Updated fog of war for entity {command.entity_id}: "
                f"{len(newly_revealed)} revealed, {len(newly_concealed)} concealed"
            )

        except ConcurrencyException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to update fog of war for entity {command.entity_id}: {e}"
            )
            raise SubjectiveCommandHandlerException(f"Fog of war update failed: {e}")


class ShareInformationCommandHandler:
    """Handler for ShareInformationCommand."""

    def __init__(
        self, repository: ITurnBriefRepository, fog_of_war_service: FogOfWarService
    ):
        self.repository = repository
        self.fog_of_war_service = fog_of_war_service
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, command: ShareInformationCommand) -> int:
        """
        Handle information sharing between entities.

        Args:
            command: The command to process

        Returns:
            Number of entities that successfully received the information

        Raises:
            InvalidCommandException: If the command is invalid
            EntityNotFoundException: If the source entity is not found
            SubjectiveCommandHandlerException: If sharing fails
        """
        try:
            command.validate()
        except ValueError as e:
            raise InvalidCommandException(f"Invalid ShareInformationCommand: {e}")

        source_turn_brief = self.repository.get_by_entity_id(command.source_entity_id)
        if not source_turn_brief:
            raise EntityNotFoundException(
                f"Source entity {command.source_entity_id} not found"
            )

        successful_shares = 0

        for target_entity_id in command.target_entity_ids:
            try:
                target_turn_brief = self.repository.get_by_entity_id(target_entity_id)
                if not target_turn_brief:
                    self.logger.warning(
                        f"Target entity {target_entity_id} not found, skipping"
                    )
                    continue

                # Use fog of war service to determine if sharing is possible
                propagatable_knowledge = (
                    self.fog_of_war_service.propagate_knowledge_between_entities(
                        source_turn_brief=source_turn_brief,
                        target_turn_brief=target_turn_brief,
                        knowledge_types=[
                            item.knowledge_type for item in command.knowledge_items
                        ],
                        max_propagation_distance=command.max_sharing_distance,
                        source_reliability_modifier=command.reliability_modifier,
                    )
                )

                # Share the knowledge items that can be propagated
                for knowledge_item in command.knowledge_items:
                    # Check if this knowledge can be shared
                    if any(
                        pk.subject == knowledge_item.subject
                        for pk in propagatable_knowledge
                    ):
                        target_turn_brief.add_knowledge(
                            knowledge_item,
                            f"shared_by_{command.source_entity_id}_{command.communication_method}",
                        )

                self.repository.save(target_turn_brief)
                successful_shares += 1

                self.logger.debug(
                    f"Shared information from {command.source_entity_id} "
                    f"to {target_entity_id}"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to share information to {target_entity_id}: {e}"
                )
                continue

        self.logger.info(
            f"Successfully shared information from {command.source_entity_id} "
            f"to {successful_shares}/{len(command.target_entity_ids)} targets"
        )

        return successful_shares


class SubjectiveCommandHandlerRegistry:
    """Registry for all Subjective command handlers."""

    def __init__(
        self, repository: ITurnBriefRepository, fog_of_war_service: FogOfWarService
    ):
        self.repository = repository
        self.fog_of_war_service = fog_of_war_service

        # Initialize handlers
        self.create_handler = CreateTurnBriefCommandHandler(repository)
        self.update_perception_handler = UpdatePerceptionCapabilitiesCommandHandler(
            repository
        )
        self.update_awareness_handler = UpdateAwarenessStateCommandHandler(repository)
        self.add_perception_handler = AddPerceptionCommandHandler(
            repository, fog_of_war_service
        )
        self.reveal_knowledge_handler = RevealKnowledgeCommandHandler(repository)
        self.detect_threat_handler = DetectThreatCommandHandler(repository)
        self.update_fog_of_war_handler = UpdateFogOfWarCommandHandler(
            repository, fog_of_war_service
        )
        self.share_information_handler = ShareInformationCommandHandler(
            repository, fog_of_war_service
        )

        self.logger = logger.getChild(self.__class__.__name__)

    def handle_create_turn_brief(self, command: CreateTurnBriefCommand) -> SubjectiveId:
        """Handle CreateTurnBriefCommand."""
        return self.create_handler.handle(command)

    def handle_update_perception_capabilities(
        self, command: UpdatePerceptionCapabilitiesCommand
    ) -> None:
        """Handle UpdatePerceptionCapabilitiesCommand."""
        self.update_perception_handler.handle(command)

    def handle_update_awareness_state(
        self, command: UpdateAwarenessStateCommand
    ) -> None:
        """Handle UpdateAwarenessStateCommand."""
        self.update_awareness_handler.handle(command)

    def handle_add_perception(self, command: AddPerceptionCommand) -> None:
        """Handle AddPerceptionCommand."""
        self.add_perception_handler.handle(command)

    def handle_reveal_knowledge(self, command: RevealKnowledgeCommand) -> None:
        """Handle RevealKnowledgeCommand."""
        self.reveal_knowledge_handler.handle(command)

    def handle_detect_threat(self, command: DetectThreatCommand) -> None:
        """Handle DetectThreatCommand."""
        self.detect_threat_handler.handle(command)

    def handle_update_fog_of_war(self, command: UpdateFogOfWarCommand) -> None:
        """Handle UpdateFogOfWarCommand."""
        self.update_fog_of_war_handler.handle(command)

    def handle_share_information(self, command: ShareInformationCommand) -> int:
        """Handle ShareInformationCommand."""
        return self.share_information_handler.handle(command)
