# M9 Orchestration Architecture - Turn Pipeline System

## Executive Summary

The M9 Orchestration system implements a sophisticated **5-phase turn pipeline** that coordinates across all Novel Engine contexts using **Saga pattern reliability** and **event-driven architecture**. The system provides a single REST API endpoint (`POST /v1/turns:run`) that orchestrates complete game turns with comprehensive error handling and compensation logic.

## System Architecture

### Turn Pipeline Phases

```
Phase 1: World State Update
├── Update entity positions and states
├── Advance world time and environmental factors
├── Trigger world state events
└── Checkpoint: World consistency verified

Phase 2: Subjective Brief Generation
├── Query updated world state for each agent
├── Generate perception summaries using AI Gateway
├── Update agent knowledge and awareness
└── Checkpoint: All agent briefs generated

Phase 3: Interaction Orchestration  
├── Process agent decision-making
├── Orchestrate negotiations and agreements
├── Resolve conflicts and multi-party interactions
└── Checkpoint: All interactions resolved

Phase 4: Event Integration
├── Collect all generated events from phases 1-3
├── Write event results back to World state
├── Update entity relationships and positions
└── Checkpoint: World state consistency maintained

Phase 5: Narrative Integration
├── Analyze event chains for narrative coherence
├── Generate story integration using AI Gateway
├── Update narrative causality and plot progression
└── Checkpoint: Narrative consistency achieved
```

### Saga Pattern Implementation

**Reliability Approach**: Each pipeline phase implements compensation logic for rollback capability.

**Saga Orchestrator**: Coordinates phase execution with automatic compensation on failure.

**Compensation Matrix**:
- **Phase 1 Failure** → No compensation needed (rollback world checkpoint)
- **Phase 2 Failure** → Rollback world state changes
- **Phase 3 Failure** → Rollback world state + clear agent briefs
- **Phase 4 Failure** → Rollback world state + clear briefs + cancel interactions  
- **Phase 5 Failure** → Full pipeline rollback to previous turn state

### Event-Driven Coordination

**Enterprise Event Bus Integration**: Leverages existing Redis-backed event infrastructure for:
- **Phase coordination**: Each phase publishes events for next phase
- **Cross-context communication**: Events flow between World, Subjective, Interaction, Narrative
- **State synchronization**: Distributed state consistency across contexts
- **Audit trails**: Complete event sourcing for turn replay and analysis

**Event Flow Pattern**:
```
TurnInitiated → WorldStateUpdateRequested → WorldStateUpdated
             → SubjectiveBriefsRequested → SubjectiveBriefsGenerated  
             → InteractionOrchestrationRequested → InteractionsCompleted
             → EventIntegrationRequested → EventsIntegrated
             → NarrativeIntegrationRequested → NarrativeIntegrated
             → TurnCompleted
```

## Component Architecture

### Domain Layer

**Turn Aggregate Root** (`Turn`):
- **Turn Identity**: Unique turn ID with sequence number
- **Turn State**: Current phase, status, and progress tracking
- **Pipeline Coordination**: Phase management with saga state
- **Event History**: Complete audit trail of turn progression
- **Rollback Capability**: Compensation logic for each phase

**Pipeline Step Entities**:
- `WorldUpdateStep`: Coordinates world state modifications
- `SubjectiveBriefStep`: Orchestrates AI-generated perception summaries
- `InteractionStep`: Manages agent decision-making and negotiations
- `EventIntegrationStep`: Integrates events back into world state
- `NarrativeStep`: Coordinates story integration and causality analysis

**Value Objects**:
- `TurnId`: Immutable turn identifier with validation
- `PhaseStatus`: Enumeration of phase states (PENDING, RUNNING, COMPLETED, FAILED, COMPENSATING)
- `TurnConfiguration`: Turn parameters and settings
- `PipelineResult`: Comprehensive result tracking with metrics
- `CompensationAction`: Rollback instructions for each phase

**Domain Events**:
- `TurnInitiated`: Turn startup with configuration
- `PhaseStarted/PhaseCompleted`: Phase lifecycle events
- `PhaseCompensationTriggered`: Rollback initiation
- `TurnCompleted/TurnFailed`: Turn outcome events

### Application Layer

**TurnOrchestrator Service**:
- **Pipeline Execution**: Coordinates all 5 phases with error handling
- **Saga Management**: Implements compensation logic and rollback procedures
- **Cross-Context Integration**: Orchestrates calls to all context application services
- **Performance Monitoring**: Metrics collection and health monitoring
- **API Orchestration**: Handles REST requests and response formatting

**Application Services**:
- `ExecuteTurnUseCase`: Main turn execution workflow
- `CompensateTurnUseCase`: Rollback and recovery procedures
- `TurnQueryService`: Turn status and history queries
- `TurnConfigurationService`: Turn parameter management

