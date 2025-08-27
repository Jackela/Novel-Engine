#!/usr/bin/env python3
"""
Event Integration Phase Implementation

Takes interaction results and integrates them into the World context,
updating entity states, world conditions, and maintaining event consistency.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ...domain.value_objects import PhaseType
from .base_phase import BasePhaseImplementation, PhaseExecutionContext, PhaseResult


class EventIntegrationPhase(BasePhaseImplementation):
    """
    Implementation of event integration pipeline phase.
    
    Coordinates with World context to:
    - Process interaction results and outcomes
    - Update entity states based on interaction results
    - Apply world state changes from agent actions
    - Maintain event causality and consistency
    - Create integration events for downstream processing
    """
    
    def __init__(self):
        super().__init__(PhaseType.EVENT_INTEGRATION)
        self.execution_timeout_ms = 12000  # 12 seconds for event processing
        self.world_service_endpoint = "world_context"
        self.event_service_endpoint = "event_context"
        
    async def _execute_phase_implementation(
        self,
        context: PhaseExecutionContext
    ) -> PhaseResult:
        """
        Execute event integration for all interaction results.
        
        Args:
            context: Phase execution context
            
        Returns:
            PhaseResult with event integration results
        """
        # Initialize phase metrics
        events_processed = 0
        world_updates_applied = 0
        entity_changes = 0
        consistency_violations = 0
        
        try:
            # Step 1: Collect interaction results from previous phase
            interaction_results = await self._collect_interaction_results(context)
            
            # Step 2: Process each interaction result into world events
            world_events = []
            for result in interaction_results:
                try:
                    processed_events = await self._process_interaction_result(context, result)
                    world_events.extend(processed_events)
                    events_processed += 1
                    
                except Exception as e:
                    # Log individual result processing failure but continue
                    context.record_performance_metric(
                        'result_processing_failures',
                        context.performance_metrics.get('result_processing_failures', 0) + 1
                    )
            
            # Step 3: Apply world state changes
            world_updates_applied = await self._apply_world_state_changes(context, world_events)
            
            # Step 4: Update entity states based on events
            entity_changes = await self._update_entity_states(context, world_events)
            
            # Step 5: Validate event consistency
            consistency_violations = await self._validate_event_consistency(context, world_events)
            
            # Step 6: Generate integration summary events
            integration_events = await self._generate_integration_events(
                context, events_processed, world_updates_applied, entity_changes
            )
            
            # Record performance metrics
            context.record_performance_metric('events_processed', float(events_processed))
            context.record_performance_metric('world_updates_applied', float(world_updates_applied))
            context.record_performance_metric('entity_changes', float(entity_changes))
            context.record_performance_metric('consistency_violations', float(consistency_violations))
            
            # Calculate success rate
            success_rate = (events_processed - consistency_violations) / max(1, events_processed)
            
            return PhaseResult(
                success=success_rate > 0.7 and consistency_violations == 0,  # Success if >70% processed and no violations
                events_processed=events_processed,
                events_generated=integration_events,
                artifacts_created=[
                    f"world_events_{len(world_events)}",
                    f"world_updates_{world_updates_applied}",
                    f"entity_changes_{entity_changes}"
                ],
                metadata={
                    'event_integration_summary': {
                        'interaction_results_processed': len(interaction_results),
                        'world_events_created': len(world_events),
                        'world_updates_applied': world_updates_applied,
                        'entity_changes': entity_changes,
                        'consistency_violations': consistency_violations,
                        'success_rate': success_rate
                    }
                }
            )
            
        except Exception as e:
            return self._create_failure_result(
                context,
                f"Event integration failed: {e}",
                {
                    'partial_results': {
                        'events_processed': events_processed,
                        'world_updates_applied': world_updates_applied,
                        'entity_changes': entity_changes
                    }
                }
            )
    
    def _validate_preconditions(self, context: PhaseExecutionContext) -> None:
        """
        Validate preconditions for event integration.
        
        Args:
            context: Phase execution context
            
        Raises:
            ValueError: If preconditions are not met
        """
        # Check that we have previous phase results to process
        if not hasattr(context, 'previous_phase_results'):
            # This is acceptable - we'll check for results during execution
            pass
        
        # Validate participants are available for entity updates
        if not context.participants:
            # Valid case - events can be processed without participants
            pass
        
        # Check world service accessibility
        if not self.world_service_endpoint:
            raise ValueError("World service endpoint not configured")
    
    async def _collect_interaction_results(
        self,
        context: PhaseExecutionContext
    ) -> List[Dict[str, Any]]:
        """
        Collect interaction results from previous phase execution.
        
        Args:
            context: Phase execution context
            
        Returns:
            List of interaction results to process
        """
        # Get interaction results from previous phase metadata
        interaction_results = []
        
        # Check execution metadata for interaction results
        previous_results = context.execution_metadata.get('previous_phase_results', {})
        interaction_phase_results = previous_results.get('interaction_orchestration', {})
        
        # Extract session results from interaction phase
        session_results = interaction_phase_results.get('session_results', {})
        for session_id, result in session_results.items():
            if result.get('completed'):
                interaction_results.append({
                    'session_id': session_id,
                    'result': result,
                    'participants': result.get('participants', []),
                    'interaction_type': result.get('interaction_subtype'),
                    'resolution': result.get('resolution', {})
                })
        
        # If no results from metadata, query interaction context directly
        if not interaction_results:
            interaction_response = await self._call_external_service(
                context,
                "interaction_context",
                "get_recent_interaction_results",
                {
                    'turn_id': str(context.turn_id),
                    'include_resolutions': True
                }
            )
            
            interaction_results = interaction_response.get('results', [])
        
        return interaction_results
    
    async def _process_interaction_result(
        self,
        context: PhaseExecutionContext,
        interaction_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process a single interaction result into world events.
        
        Args:
            context: Phase execution context
            interaction_result: Interaction result to process
            
        Returns:
            List of world events generated from this interaction
        """
        events = []
        participants = interaction_result.get('participants', [])
        interaction_type = interaction_result.get('interaction_type')
        resolution = interaction_result.get('resolution', {})
        
        # Process based on interaction type
        if interaction_type == 'agent_interaction':
            events.extend(await self._process_agent_interaction_result(
                context, participants, resolution
            ))
        elif interaction_type == 'environment_interaction':
            events.extend(await self._process_environment_interaction_result(
                context, participants, resolution
            ))
        elif interaction_type == 'npc_interaction':
            events.extend(await self._process_npc_interaction_result(
                context, participants, resolution
            ))
        elif interaction_type == 'collaboration':
            events.extend(await self._process_collaboration_result(
                context, participants, resolution
            ))
        else:
            # Generic interaction processing
            events.append(await self._create_generic_interaction_event(
                context, participants, interaction_result
            ))
        
        return events
    
    async def _process_agent_interaction_result(
        self,
        context: PhaseExecutionContext,
        participants: List[str],
        resolution: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process agent-to-agent interaction results into world events."""
        events = []
        
        outcome = resolution.get('outcome')
        
        if outcome == 'agreement':
            # Create agreement event affecting both agents
            events.append({
                'event_type': 'agent_agreement',
                'event_id': str(uuid4()),
                'participants': participants,
                'agreed_terms': resolution.get('agreed_terms', {}),
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'relationship_improvement'
            })
            
        elif outcome == 'compromise':
            # Create compromise event
            events.append({
                'event_type': 'agent_compromise',
                'event_id': str(uuid4()),
                'participants': participants,
                'compromise_terms': resolution.get('compromise_terms', {}),
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'relationship_neutral'
            })
            
        elif outcome == 'resolution':
            # Create conflict resolution event
            winner = resolution.get('winner')
            losers = resolution.get('losers', [])
            
            events.append({
                'event_type': 'conflict_resolution',
                'event_id': str(uuid4()),
                'winner': winner,
                'losers': losers,
                'winning_action': resolution.get('winning_action', {}),
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'relationship_change'
            })
            
        elif outcome == 'success':
            # Create cooperation success event
            events.append({
                'event_type': 'cooperation_success',
                'event_id': str(uuid4()),
                'participants': participants,
                'contributions': resolution.get('contributions', {}),
                'total_benefit': resolution.get('total_benefit', 0),
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'relationship_improvement'
            })
        
        return events
    
    async def _process_environment_interaction_result(
        self,
        context: PhaseExecutionContext,
        participants: List[str],
        resolution: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process agent-environment interaction results into world events."""
        events = []
        
        target = resolution.get('target')
        actions_executed = resolution.get('actions_executed', 0)
        
        if actions_executed > 0:
            events.append({
                'event_type': 'environment_interaction',
                'event_id': str(uuid4()),
                'participants': participants,
                'target': target,
                'actions_executed': actions_executed,
                'interaction_subtype': resolution.get('interaction_subtype'),
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'environment_change'
            })
        
        return events
    
    async def _process_npc_interaction_result(
        self,
        context: PhaseExecutionContext,
        participants: List[str],
        resolution: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process agent-NPC interaction results into world events."""
        events = []
        
        npc = resolution.get('npc')
        interactions_completed = resolution.get('interactions_completed', 0)
        
        if interactions_completed > 0 and npc:
            events.append({
                'event_type': 'npc_interaction',
                'event_id': str(uuid4()),
                'participants': participants,
                'npc_id': npc.get('id'),
                'npc_type': npc.get('type'),
                'interaction_subtype': resolution.get('interaction_subtype'),
                'interactions_completed': interactions_completed,
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'npc_relationship_change'
            })
        
        return events
    
    async def _process_collaboration_result(
        self,
        context: PhaseExecutionContext,
        participants: List[str],
        resolution: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process multi-agent collaboration results into world events."""
        events = []
        
        task = resolution.get('task')
        collaboration_outcome = resolution.get('collaboration_outcome', {})
        
        if task and collaboration_outcome.get('success'):
            events.append({
                'event_type': 'collaboration_completed',
                'event_id': str(uuid4()),
                'participants': participants,
                'task_type': task.get('task_type'),
                'task_id': task.get('id'),
                'outcome': collaboration_outcome,
                'timestamp': datetime.now().isoformat(),
                'turn_id': str(context.turn_id),
                'world_impact': 'collaborative_achievement'
            })
        
        return events
    
    async def _create_generic_interaction_event(
        self,
        context: PhaseExecutionContext,
        participants: List[str],
        interaction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create generic interaction event for unknown interaction types."""
        return {
            'event_type': 'generic_interaction',
            'event_id': str(uuid4()),
            'participants': participants,
            'interaction_data': interaction_result,
            'timestamp': datetime.now().isoformat(),
            'turn_id': str(context.turn_id),
            'world_impact': 'minor_change'
        }
    
    async def _apply_world_state_changes(
        self,
        context: PhaseExecutionContext,
        world_events: List[Dict[str, Any]]
    ) -> int:
        """
        Apply world state changes based on processed events.
        
        Args:
            context: Phase execution context
            world_events: List of world events to apply
            
        Returns:
            Number of world updates successfully applied
        """
        updates_applied = 0
        
        # Group events by impact type for efficient processing
        event_groups = {}
        for event in world_events:
            impact_type = event.get('world_impact', 'minor_change')
            if impact_type not in event_groups:
                event_groups[impact_type] = []
            event_groups[impact_type].append(event)
        
        # Process each impact type
        for impact_type, events in event_groups.items():
            try:
                # Apply world changes based on impact type
                update_response = await self._call_external_service(
                    context,
                    self.world_service_endpoint,
                    "apply_event_batch",
                    {
                        'events': events,
                        'impact_type': impact_type,
                        'turn_id': str(context.turn_id),
                        'source_phase': 'event_integration'
                    }
                )
                
                if update_response.get('success'):
                    updates_applied += update_response.get('updates_applied', 0)
                    
                    # Record successful update
                    self._record_event_generation(
                        context,
                        "world_state_updated",
                        {
                            'impact_type': impact_type,
                            'events_processed': len(events),
                            'updates_applied': update_response.get('updates_applied', 0)
                        }
                    )
                
            except Exception as e:
                # Log failure but continue with other event groups
                context.record_performance_metric(
                    f'world_update_failures_{impact_type}',
                    context.performance_metrics.get(f'world_update_failures_{impact_type}', 0) + 1
                )
        
        return updates_applied
    
    async def _update_entity_states(
        self,
        context: PhaseExecutionContext,
        world_events: List[Dict[str, Any]]
    ) -> int:
        """
        Update entity states based on world events.
        
        Args:
            context: Phase execution context
            world_events: List of world events affecting entities
            
        Returns:
            Number of entity state changes applied
        """
        entity_changes = 0
        
        # Collect all entities mentioned in events
        affected_entities: Dict[str, List[Dict[str, Any]]] = {}
        
        for event in world_events:
            participants = event.get('participants', [])
            for participant in participants:
                if participant not in affected_entities:
                    affected_entities[participant] = []
                affected_entities[participant].append(event)
        
        # Update each affected entity
        for entity_id, entity_events in affected_entities.items():
            try:
                # Calculate entity state changes based on events
                state_changes = self._calculate_entity_state_changes(entity_events)
                
                if state_changes:
                    # Apply entity state changes
                    update_response = await self._call_external_service(
                        context,
                        self.world_service_endpoint,
                        "update_entity_state",
                        {
                            'entity_id': entity_id,
                            'state_changes': state_changes,
                            'source_events': [e.get('event_id') for e in entity_events],
                            'turn_id': str(context.turn_id)
                        }
                    )
                    
                    if update_response.get('success'):
                        entity_changes += 1
                        
                        # Record entity state change
                        self._record_event_generation(
                            context,
                            "entity_state_updated",
                            {
                                'entity_id': entity_id,
                                'changes_applied': state_changes,
                                'events_processed': len(entity_events)
                            }
                        )
                
            except Exception as e:
                # Log entity update failure but continue
                context.record_performance_metric(
                    'entity_update_failures',
                    context.performance_metrics.get('entity_update_failures', 0) + 1
                )
        
        return entity_changes
    
    async def _validate_event_consistency(
        self,
        context: PhaseExecutionContext,
        world_events: List[Dict[str, Any]]
    ) -> int:
        """
        Validate consistency of processed events.
        
        Args:
            context: Phase execution context
            world_events: List of world events to validate
            
        Returns:
            Number of consistency violations found
        """
        violations = 0
        
        # Check for temporal consistency
        violations += self._check_temporal_consistency(world_events)
        
        # Check for logical consistency
        violations += self._check_logical_consistency(world_events)
        
        # Check for participant consistency
        violations += self._check_participant_consistency(world_events, context.participants)
        
        # Validate with world context
        if world_events:
            consistency_response = await self._call_external_service(
                context,
                self.world_service_endpoint,
                "validate_event_consistency",
                {
                    'events': world_events,
                    'turn_id': str(context.turn_id)
                }
            )
            
            violations += len(consistency_response.get('violations', []))
        
        if violations > 0:
            # Record consistency violations
            self._record_event_generation(
                context,
                "event_consistency_violations",
                {
                    'violations_count': violations,
                    'events_checked': len(world_events),
                    'violation_types': ['temporal', 'logical', 'participant', 'world_state']
                }
            )
        
        return violations
    
    async def _generate_integration_events(
        self,
        context: PhaseExecutionContext,
        events_processed: int,
        world_updates_applied: int,
        entity_changes: int
    ) -> List:
        """
        Generate events for integration phase results.
        
        Args:
            context: Phase execution context
            events_processed: Number of events processed
            world_updates_applied: Number of world updates applied
            entity_changes: Number of entity changes made
            
        Returns:
            List of generated event IDs
        """
        events_generated = []
        
        # Generate event integration summary event
        summary_event_id = self._record_event_generation(
            context,
            "event_integration_completed",
            {
                'turn_id': str(context.turn_id),
                'events_processed': events_processed,
                'world_updates_applied': world_updates_applied,
                'entity_changes': entity_changes,
                'participants': context.participants,
                'completed_at': datetime.now().isoformat()
            }
        )
        events_generated.append(summary_event_id)
        
        return events_generated
    
    # Helper methods
    
    def _calculate_entity_state_changes(
        self,
        entity_events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate entity state changes based on events affecting the entity.
        
        Args:
            entity_events: List of events affecting this entity
            
        Returns:
            Dictionary of state changes to apply
        """
        changes = {}
        
        # Analyze events to determine state changes
        for event in entity_events:
            event_type = event.get('event_type')
            
            if event_type == 'agent_agreement':
                # Agreements might improve relationships or unlock new capabilities
                changes['relationship_status'] = 'improved'
                changes['last_agreement'] = event.get('event_id')
                
            elif event_type == 'conflict_resolution':
                winner = event.get('winner')
                losers = event.get('losers', [])
                
                # Winners might gain confidence, losers might lose it
                if winner in event.get('participants', []):
                    changes['confidence'] = changes.get('confidence', 0) + 10
                elif any(loser in event.get('participants', []) for loser in losers):
                    changes['confidence'] = changes.get('confidence', 0) - 5
                
            elif event_type == 'cooperation_success':
                # Successful cooperation improves social skills and relationships
                changes['cooperation_experience'] = changes.get('cooperation_experience', 0) + 1
                changes['social_reputation'] = 'improved'
                
            elif event_type == 'environment_interaction':
                # Environment interactions might change entity position or resources
                changes['last_environment_interaction'] = event.get('timestamp')
                changes['environment_experience'] = changes.get('environment_experience', 0) + 1
                
            elif event_type == 'npc_interaction':
                # NPC interactions might improve NPC relationships
                npc_id = event.get('npc_id')
                if npc_id:
                    changes[f'npc_relationship_{npc_id}'] = 'improved'
        
        # Clean up changes (remove zero values, etc.)
        return {k: v for k, v in changes.items() if v is not None}
    
    def _check_temporal_consistency(self, events: List[Dict[str, Any]]) -> int:
        """Check temporal consistency of events."""
        violations = 0
        
        # Verify all events have timestamps
        for event in events:
            if not event.get('timestamp'):
                violations += 1
        
        # Check for reasonable temporal ordering
        timestamps = [event.get('timestamp') for event in events if event.get('timestamp')]
        if len(timestamps) > 1:
            try:
                # Verify timestamps are within reasonable range
                parsed_times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
                time_range = max(parsed_times) - min(parsed_times)
                
                # Events shouldn't span more than an hour for a single turn
                if time_range.total_seconds() > 3600:
                    violations += 1
                    
            except ValueError:
                violations += 1  # Invalid timestamp format
        
        return violations
    
    def _check_logical_consistency(self, events: List[Dict[str, Any]]) -> int:
        """Check logical consistency of events."""
        violations = 0
        
        # Check for contradictory events
        event_types = [event.get('event_type') for event in events]
        
        # Example: Can't have both agreement and conflict resolution for same participants
        if 'agent_agreement' in event_types and 'conflict_resolution' in event_types:
            # Check if same participants are involved in contradictory events
            agreement_events = [e for e in events if e.get('event_type') == 'agent_agreement']
            conflict_events = [e for e in events if e.get('event_type') == 'conflict_resolution']
            
            for agreement in agreement_events:
                for conflict in conflict_events:
                    agreement_participants = set(agreement.get('participants', []))
                    conflict_participants = set(conflict.get('participants', []))
                    
                    if agreement_participants & conflict_participants:  # Overlapping participants
                        violations += 1
        
        return violations
    
    def _check_participant_consistency(
        self,
        events: List[Dict[str, Any]],
        valid_participants: List[str]
    ) -> int:
        """Check participant consistency in events."""
        violations = 0
        
        # Check that all event participants are valid
        for event in events:
            event_participants = event.get('participants', [])
            for participant in event_participants:
                if participant not in valid_participants:
                    violations += 1
        
        return violations