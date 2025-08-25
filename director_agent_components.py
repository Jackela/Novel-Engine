#!/usr/bin/env python3
"""
DirectorAgent Component Decomposition
=====================================

Enterprise-grade modular decomposition of DirectorAgent using the Facade pattern.
This maintains backward compatibility while providing clean separation of concerns.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Protocol
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Import core dependencies
from src.persona_agent import PersonaAgent
from shared_types import CharacterAction
from src.event_bus import EventBus

logger = logging.getLogger(__name__)


# ========================================
# Core Interfaces & Data Models
# ========================================

@dataclass
class ComponentState:
    """Shared state container for all components."""
    is_initialized: bool = False
    last_error: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class DirectorComponent(ABC):
    """Base interface for all DirectorAgent components."""
    
    def __init__(self, event_bus: EventBus, state: ComponentState):
        self.event_bus = event_bus
        self.state = state
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the component. Returns True on success."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources and gracefully shutdown."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get component status and health information."""
        pass


# ========================================
# 1. Agent Lifecycle Manager
# ========================================

class IAgentLifecycleManager(Protocol):
    """Interface for agent lifecycle management."""
    
    def register_agent(self, agent: PersonaAgent) -> bool:
        """Register a new agent."""
        ...
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the simulation."""
        ...
    
    def get_agent_list(self) -> List[Dict[str, str]]:
        """Get list of registered agents."""
        ...
    
    def validate_agent_integration(self, agent: PersonaAgent) -> bool:
        """Validate agent can be integrated into simulation."""
        ...


class AgentLifecycleManager(DirectorComponent):
    """Manages the complete lifecycle of PersonaAgent instances."""
    
    def __init__(self, event_bus: EventBus, state: ComponentState):
        super().__init__(event_bus, state)
        self.registered_agents: Dict[str, PersonaAgent] = {}
        self.agent_metadata: Dict[str, Dict[str, Any]] = {}
        self.validation_rules: List[callable] = []
        
    async def initialize(self) -> bool:
        """Initialize agent lifecycle management."""
        try:
            # Setup default validation rules
            self.validation_rules = [
                self._validate_agent_character_name,
                self._validate_agent_has_required_attributes,
                self._validate_agent_not_already_registered
            ]
            
            self.logger.info("Agent Lifecycle Manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Agent Lifecycle Manager: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        try:
            for agent_id in list(self.registered_agents.keys()):
                await self._cleanup_agent(agent_id)
            
            self.registered_agents.clear()
            self.agent_metadata.clear()
            self.logger.info("Agent Lifecycle Manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def register_agent(self, agent: PersonaAgent) -> bool:
        """Register a PersonaAgent with comprehensive validation."""
        try:
            # Run validation rules
            if not self.validate_agent_integration(agent):
                return False
            
            agent_id = agent.character_name
            self.registered_agents[agent_id] = agent
            
            # Store metadata
            self.agent_metadata[agent_id] = {
                "registered_at": datetime.now().isoformat(),
                "character_name": agent.character_name,
                "agent_type": type(agent).__name__,
                "status": "active"
            }
            
            # Emit registration event
            self.event_bus.emit("AGENT_REGISTERED", {
                "agent_id": agent_id,
                "metadata": self.agent_metadata[agent_id]
            })
            
            self.logger.info(f"✅ Successfully registered agent: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to register agent {getattr(agent, 'character_name', 'unknown')}: {e}")
            return False
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the simulation."""
        try:
            if agent_id not in self.registered_agents:
                self.logger.warning(f"⚠️ Agent {agent_id} not found for removal")
                return False
            
            # Cleanup agent resources
            agent = self.registered_agents[agent_id]
            # Potentially call agent cleanup methods here
            
            # Remove from registries
            del self.registered_agents[agent_id]
            del self.agent_metadata[agent_id]
            
            # Emit removal event
            self.event_bus.emit("AGENT_REMOVED", {"agent_id": agent_id})
            
            self.logger.info(f"✅ Successfully removed agent: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to remove agent {agent_id}: {e}")
            return False
    
    def get_agent_list(self) -> List[Dict[str, str]]:
        """Get comprehensive list of registered agents."""
        try:
            return [
                {
                    "agent_id": agent_id,
                    "character_name": metadata["character_name"],
                    "status": metadata["status"],
                    "registered_at": metadata["registered_at"]
                }
                for agent_id, metadata in self.agent_metadata.items()
            ]
        except Exception as e:
            self.logger.error(f"Failed to get agent list: {e}")
            return []
    
    def validate_agent_integration(self, agent: PersonaAgent) -> bool:
        """Validate agent can be integrated using registered rules."""
        try:
            for rule in self.validation_rules:
                if not rule(agent):
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Agent validation failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get lifecycle manager status."""
        return {
            "total_agents": len(self.registered_agents),
            "active_agents": len([m for m in self.agent_metadata.values() if m["status"] == "active"]),
            "validation_rules": len(self.validation_rules),
            "is_healthy": len(self.registered_agents) >= 0
        }
    
    # Private validation methods
    def _validate_agent_character_name(self, agent: PersonaAgent) -> bool:
        """Validate agent has a character name."""
        return hasattr(agent, 'character_name') and agent.character_name
    
    def _validate_agent_has_required_attributes(self, agent: PersonaAgent) -> bool:
        """Validate agent has required attributes."""
        required_attrs = ['character_name']
        return all(hasattr(agent, attr) for attr in required_attrs)
    
    def _validate_agent_not_already_registered(self, agent: PersonaAgent) -> bool:
        """Validate agent is not already registered."""
        return agent.character_name not in self.registered_agents
    
    async def _cleanup_agent(self, agent_id: str) -> None:
        """Clean up specific agent resources."""
        try:
            # Add any agent-specific cleanup logic here
            pass
        except Exception as e:
            self.logger.error(f"Failed to cleanup agent {agent_id}: {e}")


# ========================================
# 2. Turn Execution Engine  
# ========================================

class ITurnExecutionEngine(Protocol):
    """Interface for turn execution management."""
    
    def run_turn(self) -> Dict[str, Any]:
        """Execute a single simulation turn."""
        ...
    
    def prepare_world_state_for_turn(self) -> Dict[str, Any]:
        """Prepare world state for turn execution."""
        ...
    
    def handle_agent_action(self, agent: PersonaAgent, action: Optional[CharacterAction]) -> None:
        """Handle an agent's action during a turn."""
        ...


