"""
Orchestration Context - M9 Turn Pipeline Implementation
========================================================

This bounded context handles comprehensive turn orchestration across all Novel Engine
contexts, implementing a sophisticated pipeline that coordinates:

1. World State Updates - Entity positions, environment changes, time progression
2. Subjective Brief Generation - Agent perception updates using AI Gateway
3. Interaction Orchestration - Agent decision-making and negotiation processes
4. Event Integration - Writing results back to World state with consistency
5. Narrative Integration - Story coherence using AI Gateway and causal analysis

M9 Implementation Features:
- Complete Turn Pipeline with 5-phase orchestration
- Saga Pattern with compensation logic for reliability
- Event-driven coordination using enterprise event bus
- AI Gateway integration for subjective briefs and narrative coherence
- REST API endpoint (POST /v1/turns:run) for external orchestration
- Cross-context state consistency with rollback capabilities
- Performance monitoring and comprehensive error handling

Architecture follows Domain-Driven Design patterns with:
- Domain Layer: Turn abstractions, pipeline steps, saga coordination
- Infrastructure Layer: Event bus integration, persistence, API infrastructure
- Application Layer: TurnOrchestrator service with complete workflow management
"""

__version__ = "1.0.0"
__context_name__ = "orchestration"
__description__ = "M9 Turn Pipeline Orchestration with Saga Patterns"
__author__ = "Novel Engine Orchestration Team"

# Core exports will be added as implementation progresses
__all__ = []
