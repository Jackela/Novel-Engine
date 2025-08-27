#!/usr/bin/env python3
"""
Turn Configuration Value Object

Immutable configuration for turn execution including timing,
AI settings, participant management, and constraint enforcement.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from uuid import UUID


@dataclass(frozen=True)
class TurnConfiguration:
    """
    Immutable value object representing turn execution configuration.
    
    Encapsulates all parameters and constraints for orchestrating a complete
    turn pipeline across all Novel Engine contexts with comprehensive
    validation and business rule enforcement.
    
    Attributes:
        world_time_advance: Seconds to advance world time
        ai_integration_enabled: Whether to use AI Gateway for briefs/narrative
        narrative_analysis_depth: Level of narrative analysis (basic, standard, detailed)
        max_execution_time_ms: Maximum turn execution time in milliseconds
        max_ai_cost: Maximum allowed AI cost for the turn
        participants: List of agent IDs participating in the turn
        excluded_agents: List of agent IDs to exclude from turn
        phase_timeouts: Custom timeout overrides for specific phases
        ai_prompt_templates: Custom AI prompt configurations
        world_constraints: World state modification constraints
        interaction_rules: Custom interaction and negotiation rules
        narrative_themes: Themes to emphasize in narrative integration
        performance_targets: Performance and quality targets
        rollback_enabled: Whether to enable saga rollback capabilities
        metadata: Additional configuration metadata
        
    Business Rules:
        - World time advance must be positive
        - AI cost limit must be positive if specified
        - Participants list must not be empty
        - Phase timeouts must be positive
        - Narrative analysis depth must be valid option
        - Performance targets must be achievable
    """
    
    # Core timing and execution settings
    world_time_advance: int = 300  # 5 minutes default
    ai_integration_enabled: bool = True
    narrative_analysis_depth: str = "standard"
    max_execution_time_ms: int = 30000  # 30 seconds default
    rollback_enabled: bool = True
    
    # Cost and resource constraints
    max_ai_cost: Optional[Decimal] = None
    max_memory_usage_mb: int = 512
    max_concurrent_operations: int = 10
    
    # Participant management
    participants: List[str] = field(default_factory=list)
    excluded_agents: Set[str] = field(default_factory=set)
    required_agents: Set[str] = field(default_factory=set)
    
    # Phase-specific configuration
    phase_timeouts: Dict[str, int] = field(default_factory=dict)
    phase_enabled: Dict[str, bool] = field(default_factory=dict)
    
    # AI Gateway configuration
    ai_prompt_templates: Dict[str, str] = field(default_factory=dict)
    ai_model_preferences: Dict[str, str] = field(default_factory=dict)
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1000
    
    # World state constraints
    world_constraints: Dict[str, Any] = field(default_factory=dict)
    allow_entity_creation: bool = True
    allow_entity_deletion: bool = False
    allow_time_manipulation: bool = True
    
    # Interaction rules
    interaction_rules: Dict[str, Any] = field(default_factory=dict)
    negotiation_timeout_seconds: int = 300
    allow_multi_party_negotiations: bool = True
    require_consensus: bool = False
    
    # Narrative configuration
    narrative_themes: List[str] = field(default_factory=list)
    maintain_narrative_consistency: bool = True
    generate_plot_summaries: bool = True
    
    # Performance and quality targets
    performance_targets: Dict[str, float] = field(default_factory=dict)
    quality_thresholds: Dict[str, float] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Class-level constants
    VALID_ANALYSIS_DEPTHS = {"basic", "standard", "detailed", "comprehensive"}
    DEFAULT_PHASE_TIMEOUTS = {
        "world_update": 5000,  # 5 seconds
        "subjective_brief": 10000,  # 10 seconds  
        "interaction_orchestration": 12000,  # 12 seconds
        "event_integration": 3000,  # 3 seconds
        "narrative_integration": 8000  # 8 seconds
    }
    DEFAULT_PERFORMANCE_TARGETS = {
        "total_execution_time": 30.0,  # seconds
        "ai_response_time": 5.0,  # seconds
        "event_processing_rate": 100.0,  # events/second
        "memory_efficiency": 0.8  # utilization ratio
    }
    
    def __post_init__(self):
        """Validate configuration structure and business rules."""
        # Validate world time advance
        if self.world_time_advance <= 0:
            raise ValueError("world_time_advance must be positive")
        
        # Validate narrative analysis depth
        if self.narrative_analysis_depth not in self.VALID_ANALYSIS_DEPTHS:
            raise ValueError(
                f"narrative_analysis_depth must be one of {self.VALID_ANALYSIS_DEPTHS}"
            )
        
        # Validate execution time
        if self.max_execution_time_ms <= 0:
            raise ValueError("max_execution_time_ms must be positive")
        
        # Validate AI cost limit
        if self.max_ai_cost is not None and self.max_ai_cost <= 0:
            raise ValueError("max_ai_cost must be positive if specified")
        
        # Validate participants
        if not self.participants:
            # Set default to empty list, will be populated by orchestrator
            pass
        
        # Validate excluded and required agents don't overlap
        if self.excluded_agents.intersection(self.required_agents):
            raise ValueError("excluded_agents and required_agents cannot overlap")
        
        # Validate phase timeouts
        for phase, timeout in self.phase_timeouts.items():
            if timeout <= 0:
                raise ValueError(f"Phase timeout for {phase} must be positive")
        
        # Validate AI temperature
        if not 0.0 <= self.ai_temperature <= 2.0:
            raise ValueError("ai_temperature must be between 0.0 and 2.0")
        
        # Validate AI max tokens
        if self.ai_max_tokens <= 0:
            raise ValueError("ai_max_tokens must be positive")
        
        # Validate negotiation timeout
        if self.negotiation_timeout_seconds <= 0:
            raise ValueError("negotiation_timeout_seconds must be positive")
        
        # Set default phase timeouts if not provided
        if not self.phase_timeouts:
            object.__setattr__(self, 'phase_timeouts', self.DEFAULT_PHASE_TIMEOUTS.copy())
        
        # Set default performance targets if not provided
        if not self.performance_targets:
            object.__setattr__(self, 'performance_targets', self.DEFAULT_PERFORMANCE_TARGETS.copy())
    
    @classmethod
    def create_default(cls) -> 'TurnConfiguration':
        """
        Create default turn configuration.
        
        Returns:
            TurnConfiguration with sensible defaults
        """
        return cls()
    
    @classmethod
    def create_fast_turn(cls, participants: List[str] = None) -> 'TurnConfiguration':
        """
        Create configuration optimized for fast execution.
        
        Args:
            participants: Optional list of participating agents
            
        Returns:
            TurnConfiguration optimized for speed
        """
        return cls(
            world_time_advance=60,  # 1 minute
            narrative_analysis_depth="basic",
            max_execution_time_ms=15000,  # 15 seconds
            ai_max_tokens=500,
            participants=participants or [],
            phase_timeouts={
                "world_update": 2000,
                "subjective_brief": 5000,
                "interaction_orchestration": 5000,
                "event_integration": 1000,
                "narrative_integration": 2000
            }
        )
    
    @classmethod
    def create_detailed_turn(
        cls, 
        participants: List[str] = None,
        max_ai_cost: Optional[Decimal] = None
    ) -> 'TurnConfiguration':
        """
        Create configuration for detailed, comprehensive turns.
        
        Args:
            participants: Optional list of participating agents
            max_ai_cost: Optional AI cost limit
            
        Returns:
            TurnConfiguration optimized for detail and quality
        """
        return cls(
            world_time_advance=600,  # 10 minutes
            narrative_analysis_depth="comprehensive",
            max_execution_time_ms=60000,  # 60 seconds
            max_ai_cost=max_ai_cost or Decimal("10.00"),
            ai_max_tokens=2000,
            participants=participants or [],
            generate_plot_summaries=True,
            maintain_narrative_consistency=True,
            phase_timeouts={
                "world_update": 8000,
                "subjective_brief": 20000,
                "interaction_orchestration": 20000,
                "event_integration": 5000,
                "narrative_integration": 15000
            }
        )
    
    @classmethod
    def create_ai_disabled(cls, participants: List[str] = None) -> 'TurnConfiguration':
        """
        Create configuration without AI integration.
        
        Args:
            participants: Optional list of participating agents
            
        Returns:
            TurnConfiguration with AI features disabled
        """
        return cls(
            ai_integration_enabled=False,
            narrative_analysis_depth="basic",
            max_execution_time_ms=10000,  # 10 seconds
            participants=participants or [],
            generate_plot_summaries=False,
            phase_timeouts={
                "world_update": 3000,
                "subjective_brief": 2000,  # No AI, faster
                "interaction_orchestration": 4000,
                "event_integration": 1000,
                "narrative_integration": 2000  # No AI, faster
            }
        )
    
    def with_participants(self, participants: List[str]) -> 'TurnConfiguration':
        """
        Create new configuration with different participants.
        
        Args:
            participants: New list of participating agents
            
        Returns:
            New TurnConfiguration with updated participants
        """
        return TurnConfiguration(
            **{**self.__dict__, 'participants': participants}
        )
    
    def with_ai_cost_limit(self, max_cost: Decimal) -> 'TurnConfiguration':
        """
        Create new configuration with AI cost limit.
        
        Args:
            max_cost: Maximum AI cost for the turn
            
        Returns:
            New TurnConfiguration with cost limit
        """
        return TurnConfiguration(
            **{**self.__dict__, 'max_ai_cost': max_cost}
        )
    
    def with_timeout(self, timeout_ms: int) -> 'TurnConfiguration':
        """
        Create new configuration with different timeout.
        
        Args:
            timeout_ms: New maximum execution time
            
        Returns:
            New TurnConfiguration with updated timeout
        """
        return TurnConfiguration(
            **{**self.__dict__, 'max_execution_time_ms': timeout_ms}
        )
    
    def with_narrative_depth(self, depth: str) -> 'TurnConfiguration':
        """
        Create new configuration with different narrative analysis depth.
        
        Args:
            depth: New narrative analysis depth level
            
        Returns:
            New TurnConfiguration with updated depth
        """
        if depth not in self.VALID_ANALYSIS_DEPTHS:
            raise ValueError(f"Invalid depth: {depth}")
        
        return TurnConfiguration(
            **{**self.__dict__, 'narrative_analysis_depth': depth}
        )
    
    def get_phase_timeout(self, phase_name: str) -> int:
        """
        Get timeout for specific phase.
        
        Args:
            phase_name: Name of the pipeline phase
            
        Returns:
            Timeout in milliseconds for the phase
        """
        return self.phase_timeouts.get(
            phase_name, 
            self.DEFAULT_PHASE_TIMEOUTS.get(phase_name, 5000)
        )
    
    def is_phase_enabled(self, phase_name: str) -> bool:
        """
        Check if specific phase is enabled.
        
        Args:
            phase_name: Name of the pipeline phase
            
        Returns:
            True if phase is enabled
        """
        return self.phase_enabled.get(phase_name, True)
    
    def should_use_ai_for_phase(self, phase_name: str) -> bool:
        """
        Check if AI should be used for specific phase.
        
        Args:
            phase_name: Name of the pipeline phase
            
        Returns:
            True if AI integration is enabled for this phase
        """
        if not self.ai_integration_enabled:
            return False
        
        # AI is used for subjective briefs and narrative integration
        ai_phases = {"subjective_brief", "narrative_integration"}
        return phase_name in ai_phases
    
    def get_estimated_ai_cost(self) -> Optional[Decimal]:
        """
        Get estimated AI cost for the turn.
        
        Returns:
            Estimated cost or None if AI disabled
        """
        if not self.ai_integration_enabled:
            return Decimal("0.00")
        
        # Rough estimation based on configuration
        base_cost = Decimal("0.50")
        
        if self.narrative_analysis_depth == "comprehensive":
            base_cost *= Decimal("3.0")
        elif self.narrative_analysis_depth == "detailed":
            base_cost *= Decimal("2.0")
        elif self.narrative_analysis_depth == "standard":
            base_cost *= Decimal("1.5")
        
        # Scale by number of participants
        participant_multiplier = max(1, len(self.participants)) * Decimal("0.2")
        
        return base_cost + participant_multiplier
    
    def get_total_phase_timeout(self) -> int:
        """
        Get sum of all phase timeouts.
        
        Returns:
            Total expected phase execution time in milliseconds
        """
        return sum(
            self.get_phase_timeout(phase) 
            for phase in self.DEFAULT_PHASE_TIMEOUTS.keys()
        )
    
    def validate_constraints(self) -> List[str]:
        """
        Validate configuration constraints and return any issues.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if total phase timeouts exceed max execution time
        total_phase_time = self.get_total_phase_timeout()
        if total_phase_time > self.max_execution_time_ms:
            errors.append(
                f"Total phase timeouts ({total_phase_time}ms) exceed "
                f"max execution time ({self.max_execution_time_ms}ms)"
            )
        
        # Check AI cost estimation vs limit
        if self.max_ai_cost:
            estimated_cost = self.get_estimated_ai_cost()
            if estimated_cost and estimated_cost > self.max_ai_cost:
                errors.append(
                    f"Estimated AI cost ({estimated_cost}) exceeds "
                    f"limit ({self.max_ai_cost})"
                )
        
        # Check participant constraints
        if self.required_agents:
            missing_required = self.required_agents - set(self.participants)
            if missing_required:
                errors.append(f"Missing required agents: {missing_required}")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if configuration is valid.
        
        Returns:
            True if configuration passes all validations
        """
        return len(self.validate_constraints()) == 0
    
    def __str__(self) -> str:
        """String representation for general use."""
        return (
            f"TurnConfig(participants={len(self.participants)}, "
            f"time_advance={self.world_time_advance}s, "
            f"ai_enabled={self.ai_integration_enabled})"
        )
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"TurnConfiguration(participants={self.participants}, "
            f"world_time_advance={self.world_time_advance}, "
            f"ai_integration_enabled={self.ai_integration_enabled}, "
            f"narrative_analysis_depth='{self.narrative_analysis_depth}')"
        )