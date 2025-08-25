#!/usr/bin/env python3
"""
Turn Execution Engine
=====================

Manages turn execution logic and coordination with integrated
SubjectiveRealityEngine and EmergentNarrativeEngine.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import core engines for integration
from src.core.subjective_reality import SubjectiveRealityEngine, TurnBriefFactory
from src.core.emergent_narrative import EmergentNarrativeEngine, CausalGraph
from src.core.data_models import StandardResponse, ErrorInfo


class TurnExecutionEngine:
    """
    Manages turn execution logic and coordination with integrated
    subjective reality and emergent narrative engines.
    
    Responsibilities:
    - Turn sequence management with personalized agent briefs
    - Agent turn coordination with causal event tracking
    - Turn result aggregation with narrative coherence
    - Performance monitoring and subjective reality metrics
    """
    
    def __init__(self, agent_manager, state_manager=None, logger: Optional[logging.Logger] = None):
        """Initialize turn execution engine with core engines."""
        self.agent_manager = agent_manager
        self.state_manager = state_manager
        self.logger = logger or logging.getLogger(__name__)
        self.turn_metrics = {}
        self._initialized = False
        
        # Initialize core engines
        self.subjective_reality_engine = SubjectiveRealityEngine()
        self.emergent_narrative_engine = EmergentNarrativeEngine()
        self.turn_brief_factory = self.subjective_reality_engine.turn_brief_factory
        self.causal_graph = self.emergent_narrative_engine.causal_graph
        
        # Turn counter for briefing system
        self.current_turn_number = 0
    
    async def initialize(self) -> bool:
        """Initialize the turn engine and core engines."""
        try:
            self.logger.info("Initializing TurnExecutionEngine with core engines")
            
            # Initialize core engines
            await self.subjective_reality_engine.initialize()
            await self.emergent_narrative_engine.initialize()
            
            self.logger.info("SubjectiveRealityEngine and EmergentNarrativeEngine initialized")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"TurnExecutionEngine initialization failed: {e}")
            return False
    
    async def execute_turn(self, turn_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a complete simulation turn with subjective reality and narrative integration.
        
        Args:
            turn_data: Optional turn configuration including world state
            
        Returns:
            Dict containing turn execution results with subjective briefs and narrative events
        """
        start_time = datetime.now()
        self.current_turn_number += 1
        
        try:
            self.logger.debug(f"Executing simulation turn #{self.current_turn_number}")
            
            # Initialize turn result with enhanced structure
            turn_result = self._initialize_enhanced_turn_result(start_time)
            
            # Phase 1: Generate subjective reality turn briefs for all agents
            await self._generate_turn_briefs(turn_result, turn_data)
            
            # Phase 2: Execute agents with personalized briefs
            await self._execute_all_agents_with_briefs(turn_result, turn_data)
            
            # Phase 3: Process results through emergent narrative engine
            await self._process_narrative_coherence(turn_result)
            
            # Phase 4: Finalize with enhanced metrics
            self._finalize_enhanced_turn_result(turn_result, start_time)
            
            return turn_result
            
        except Exception as e:
            return self._create_error_result(e, start_time)
    
    def _initialize_enhanced_turn_result(self, start_time: datetime) -> Dict[str, Any]:
        """Initialize enhanced turn result structure with subjective reality and narrative data."""
        return {
            'success': False,
            'turn_number': self.current_turn_number,
            'agent_results': {},
            'agent_briefs': {},  # New: personalized turn briefs
            'world_state_changes': {},
            'narrative_events': [],
            'causal_events': [],  # New: causal graph events
            'narrative_coherence': {},  # New: coherence analysis
            'subjective_metrics': {},  # New: subjective reality metrics
            'metrics': {},
            'timestamp': start_time.isoformat()
        }
        
    def _initialize_turn_result(self, start_time: datetime) -> Dict[str, Any]:
        """Initialize turn result structure (legacy method)."""
        return self._initialize_enhanced_turn_result(start_time)
    
    async def _generate_turn_briefs(self, turn_result: Dict[str, Any], 
                                  turn_data: Optional[Dict[str, Any]]) -> None:
        """Generate personalized turn briefs for all agents using SubjectiveRealityEngine."""
        try:
            self.logger.debug("Generating personalized turn briefs")
            
            # Extract world state from turn_data or use default
            global_world_state = turn_data.get('world_state', {}) if turn_data else {}
            
            # Generate briefs for all agents
            for agent_id, agent in self.agent_manager.agents.items():
                try:
                    # Generate personalized turn brief
                    brief = await self.turn_brief_factory.generate_turn_brief(
                        agent_id=agent_id,
                        turn_number=self.current_turn_number,
                        global_world_state=global_world_state,
                        agent=agent
                    )
                    
                    turn_result['agent_briefs'][agent_id] = brief
                    self.logger.debug(f"Generated turn brief for agent {agent_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate brief for agent {agent_id}: {e}")
                    turn_result['agent_briefs'][agent_id] = {
                        'error': str(e),
                        'agent_id': agent_id,
                        'turn_number': self.current_turn_number
                    }
                    
        except Exception as e:
            self.logger.error(f"Turn brief generation failed: {e}")
    
    async def _execute_all_agents_with_briefs(self, turn_result: Dict[str, Any], 
                                            turn_data: Optional[Dict[str, Any]]) -> None:
        """Execute turn for all agents with their personalized briefs."""
        for agent_id, agent in self.agent_manager.agents.items():
            await self._execute_single_agent_with_brief(turn_result, agent_id, agent, turn_data)
    
    async def _execute_all_agents(self, turn_result: Dict[str, Any], 
                                turn_data: Optional[Dict[str, Any]]) -> None:
        """Execute turn for all agents (legacy method)."""
        await self._execute_all_agents_with_briefs(turn_result, turn_data)
    
    async def _execute_single_agent_with_brief(self, turn_result: Dict[str, Any], 
                                             agent_id: str, agent: Any,
                                             turn_data: Optional[Dict[str, Any]]) -> None:
        """Execute turn for a single agent with personalized brief and causal tracking."""
        try:
            # Get agent's personalized brief
            agent_brief = turn_result['agent_briefs'].get(agent_id, {})
            
            # Execute agent turn with brief
            agent_result = await self._execute_agent_turn_with_brief(agent, agent_brief, turn_data)
            turn_result['agent_results'][agent_id] = agent_result
            
            # Record causal events for narrative engine
            await self._record_causal_events(agent_id, agent_result, turn_result)
            
            # Collect changes and events
            self._collect_agent_changes(turn_result, agent_result)
            
        except Exception as e:
            self.logger.error(f"Agent {agent_id} turn failed: {e}")
            turn_result['agent_results'][agent_id] = {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_single_agent(self, turn_result: Dict[str, Any], 
                                  agent_id: str, agent: Any,
                                  turn_data: Optional[Dict[str, Any]]) -> None:
        """Execute turn for a single agent and collect results (legacy method)."""
        await self._execute_single_agent_with_brief(turn_result, agent_id, agent, turn_data)
    
    def _collect_agent_changes(self, turn_result: Dict[str, Any], 
                             agent_result: Dict[str, Any]) -> None:
        """Collect world state changes and narrative events from agent result."""
        if 'world_state_changes' in agent_result:
            turn_result['world_state_changes'].update(
                agent_result['world_state_changes']
            )
        
        if 'narrative_events' in agent_result:
            turn_result['narrative_events'].extend(
                agent_result['narrative_events']
            )
    
    async def _record_causal_events(self, agent_id: str, agent_result: Dict[str, Any], 
                                   turn_result: Dict[str, Any]) -> None:
        """Record agent actions as causal events in the emergent narrative engine."""
        try:
            if agent_result.get('success', False):
                # Create causal event from agent action
                event_data = {
                    'event_id': f"{agent_id}_turn_{self.current_turn_number}",
                    'agent_id': agent_id,
                    'turn_number': self.current_turn_number,
                    'action': agent_result.get('action_taken', 'observe'),
                    'world_state_changes': agent_result.get('world_state_changes', {}),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add event to causal graph
                await self.causal_graph.add_event(event_data)
                
                # Store in turn result for API access
                turn_result['causal_events'].append(event_data)
                
        except Exception as e:
            self.logger.error(f"Failed to record causal event for {agent_id}: {e}")
    
    async def _process_narrative_coherence(self, turn_result: Dict[str, Any]) -> None:
        """Process turn results through emergent narrative engine for coherence analysis."""
        try:
            self.logger.debug("Processing narrative coherence")
            
            # Analyze narrative coherence of the turn
            coherence_result = await self.emergent_narrative_engine.analyze_turn_coherence(
                turn_number=self.current_turn_number,
                agent_results=turn_result['agent_results'],
                causal_events=turn_result['causal_events']
            )
            
            turn_result['narrative_coherence'] = coherence_result
            
            # Generate predicted events based on causal relationships
            predictions = await self.emergent_narrative_engine.predict_next_events(
                current_causal_state=turn_result['causal_events']
            )
            
            turn_result['predicted_events'] = predictions
            
        except Exception as e:
            self.logger.error(f"Narrative coherence processing failed: {e}")
            turn_result['narrative_coherence'] = {'error': str(e)}
    
    def _finalize_enhanced_turn_result(self, turn_result: Dict[str, Any], 
                                     start_time: datetime) -> None:
        """Finalize turn result with enhanced metrics including subjective reality data."""
        execution_time = (datetime.now() - start_time).total_seconds()
        successful_agents = sum(1 for r in turn_result['agent_results'].values() 
                              if r.get('success', False))
        successful_briefs = sum(1 for b in turn_result['agent_briefs'].values() 
                              if 'error' not in b)
        
        # Enhanced metrics with subjective reality data
        turn_result['metrics'] = {
            'execution_time_seconds': execution_time,
            'agent_count': len(self.agent_manager.agents),
            'successful_agents': successful_agents,
            'successful_briefs': successful_briefs,
            'world_state_changes_count': len(turn_result['world_state_changes']),
            'narrative_events_count': len(turn_result['narrative_events']),
            'causal_events_count': len(turn_result['causal_events']),
            'turn_number': self.current_turn_number
        }
        
        # Subjective reality metrics
        turn_result['subjective_metrics'] = {
            'briefs_generated': len(turn_result['agent_briefs']),
            'brief_success_rate': successful_briefs / len(self.agent_manager.agents) if self.agent_manager.agents else 0,
            'causal_relationships_tracked': len(turn_result['causal_events']),
            'narrative_coherence_score': turn_result.get('narrative_coherence', {}).get('coherence_score', 0.0)
        }
        
        turn_result['success'] = successful_agents > 0
        
        self.logger.info(f"Turn #{self.current_turn_number} executed in {execution_time:.3f}s: "
                       f"{successful_agents}/{len(self.agent_manager.agents)} agents successful, "
                       f"{successful_briefs} briefs generated, "
                       f"{len(turn_result['causal_events'])} causal events tracked")
    
    def _finalize_turn_result(self, turn_result: Dict[str, Any], 
                            start_time: datetime) -> None:
        """Finalize turn result with metrics and success status (legacy method)."""
        self._finalize_enhanced_turn_result(turn_result, start_time)
    
    def _create_error_result(self, error: Exception, start_time: datetime) -> Dict[str, Any]:
        """Create error result for failed turn execution."""
        self.logger.error(f"Turn execution failed: {error}")
        return {
            'success': False,
            'error': str(error),
            'timestamp': start_time.isoformat(),
            'metrics': {'execution_time_seconds': (datetime.now() - start_time).total_seconds()}
        }
    
    async def _execute_agent_turn_with_brief(self, agent: Any, agent_brief: Dict[str, Any], 
                                           turn_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute turn for a single agent with personalized brief."""
        try:
            agent_id = getattr(agent, 'agent_id', 'unknown')
            
            # Enhanced agent turn execution with subjective reality brief
            if hasattr(agent, 'make_decision_with_brief'):
                # Agent supports subjective reality briefings
                result = await agent.make_decision_with_brief(agent_brief, turn_data)
            elif hasattr(agent, 'make_decision'):
                # Standard agent decision making
                result = await agent.make_decision(turn_data)
            else:
                # Fallback for agents without decision-making capability
                result = {
                    'action_taken': 'observe',
                    'reasoning': f"Agent {agent_id} observed their subjective reality",
                    'world_state_changes': {},
                    'narrative_events': [
                        f"Agent {agent_id} contemplated their understanding of the situation"
                    ],
                    'confidence': agent_brief.get('confidence_levels', {}).get('overall', 0.7)
                }
            
            # Ensure result has required fields
            return {
                'success': True,
                'agent_id': agent_id,
                'action_taken': result.get('action_taken', 'observe'),
                'reasoning': result.get('reasoning', 'No reasoning provided'),
                'world_state_changes': result.get('world_state_changes', {}),
                'narrative_events': result.get('narrative_events', []),
                'confidence': result.get('confidence', 0.5),
                'brief_used': agent_brief.get('brief_id', f"brief_{agent_id}_{self.current_turn_number}")
            }
            
        except Exception as e:
            return {
                'success': False,
                'agent_id': getattr(agent, 'agent_id', 'unknown'),
                'error': str(e)
            }
    
    async def _execute_agent_turn(self, agent: Any, turn_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute turn for a single agent (legacy method)."""
        # Generate minimal brief for legacy compatibility
        agent_id = getattr(agent, 'agent_id', 'unknown')
        minimal_brief = {
            'agent_id': agent_id,
            'turn_number': self.current_turn_number,
            'brief_id': f"legacy_brief_{agent_id}_{self.current_turn_number}"
        }
        
        return await self._execute_agent_turn_with_brief(agent, minimal_brief, turn_data)
    
    async def get_agent_turn_brief(self, agent_id: str, turn_number: Optional[int] = None, 
                                 world_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get personalized turn brief for a specific agent (API endpoint method)."""
        try:
            target_turn = turn_number or self.current_turn_number
            target_world_state = world_state or {}
            
            # Get agent
            if agent_id not in self.agent_manager.agents:
                return {
                    'success': False,
                    'error': f"Agent {agent_id} not found",
                    'agent_id': agent_id,
                    'turn_number': target_turn
                }
            
            agent = self.agent_manager.agents[agent_id]
            
            # Generate turn brief
            brief = await self.turn_brief_factory.generate_turn_brief(
                agent_id=agent_id,
                turn_number=target_turn,
                global_world_state=target_world_state,
                agent=agent
            )
            
            return {
                'success': True,
                'agent_id': agent_id,
                'turn_number': target_turn,
                'brief': brief
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get turn brief for agent {agent_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent_id': agent_id,
                'turn_number': turn_number or self.current_turn_number
            }
    
    async def get_all_agent_briefs(self, turn_number: Optional[int] = None, 
                                 world_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get personalized turn briefs for all agents (API endpoint method)."""
        try:
            target_turn = turn_number or self.current_turn_number
            target_world_state = world_state or {}
            
            briefs = {}
            errors = {}
            
            # Generate briefs for all agents
            for agent_id, agent in self.agent_manager.agents.items():
                try:
                    brief = await self.turn_brief_factory.generate_turn_brief(
                        agent_id=agent_id,
                        turn_number=target_turn,
                        global_world_state=target_world_state,
                        agent=agent
                    )
                    briefs[agent_id] = brief
                except Exception as e:
                    errors[agent_id] = str(e)
            
            return {
                'success': len(errors) == 0,
                'turn_number': target_turn,
                'agent_briefs': briefs,
                'errors': errors if errors else None,
                'agent_count': len(self.agent_manager.agents),
                'successful_briefs': len(briefs)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get all agent briefs: {e}")
            return {
                'success': False,
                'error': str(e),
                'turn_number': turn_number or self.current_turn_number
            }
    
    async def get_causal_graph_data(self) -> Dict[str, Any]:
        """Get current causal graph data (API endpoint method)."""
        try:
            return await self.emergent_narrative_engine.get_causal_graph_summary()
        except Exception as e:
            self.logger.error(f"Failed to get causal graph data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup turn engine resources including core engines."""
        self.logger.info("Cleaning up TurnExecutionEngine and core engines")
        
        # Cleanup core engines
        if hasattr(self.subjective_reality_engine, 'cleanup'):
            await self.subjective_reality_engine.cleanup()
        if hasattr(self.emergent_narrative_engine, 'cleanup'):
            await self.emergent_narrative_engine.cleanup()
            
        self.turn_metrics.clear()