class TurnExecutionEngine(DirectorComponent):
    """Manages turn-based execution and agent coordination."""
    
    def __init__(self, event_bus: EventBus, state: ComponentState, 
                 agent_manager: IAgentLifecycleManager,
                 world_state_manager: 'IWorldStateManager'):
        super().__init__(event_bus, state)
        self.agent_manager = agent_manager
        self.world_state_manager = world_state_manager
        
        # Turn execution state
        self.turn_number = 0
        self.turn_history: List[Dict[str, Any]] = []
        self.current_turn_data: Optional[Dict[str, Any]] = None
        
    async def initialize(self) -> bool:
        """Initialize turn execution engine."""
        try:
            self.turn_number = 0
            self.turn_history = []
            
            # Subscribe to relevant events
            self.event_bus.subscribe("AGENT_ACTION_COMPLETED", self._on_agent_action_completed)
            self.event_bus.subscribe("TURN_INTERRUPT_REQUEST", self._on_turn_interrupt)
            
            self.logger.info("Turn Execution Engine initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Turn Execution Engine: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up turn execution resources."""
        try:
            # Store final turn history if needed
            if self.turn_history:
                await self._store_final_history()
            
            self.turn_history.clear()
            self.current_turn_data = None
            self.logger.info("Turn Execution Engine cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def run_turn(self) -> Dict[str, Any]:
        """Execute a single simulation turn with comprehensive orchestration."""
        try:
            self.turn_number += 1
            turn_start_time = datetime.now()
            
            self.logger.info(f"🎬 Starting Turn {self.turn_number}")
            
            # Phase 1: Prepare turn context
            world_state = self.prepare_world_state_for_turn()
            
            # Phase 2: Emit turn start event
            turn_context = {
                "turn_number": self.turn_number,
                "world_state": world_state,
                "timestamp": turn_start_time.isoformat()
            }
            
            self.current_turn_data = turn_context
            self.event_bus.emit("TURN_START", turn_context)
            
            # Phase 3: Collect agent actions (handled via event callbacks)
            agent_actions = self._collect_agent_actions()
            
            # Phase 4: Process turn results
            turn_result = self._process_turn_results(agent_actions, turn_start_time)
            
            # Phase 5: Store turn in history
            self._store_turn_in_history(turn_result)
            
            self.logger.info(f"✅ Turn {self.turn_number} completed successfully")
            return turn_result
            
        except Exception as e:
            self.logger.error(f"❌ Turn {self.turn_number} failed: {e}")
            return {
                "status": "error",
                "turn_number": self.turn_number,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def prepare_world_state_for_turn(self) -> Dict[str, Any]:
        """Prepare comprehensive world state for turn execution."""
        try:
            base_world_state = {
                "turn_number": self.turn_number,
                "timestamp": datetime.now().isoformat(),
                "registered_agents": len(self.agent_manager.get_agent_list()),
            }
            
            # Get world state from world state manager
            if hasattr(self.world_state_manager, 'get_world_state_summary'):
                world_summary = self.world_state_manager.get_world_state_summary()
                base_world_state.update(world_summary)
            
            return base_world_state
            
        except Exception as e:
            self.logger.error(f"Failed to prepare world state: {e}")
            return {"turn_number": self.turn_number, "error": str(e)}
    
    def handle_agent_action(self, agent: PersonaAgent, action: Optional[CharacterAction]) -> None:
        """Handle and process an agent's action during a turn."""
        try:
            if action:
                self.logger.info(f"🎯 Processing action from {agent.character_name}")
                
                # Emit action event for other components to process
                self.event_bus.emit("AGENT_ACTION", {
                    "agent_id": agent.character_name,
                    "action": action,
                    "turn_number": self.turn_number
                })
            else:
                self.logger.warning(f"⚠️ No action received from {agent.character_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to handle action from {getattr(agent, 'character_name', 'unknown')}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get turn execution engine status."""
        return {
            "current_turn": self.turn_number,
            "total_turns_executed": len(self.turn_history),
            "is_turn_active": self.current_turn_data is not None,
            "last_turn_success": len(self.turn_history) > 0 and 
                               self.turn_history[-1].get("status") != "error"
        }
    
    # Private methods
    def _collect_agent_actions(self) -> List[Dict[str, Any]]:
        """Collect actions from all registered agents."""
        actions = []
        # This would be implemented based on specific agent interaction patterns
        # For now, return empty list as placeholder
        return actions
    
    def _process_turn_results(self, agent_actions: List[Dict[str, Any]], 
                            turn_start_time: datetime) -> Dict[str, Any]:
        """Process and compile turn results."""
        execution_time = (datetime.now() - turn_start_time).total_seconds()
        
        return {
            "status": "completed",
            "turn_number": self.turn_number,
            "execution_time": execution_time,
            "actions_processed": len(agent_actions),
            "timestamp": datetime.now().isoformat()
        }
    
    def _store_turn_in_history(self, turn_result: Dict[str, Any]) -> None:
        """Store turn result in history."""
        try:
            self.turn_history.append(turn_result)
            
            # Limit history size to prevent memory issues
            max_history_size = 1000
            if len(self.turn_history) > max_history_size:
                self.turn_history = self.turn_history[-max_history_size:]
                
        except Exception as e:
            self.logger.error(f"Failed to store turn in history: {e}")
    
    async def _store_final_history(self) -> None:
        """Store final turn history for persistence."""
        try:
            # Implementation would depend on specific storage requirements
            self.logger.info(f"Storing final turn history with {len(self.turn_history)} turns")
        except Exception as e:
            self.logger.error(f"Failed to store final history: {e}")
    
    def _on_agent_action_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle agent action completion events."""
        try:
            agent_id = event_data.get("agent_id")
            self.logger.debug(f"Agent {agent_id} completed action")
        except Exception as e:
            self.logger.error(f"Error handling agent action completion: {e}")
    
    def _on_turn_interrupt(self, event_data: Dict[str, Any]) -> None:
        """Handle turn interruption requests."""
        try:
            reason = event_data.get("reason", "unknown")
            self.logger.warning(f"Turn interrupt requested: {reason}")
            # Implement turn interruption logic
        except Exception as e:
            self.logger.error(f"Error handling turn interrupt: {e}")


# ========================================
# 3. World State Manager
# ========================================

class IWorldStateManager(Protocol):
    """Interface for world state management."""
    
    def load_world_state(self, file_path: Optional[str] = None) -> bool:
        """Load world state from file."""
        ...
    
    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """Save current world state to file."""
        ...
    
    def get_world_state_summary(self) -> Dict[str, Any]:
        """Get summarized world state."""
        ...
    
    def update_world_state(self, updates: Dict[str, Any]) -> bool:
        """Update world state with new data."""
        ...


class WorldStateManager(DirectorComponent):
    """Manages persistent world state and environmental data."""
    
    def __init__(self, event_bus: EventBus, state: ComponentState, 
                 world_state_file_path: Optional[str] = None):
        super().__init__(event_bus, state)
        self.world_state_file_path = world_state_file_path
        self.world_state_data: Dict[str, Any] = {}
        self.state_backup_interval = 5  # Backup every N updates
        self.update_counter = 0
        
    async def initialize(self) -> bool:
        """Initialize world state management."""
        try:
            if self.world_state_file_path and os.path.exists(self.world_state_file_path):
                self.load_world_state(self.world_state_file_path)
            else:
                self._initialize_default_world_state()
            
            # Subscribe to world state change events
            self.event_bus.subscribe("WORLD_STATE_UPDATE", self._on_world_state_update)
            
            self.logger.info("World State Manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize World State Manager: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up world state resources."""
        try:
            # Save final state
            if self.world_state_data:
                self.save_world_state()
            
            self.world_state_data.clear()
            self.logger.info("World State Manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def load_world_state(self, file_path: Optional[str] = None) -> bool:
        """Load world state from JSON file."""
        try:
            path = file_path or self.world_state_file_path
            if not path or not os.path.exists(path):
                self.logger.warning("World state file not found, using defaults")
                self._initialize_default_world_state()
                return True
            
            with open(path, 'r', encoding='utf-8') as f:
                self.world_state_data = json.load(f)
            
            # Validate loaded data
            self._validate_world_state_data()
            
            self.logger.info(f"✅ Loaded world state from {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load world state: {e}")
            self._initialize_default_world_state()
            return False
    
    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """Save current world state to JSON file."""
        try:
            path = file_path or self.world_state_file_path
            if not path:
                self.logger.error("No file path provided for world state save")
                return False
            
            # Add metadata
            save_data = {
                **self.world_state_data,
                "_metadata": {
                    "last_saved": datetime.now().isoformat(),
                    "version": "1.0",
                    "update_count": self.update_counter
                }
            }
            
            # Create backup if file exists
            if os.path.exists(path):
                backup_path = f"{path}.backup"
                os.rename(path, backup_path)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Saved world state to {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save world state: {e}")
            return False
    
    def get_world_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive world state summary."""
        try:
            return {
                "environment": self.world_state_data.get("environment", {}),
                "locations": len(self.world_state_data.get("locations", {})),
                "entities": len(self.world_state_data.get("entities", {})),
                "last_updated": self.world_state_data.get("_metadata", {}).get("last_saved"),
                "state_health": "healthy" if self.world_state_data else "uninitialized"
            }
        except Exception as e:
            self.logger.error(f"Failed to get world state summary: {e}")
            return {"error": str(e)}
    
    def update_world_state(self, updates: Dict[str, Any]) -> bool:
        """Update world state with new data."""
        try:
            self.world_state_data.update(updates)
            self.update_counter += 1
            
            # Periodic backup
            if self.update_counter % self.state_backup_interval == 0:
                self.save_world_state()
            
            # Emit update event
            self.event_bus.emit("WORLD_STATE_CHANGED", {
                "updates": updates,
                "update_count": self.update_counter
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update world state: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get world state manager status."""
        return {
            "state_loaded": bool(self.world_state_data),
            "update_count": self.update_counter,
            "data_size": len(str(self.world_state_data)),
            "has_backup": os.path.exists(f"{self.world_state_file_path}.backup") if self.world_state_file_path else False
        }
    
    # Private methods
    def _initialize_default_world_state(self) -> None:
        """Initialize default world state structure."""
        self.world_state_data = {
            "environment": {
                "time": datetime.now().isoformat(),
                "weather": "clear",
                "visibility": "normal"
            },
            "locations": {
                "default_location": {
                    "name": "Default Location",
                    "description": "A generic simulation environment",
                    "coordinates": {"x": 0, "y": 0, "z": 0}
                }
            },
            "entities": {},
            "global_flags": {},
            "_metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        self.logger.info("Initialized default world state")
    
    def _validate_world_state_data(self) -> None:
        """Validate world state data integrity."""
        required_sections = ["environment", "locations", "entities"]
        
        for section in required_sections:
            if section not in self.world_state_data:
                self.world_state_data[section] = {}
                self.logger.warning(f"Added missing world state section: {section}")
    
    def _on_world_state_update(self, event_data: Dict[str, Any]) -> None:
        """Handle world state update events."""
        try:
            updates = event_data.get("updates", {})
            if updates:
                self.update_world_state(updates)
        except Exception as e:
            self.logger.error(f"Error handling world state update event: {e}")


# ========================================
# Facade Pattern DirectorAgent
# ========================================

class DirectorAgentFacade:
    """
    Enterprise-grade DirectorAgent using Facade pattern for clean architecture.
    
    Maintains full backward compatibility while providing modular, testable components.
    Each component can be independently developed, tested, and maintained.
    """
    
    def __init__(self, event_bus: EventBus, world_state_file_path: Optional[str] = None, 
                 campaign_log_path: Optional[str] = None, campaign_brief_path: Optional[str] = None):
        """Initialize DirectorAgent with modular component architecture."""
        
        self.event_bus = event_bus
        self.shared_state = ComponentState()
        
        # Initialize core components
        self.agent_lifecycle_manager = AgentLifecycleManager(event_bus, self.shared_state)
        self.world_state_manager = WorldStateManager(event_bus, self.shared_state, world_state_file_path)
        self.turn_execution_engine = TurnExecutionEngine(
            event_bus, self.shared_state, 
            self.agent_lifecycle_manager, self.world_state_manager
        )
        
        # Component registry for management
        self.components: Dict[str, DirectorComponent] = {
            "agent_lifecycle": self.agent_lifecycle_manager,
            "world_state": self.world_state_manager, 
            "turn_execution": self.turn_execution_engine
        }
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Backward compatibility state
        self.world_state_file_path = world_state_file_path
        self.campaign_log_path = campaign_log_path
        self.campaign_brief_path = campaign_brief_path
        
        # Initialize synchronously for backward compatibility
        self._initialize_synchronous()
    
    def _initialize_synchronous(self) -> None:
        """Synchronous initialization for backward compatibility."""
        import asyncio
        
        try:
            # Run async initialization
            if asyncio.get_event_loop().is_running():
                # If already in async context, schedule for later
                asyncio.create_task(self._initialize_async())
            else:
                # Run in new event loop
                asyncio.run(self._initialize_async())
        except Exception as e:
            self.logger.error(f"Synchronous initialization failed: {e}")
    
    async def _initialize_async(self) -> bool:
        """Initialize all components asynchronously."""
        try:
            initialization_results = {}
            
            for name, component in self.components.items():
                result = await component.initialize()
                initialization_results[name] = result
                
                if not result:
                    self.logger.error(f"Component {name} failed to initialize")
                    return False
            
            self.shared_state.is_initialized = True
            self.logger.info("✅ DirectorAgent Facade fully initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ DirectorAgent Facade initialization failed: {e}")
            self.shared_state.last_error = str(e)
            return False
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        try:
            for name, component in reversed(list(self.components.items())):
                await component.cleanup()
                self.logger.info(f"Component {name} cleaned up")
            
            self.shared_state.is_initialized = False
            self.logger.info("DirectorAgent Facade shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    # ========================================
    # Backward Compatibility Interface
    # ========================================
    
    def register_agent(self, agent: PersonaAgent) -> bool:
        """Register a PersonaAgent (backward compatible)."""
        return self.agent_lifecycle_manager.register_agent(agent)
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent (backward compatible)."""
        return self.agent_lifecycle_manager.remove_agent(agent_id)
    
    def run_turn(self) -> Dict[str, Any]:
        """Execute a simulation turn (backward compatible)."""
        return self.turn_execution_engine.run_turn()
    
    def get_agent_list(self) -> List[Dict[str, str]]:
        """Get list of agents (backward compatible)."""
        return self.agent_lifecycle_manager.get_agent_list()
    
    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """Save world state (backward compatible)."""
        return self.world_state_manager.save_world_state(file_path)
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get comprehensive simulation status."""
        try:
            status = {
                "is_initialized": self.shared_state.is_initialized,
                "last_error": self.shared_state.last_error,
                "components": {}
            }
            
            for name, component in self.components.items():
                status["components"][name] = component.get_status()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get simulation status: {e}")
            return {"error": str(e)}
    
    # ========================================
    # Component Access Methods
    # ========================================
    
    @property
    def agents(self) -> IAgentLifecycleManager:
        """Access to agent lifecycle management."""
        return self.agent_lifecycle_manager
    
    @property  
    def world_state(self) -> IWorldStateManager:
        """Access to world state management."""
        return self.world_state_manager
    
    @property
    def turns(self) -> ITurnExecutionEngine:
        """Access to turn execution."""
        return self.turn_execution_engine


# ========================================
# Factory Functions
# ========================================

def create_director_agent(event_bus: EventBus, world_state_file_path: Optional[str] = None,
                         campaign_log_path: Optional[str] = None, campaign_brief_path: Optional[str] = None) -> DirectorAgentFacade:
    """
    Factory function to create a new DirectorAgent with modular architecture.
    
    Maintains backward compatibility while providing enterprise-grade modularity.
    """
    return DirectorAgentFacade(event_bus, world_state_file_path, campaign_log_path, campaign_brief_path)


def create_director_with_custom_components(event_bus: EventBus, 
                                         agent_manager: Optional[IAgentLifecycleManager] = None,
                                         world_manager: Optional[IWorldStateManager] = None,
                                         turn_engine: Optional[ITurnExecutionEngine] = None) -> DirectorAgentFacade:
    """
    Factory function for creating DirectorAgent with custom component implementations.
    
    Allows for dependency injection and testing with mock components.
    """
    facade = DirectorAgentFacade(event_bus)
    
    # Override components if provided
    if agent_manager:
        facade.agent_lifecycle_manager = agent_manager
        facade.components["agent_lifecycle"] = agent_manager
    
    if world_manager:
        facade.world_state_manager = world_manager
        facade.components["world_state"] = world_manager
        
    if turn_engine:
        facade.turn_execution_engine = turn_engine
        facade.components["turn_execution"] = turn_engine
    
    return facade


if __name__ == "__main__":
    # Example usage
    from src.event_bus import EventBus
    
    event_bus = EventBus()
    director = create_director_agent(event_bus)
    
    print("DirectorAgent Facade created successfully!")
    print("Status:", director.get_simulation_status())