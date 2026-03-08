# Orchestration Context

## Overview
The Orchestration Context coordinates complex multi-phase operations across all Novel Engine contexts. It implements the saga pattern for distributed transaction management, ensuring consistency during turn-based world simulation.

This context manages the complete turn lifecycle: world updates, perception, decision-making, action resolution, and narrative generation. It provides reliability through compensation actions, performance tracking, and comprehensive audit trails.

## Domain

### Aggregates
- **Turn**: Root aggregate for turn execution
  - Complete lifecycle management: created → planning → executing → completed/failed
  - Phase coordination across all contexts
  - Saga compensation for failure recovery
  - Performance metrics tracking
  - Audit trail maintenance

### Entities
- **None**: Turn aggregate encapsulates all execution state.

### Value Objects
- **TurnId**: Unique turn identifier with campaign association
- **TurnConfiguration**: Execution parameters
  - Participants, world time advancement
  - AI integration settings, timeout configuration
  - Rollback/c compensation enabled flag
  
- **PhaseStatus**: Individual phase execution state
  - **PhaseStatusEnum**: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
  - Timing and event tracking
  
- **PhaseResult**: Completed phase outcome
  - Success/failure status, events processed/generated
  - Performance metrics, AI usage
  
- **PipelineResult**: Complete turn outcome
  - Aggregate of all phase results
  - Total execution time, completion percentage
  
- **CompensationAction**: Saga rollback operation
  - **CompensationType**: REVERT_STATE, NOTIFY_FAILURE, LOG_ERROR
  - Execution tracking and cost
  
- **TurnState**: Aggregate state enumeration
  - CREATED, PLANNING, EXECUTING, COMPENSATING, COMPLETED, FAILED, CANCELLED

### Domain Events
- **TurnCreated**: Turn initialized
  - Contains: turn_id, configuration, participants
  
- **TurnPlanningStarted**: Planning phase began
  - Contains: participant count, phases planned, saga enabled
  
- **TurnExecutionStarted**: Execution commenced
  - Contains: first phase, estimated completion
  
- **PhaseStarted**: Individual phase began
  - Contains: phase_type, started_at
  
- **PhaseCompleted**: Phase finished successfully
  - Contains: phase_type, events processed, performance summary
  
- **PhaseFailed**: Phase execution failed
  - Contains: phase_type, error message, compensation required
  
- **CompensationInitiated**: Saga rollback started
  - Contains: failed_phase, compensation actions list
  
- **TurnCompensationCompleted**: Recovery finished
  - Contains: compensation summary, recovery time
  
- **TurnCompleted**: Turn finished successfully
  - Contains: execution time, performance summary, phases completed
  
- **TurnFailed**: Turn failed permanently
  - Contains: error message, failed phases, execution time

## Application

### Services
- **TurnOrchestrator**: Main orchestration service
  - `create_turn(configuration)` - Initialize turn
  - `start_turn(turn_id)` - Begin execution
  - `execute_phase(turn_id, phase_type)` - Run specific phase
  - `complete_turn(turn_id)` - Mark successful completion
  - `fail_turn(turn_id, reason)` - Handle failure
  - `get_turn_status(turn_id)` - Current execution state
  - `get_performance_summary(turn_id)` - Execution metrics

- **PipelineOrchestrator**: Phase pipeline management
  - `execute_pipeline(turn_id)` - Run complete phase sequence
  - `execute_phase_with_retry(turn_id, phase_type)` - Resilient phase execution
  - `determine_next_phase(turn_id)` - Phase sequencing logic

- **SagaCoordinator**: Compensation management
  - `initiate_compensation(turn_id, failed_phase)` - Start rollback
  - `execute_compensation_action(action_id)` - Run compensation
  - `complete_compensation(turn_id)` - Finalize recovery

- **PerformanceTracker**: Metrics collection
  - `record_phase_metrics(turn_id, phase_type, metrics)` - Phase timing
  - `record_ai_usage(turn_id, usage_data)` - AI cost tracking
  - `get_execution_stats()` - Aggregate statistics

### Commands
- **CreateTurn**: Initialize turn
  - Handler: `CreateTurnHandler`
  - Side effects: TurnCreated event
  
- **ExecuteTurn**: Run complete turn
  - Handler: `ExecuteTurnHandler`
  - Side effects: Phase events, TurnCompleted/TurnFailed
  
- **CompensateTurn**: Execute failure recovery
  - Handler: `CompensateTurnHandler`
  - Side effects: Compensation events

### Queries
- **GetTurnStatus**: Execution state
  - Handler: `GetTurnStatusHandler`
  
- **GetTurnPerformance**: Metrics
  - Handler: `GetTurnPerformanceHandler`
  
- **ListActiveTurns**: Current executions
  - Handler: `ListActiveTurnsHandler`

## Infrastructure

### Repositories
- **TurnRepository**: Turn persistence
  - Event sourcing compatible
  - Optimistic locking for concurrent access

### External Services
- **MetricsMiddleware**: Performance instrumentation
- **TracingMiddleware**: Distributed tracing
- **PrometheusCollector**: Metrics export

### API Layer
- **TurnAPI**: REST endpoints for turn management
  - `/api/orchestration/start` - Create and start turn
  - `/api/orchestration/{id}/status` - Get status
  - `/api/orchestration/{id}/compensate` - Trigger compensation

## API

### REST Endpoints
- `POST /api/orchestration/turns` - Create turn
- `POST /api/orchestration/turns/{id}/start` - Start execution
- `GET /api/orchestration/turns/{id}/status` - Get status
- `GET /api/orchestration/turns/{id}/performance` - Get metrics
- `POST /api/orchestration/turns/{id}/compensate` - Trigger recovery

### WebSocket Events
- `orchestration.turn_started` - Execution began
- `orchestration.phase_completed` - Phase progress
- `orchestration.turn_completed` - Turn finished

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/orchestration/unit/ -v

# Integration tests
pytest tests/contexts/orchestration/integration/ -v

# All context tests
pytest tests/contexts/orchestration/ -v
```

### Test Coverage
Current coverage: 75%
Target coverage: 85%

## Architecture Decision Records
- ADR-001: Turn as saga coordinator for distributed transactions
- ADR-002: Phase-based pipeline for extensible processing
- ADR-003: Compensation actions for failure recovery
- ADR-004: Comprehensive audit trail for observability

## Integration Points

### Inbound
- Events consumed:
  - `CampaignStarted` from Campaigns Context
  - `CharacterLocationChanged` from Character Context (perception triggers)

### Outbound
- Events published:
  - `TurnCompleted` - For narrative generation
  - `WorldUpdateRequired` - For World Context
  - `PerceptionUpdateRequired` - For Subjective Context

### Dependencies
- **Domain**: None (pure domain)
- **Application**: All other contexts (World, Character, Subjective, etc.)
- **Infrastructure**: PostgreSQL, Redis, Prometheus, OpenTelemetry

## Development Guide

### Adding New Features
1. Extend Turn aggregate for new state
2. Add phase types to PhaseType enum
3. Implement phase handlers
4. Add compensation types if needed
5. Update API endpoints
6. Write tests

### Common Tasks
- **Adding a new phase**: Extend `PhaseType`, add handler, update pipeline
- **Adding compensation types**: Extend `CompensationType`, implement actions

## Maintainer
Team: @orchestration-team
Contact: orchestration@example.com