### Infrastructure Layer

**Event Bus Integration**:
- `TurnEventPublisher`: Publishes turn lifecycle events
- `TurnEventSubscriber`: Subscribes to cross-context events
- `EventSagaCoordinator`: Manages distributed saga state

**Persistence Layer**:
- `TurnRepository`: Turn state persistence and recovery
- `TurnEventStore`: Event sourcing with replay capability
- `SagaStateRepository`: Saga coordination state management

**API Layer**:
- `TurnRouter`: FastAPI router with `/v1/turns:run` endpoint
- `TurnRequestHandler`: Request validation and response formatting
- `TurnStatusEndpoints`: Turn monitoring and health check endpoints

## Integration Points

### Context Application Service Integration

**World Context Integration**:
- Uses `UpdateWorldStateUC` for Phase 1 world state updates
- Subscribes to `WorldStateChanged` events for coordination
- Implements rollback through world state checkpointing

**Subjective Context Integration**:
- Uses `SubjectiveApplicationService` for perception management
- Integrates with AI Gateway for subjective brief generation
- Manages agent knowledge state with consistency guarantees

**Interaction Context Integration**:
- Uses `InteractionApplicationService` for negotiation orchestration
- Coordinates multi-party decision-making processes  
- Handles conflict resolution and consensus building

**Narrative Context Integration**:
- Uses `NarrativeArcApplicationService` for story progression
- Integrates with AI Gateway for narrative coherence analysis
- Maintains causal consistency across story elements

**AI Gateway Integration**:
- Uses `ExecuteLLMService` for all AI operations
- Implements prompt templates for subjective briefs and narrative analysis
- Manages AI costs and performance optimization

### API Endpoint Design

**POST /v1/turns:run**
```json
{
  "turn_configuration": {
    "turn_id": "optional-custom-id",
    "world_time_advance": 300,
    "ai_integration_enabled": true,
    "narrative_analysis_depth": "standard"
  },
  "participants": ["agent_1", "agent_2", "agent_3"],
  "constraints": {
    "max_execution_time": 30000,
    "max_ai_cost": "5.00"
  }
}
```

**Response Format**:
```json
{
  "turn_id": "turn_12345",
  "status": "completed",
  "execution_time_ms": 15420,
  "phases": [
    {
      "phase": "world_update",
      "status": "completed", 
      "duration_ms": 1200,
      "events_generated": 15
    }
  ],
  "ai_usage": {
    "total_cost": "2.45",
    "requests_made": 12,
    "tokens_consumed": 4500
  },
  "saga_state": {
    "compensation_points": 5,
    "rollback_available": true
  }
}
```

## Performance and Scalability

### Performance Targets
- **Turn Execution**: <30 seconds for standard turns
- **Phase Transition**: <2 seconds between phases
- **Event Processing**: <500ms for event propagation
- **API Response**: <1 second for status queries
- **Rollback Time**: <10 seconds for full compensation

### Scalability Design
- **Horizontal Scaling**: Event bus supports distributed processing
- **Resource Management**: AI Gateway provides cost and rate limiting
- **Database Optimization**: Event sourcing with efficient projections
- **Caching Strategy**: Turn state caching for repeated queries
- **Circuit Breaker**: Protection against cascading failures

## Quality Attributes

### Reliability
- **Saga Pattern**: Guaranteed consistency with compensation logic
- **Event Sourcing**: Complete audit trail and replay capability
- **Circuit Breaker**: Automatic failure detection and recovery
- **Health Monitoring**: Continuous system health assessment

### Performance
- **Async Processing**: Non-blocking pipeline execution
- **Resource Optimization**: AI Gateway cost management
- **Event Bus Efficiency**: Redis-backed high-performance messaging
- **Database Optimization**: Efficient persistence patterns

### Maintainability  
- **Clean Architecture**: Clear separation of concerns
- **Domain-Driven Design**: Business logic encapsulation
- **Comprehensive Testing**: Unit, integration, and end-to-end validation
- **Monitoring Integration**: Complete observability and debugging

## Implementation Strategy

### Wave 2: Core Domain Implementation
- Turn aggregate and entities
- Value objects and domain events
- Saga coordination patterns
- Domain services for pipeline management

### Wave 3: Pipeline Step Implementation  
- World state update step
- Subjective brief generation step
- Interaction orchestration step
- Event integration step
- Narrative integration step

### Wave 4: Application Service & API
- TurnOrchestrator service implementation
- REST API endpoint creation
- Request/response handling
- Error handling and compensation

### Wave 5: Integration & Validation
- End-to-end pipeline testing
- Saga reliability validation
- Performance benchmarking
- Cross-context integration verification

This architecture provides a robust, scalable, and maintainable foundation for the M9 Orchestration milestone while leveraging the sophisticated existing Novel Engine infrastructure.