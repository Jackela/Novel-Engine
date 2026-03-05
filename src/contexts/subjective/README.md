# Subjective Context

## Overview
The Subjective Context manages entity-specific perceptions and knowledge states within the Novel Engine platform. It implements the "fog of war" concept, where each entity has a limited and potentially inaccurate view of the world based on their capabilities and position.

This context handles perception ranges, awareness states, knowledge acquisition, and threat detection from individual entity perspectives. It enables realistic asymmetric information in narratives.

## Domain

### Aggregates
- **TurnBrief**: Root aggregate for entity subjective state
  - Perception capabilities and current awareness
  - Knowledge base with certainty levels
  - Visible subjects tracking
  - Known threats monitoring
  - Links to world state version

### Entities
- **None**: TurnBrief aggregate manages all data.

### Value Objects
- **SubjectiveId**: Unique identifier for turn briefs

- **PerceptionCapabilities**: Sensory abilities
  - **PerceptionType**: VISUAL, AUDITORY, OLFACTORY, TACTILE, MAGICAL, PSYCHIC, TECHNOLOGICAL
  - Range and accuracy per type
  - Environmental modifiers
  
- **PerceptionRange**: Specific sense parameters
  - Base range, environmental effects
  - Accuracy modifier at distance
  - `calculate_visibility_at_distance(distance)` - Visibility calculation
  
- **VisibilityLevel**: Clarity of perception
  - CLEAR, PARTIAL, OBSCURED, HIDDEN, INVISIBLE
  
- **AwarenessState**: Current mental state
  - **AlertnessLevel**: UNCONSCIOUS, ASLEEP, DROWSY, RELAXED, ALERT, FOCUSED, HYPER_ALERT
  - **AttentionFocus**: UNFOCUSED, GENERAL, TARGET_SPECIFIC
  - Focus target tracking
  - Fatigue and stress modifiers
  
- **KnowledgeBase**: Entity's known information
  - **KnowledgeItem**: Specific fact with certainty
  - **CertaintyLevel**: CERTAIN, LIKELY, POSSIBLE, SPECULATED, MINIMAL
  - Source tracking and reliability
  
- **Awareness**: Combined perception/awareness metric
  - Current visibility determination
  - Stealth detection capability
  - Reaction time modifier

### Domain Events
- **TurnBriefCreated**: New subjective view initialized
  - Contains: entity_id, world_state_version, initial_alertness
  
- **NewPerceptionAcquired**: Something perceived
  - Contains: perceived_subject, perception_type, visibility_level, distance
  
- **KnowledgeRevealed**: New fact learned
  - Contains: knowledge_item, revelation_method
  
- **KnowledgeUpdated**: Existing knowledge changed
  - Contains: subject, old/new knowledge, update_reason
  
- **ThreatDetected**: Danger identified
  - Contains: threat_subject, threat_type, level, confidence, detection_method
  
- **ThreatLost**: Threat no longer tracked
  - Contains: threat_subject, loss_reason, last_known_position
  
- **FogOfWarUpdated**: Visibility changes
  - Contains: newly_revealed, newly_concealed, visibility_changes
  
- **AlertnessChanged**: Awareness level shift
  - Contains: old/new alertness, change_trigger
  
- **AttentionFocusChanged**: Focus adjustment
  - Contains: old/new focus, old/new target
  
- **PerceptionRangeUpdated**: Sensory capability change
  - Contains: perception_type, old/new range, change_reason
  
- **TurnBriefUpdated**: General update
  - Contains: update_reason, version change

## Application

### Services
- **SubjectiveApplicationService**: Main subjective operations
  - `create_turn_brief(entity_id, capabilities, world_version)` - Initialize view
  - `update_perception(brief_id, perception_data)` - Process perception
  - `add_knowledge(brief_id, knowledge, source)` - Learn fact
  - `detect_threat(brief_id, threat_data)` - Record danger
  - `update_fog_of_war(brief_id, changes)` - Apply visibility updates
  - `get_perception_summary(brief_id)` - Current state overview

- **FogOfWarService**: Visibility calculation
  - `calculate_visibility(brief_id, subjects)` - What can be seen
  - `update_visibility(brief_id, world_changes)` - Apply world updates
  - `is_subject_detectable(brief_id, subject, stealth_level)` - Detection check

### Commands
- **CreateTurnBrief**: Initialize subjective view
  - Handler: `CreateTurnBriefHandler`
  
- **RecordPerception**: Process sensory input
  - Handler: `RecordPerceptionHandler`
  
- **UpdateAwareness**: Change alertness/focus
  - Handler: `UpdateAwarenessHandler`

### Queries
- **GetSubjectiveView**: Entity's current perception
  - Handler: `GetSubjectiveViewHandler`
  
- **GetKnownThreats**: Active danger list
  - Handler: `GetKnownThreatsHandler`
  
- **GetKnowledgeAbout**: Specific subject info
  - Handler: `GetKnowledgeAboutHandler`

## Infrastructure

### Repositories
- **TurnBriefRepository**: Subjective state persistence
  - Implementation: PostgreSQL with JSONB for flexible perception data
  - Cache: Redis for hot entities

### External Services
- None directly

## API

### REST Endpoints
- `POST /api/subjective/turn-briefs` - Create brief
- `GET /api/subjective/turn-briefs/{id}` - Get current view
- `POST /api/subjective/turn-briefs/{id}/perceptions` - Record perception
- `GET /api/subjective/turn-briefs/{id}/threats` - List known threats
- `GET /api/subjective/turn-briefs/{id}/knowledge/{subject}` - Query knowledge

### WebSocket Events
- `subjective.threat_detected` - Real-time threat alerts
- `subjective.visibility_changed` - Fog of war updates

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/subjective/unit/ -v

# Integration tests
pytest tests/contexts/subjective/integration/ -v

# All context tests
pytest tests/contexts/subjective/ -v
```

### Test Coverage
Current coverage: 70%
Target coverage: 80%

## Architecture Decision Records
- ADR-001: TurnBrief as aggregate for subjective reality
- ADR-002: Fog of war model for asymmetric information
- ADR-003: Knowledge certainty levels for unreliable information

## Integration Points

### Inbound
- Events consumed:
  - `WorldStateChanged` from World Context (affects visibility)
  - `CharacterMoved` from Character Context (perception triggers)

### Outbound
- Events published:
  - `ThreatDetected` - For AI decision-making
  - `KnowledgeRevealed` - For character memory

### Dependencies
- **Domain**: None (pure domain)
- **Application**: World Context (world state), Character Context (entities)
- **Infrastructure**: PostgreSQL, Redis

## Development Guide

### Adding New Features
1. Extend value objects (perception types, alertness levels)
2. Add domain logic to TurnBrief
3. Update application services
4. Write tests

### Common Tasks
- **Adding perception types**: Extend `PerceptionType` enum
- **New knowledge categories**: Extend knowledge subject types
- **Detection algorithms**: Update `FogOfWarService`

## Maintainer
Team: @subjective-team
Contact: subjective@example.com
