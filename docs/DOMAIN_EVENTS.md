# Novel Engine M1 - Domain Events Catalog

**Version**: 1.0.0  
**Last Updated**: 2025-08-26  
**Status**: Baseline Domain Event Specification  
**Maintainer**: Novel Engine Development Team

---

## 📋 Table of Contents

1. [Domain Events Overview](#domain-events-overview)
2. [Event Architecture](#event-architecture)
3. [Characters Domain Events](#characters-domain-events)
4. [Narratives Domain Events](#narratives-domain-events)
5. [Campaigns Domain Events](#campaigns-domain-events)
6. [Interactions Domain Events](#interactions-domain-events)
7. [Orchestration Domain Events](#orchestration-domain-events)
8. [Shared Domain Events](#shared-domain-events)
9. [Event Handling Patterns](#event-handling-patterns)
10. [Integration Guidelines](#integration-guidelines)

---

## Domain Events Overview

### Purpose
Domain events represent significant business occurrences within the Novel Engine M1 system. They enable decoupled communication between bounded contexts, support event sourcing patterns, and provide a foundation for eventual consistency across microservices.

### Event-Driven Architecture Benefits
- **Decoupling**: Bounded contexts communicate through well-defined events
- **Scalability**: Asynchronous processing enables horizontal scaling
- **Resilience**: Event replay and compensation patterns support fault tolerance
- **Auditability**: Complete event log provides audit trail and debugging capability
- **Integration**: External systems can subscribe to relevant business events

### Design Principles
- **Domain-Centric**: Events represent meaningful business occurrences
- **Immutable**: Events are immutable facts about what happened
- **Self-Contained**: Events contain all necessary data for processing
- **Versioned**: Events support schema evolution and backward compatibility
- **Traceable**: Events include correlation and causation identifiers

---

## Event Architecture

### Event Structure
```json
{
  "eventId": "uuid",
  "eventType": "domain.aggregate.action",
  "eventVersion": "1.0.0",
  "aggregateId": "uuid",
  "aggregateType": "Character|Story|Campaign|Interaction",
  "timestamp": "ISO-8601",
  "correlationId": "uuid",
  "causationId": "uuid",
  "userId": "uuid",
  "payload": {
    // Event-specific data
  },
  "metadata": {
    "source": "service-name",
    "trace": "trace-id",
    "schema": "schema-url"
  }
}
```

### Event Categories
- **Command Events**: Actions initiated by users or systems
- **Domain Events**: Business-significant state changes
- **Integration Events**: Cross-context communication events
- **System Events**: Infrastructure and operational events
- **Notification Events**: User notification triggers

### Event Processing Patterns
- **Event Sourcing**: Aggregate state derived from event sequence
- **CQRS**: Separate command and query models updated by events
- **Saga Pattern**: Long-running transactions coordinated through events
- **Event Streaming**: Real-time event processing and routing
- **Event Store**: Persistent event log with replay capabilities

---

## Characters Domain Events

### Character Lifecycle Events

#### CharacterCreated
```yaml
eventType: "characters.character.created"
eventVersion: "1.0.0"
description: "New character has been created in the system"
triggers:
  - User creates character through API
  - System generates NPC character
  - Character import from external system
payload:
  characterId: uuid
  name: string
  type: "protagonist|antagonist|npc|narrator"
  personalityTraits:
    openness: number
    conscientiousness: number
    extraversion: number
    agreeableness: number
    neuroticism: number
  background: string
  configuration: object
  createdBy: uuid
subscribers:
  - Memory Service (initialize character memory)
  - Story Engine (register character for narrative generation)
  - Campaign Manager (make character available for campaigns)
  - Monitoring Service (track character creation metrics)
```

#### CharacterUpdated
```yaml
eventType: "characters.character.updated"
eventVersion: "1.0.0"
description: "Character information has been modified"
payload:
  characterId: uuid
  changes: object # Key-value pairs of changed fields
  previousValues: object # Previous values for changed fields
  updatedBy: uuid
subscribers:
  - Memory Service (update character profile memory)
  - Story Engine (refresh character context)
  - Campaign Manager (sync character data across active campaigns)
```

#### CharacterDeleted
```yaml
eventType: "characters.character.deleted"
eventVersion: "1.0.0"
description: "Character has been permanently deleted"
payload:
  characterId: uuid
  name: string
  deletionReason: string
  deletedBy: uuid
subscribers:
  - Memory Service (archive/delete character memories)
  - Story Engine (remove character from story templates)
  - Campaign Manager (remove character from campaigns)
  - Cleanup Service (cascade delete related data)
```

### Character Development Events

#### CharacterSkillGained
```yaml
eventType: "characters.character.skill-gained"
eventVersion: "1.0.0"
description: "Character has acquired a new skill or ability"
payload:
  characterId: uuid
  skillName: string
  skillLevel: number
  acquisitionMethod: "training|experience|story-event"
  context: string
subscribers:
  - Story Engine (incorporate skill into narrative generation)
  - Campaign Manager (update character capabilities)
  - Analytics Service (track character development patterns)
```

#### CharacterRelationshipFormed
```yaml
eventType: "characters.character.relationship-formed"
eventVersion: "1.0.0"
description: "Character has formed a relationship with another character"
payload:
  characterId: uuid
  relatedCharacterId: uuid
  relationshipType: "ally|enemy|neutral|romantic|family"
  relationshipStrength: number # 0.0 to 1.0
  context: string
  formationEvent: string
subscribers:
  - Memory Service (create relationship memories)
  - Story Engine (consider relationships in story generation)
  - Interactions Service (adjust interaction patterns)
```

#### CharacterPersonalityEvolved
```yaml
eventType: "characters.character.personality-evolved"
eventVersion: "1.0.0"
description: "Character personality traits have changed through experiences"
payload:
  characterId: uuid
  traitChanges:
    openness: number # Change delta
    conscientiousness: number
    extraversion: number
    agreeableness: number
    neuroticism: number
  triggeringEvents: array # Events that caused personality change
  evolutionReason: string
subscribers:
  - Story Engine (adapt character behavior generation)
  - Interactions Service (update interaction patterns)
  - Analytics Service (track character development)
```

---

## Narratives Domain Events

### Story Lifecycle Events

#### StoryGenerationRequested
```yaml
eventType: "narratives.story.generation-requested"
eventVersion: "1.0.0"
description: "User has requested generation of a new story"
payload:
  storyId: uuid
  title: string
  genre: "fantasy|sci-fi|mystery|romance|horror|adventure|drama|comedy"
  themes: array
  characters: array # Character IDs
  length: "short|medium|long"
  tone: "dark|light|heroic|mysterious|comedic"
  configuration: object
  requestedBy: uuid
subscribers:
  - Story Engine (process story generation)
  - Characters Service (prepare character contexts)
  - Memory Service (gather relevant memories)
  - Analytics Service (track story generation requests)
```

#### StoryGenerated
```yaml
eventType: "narratives.story.generated"
eventVersion: "1.0.0"
description: "Story has been successfully generated by AI"
payload:
  storyId: uuid
  title: string
  content: string
  wordCount: number
  qualityScore: number # AI-evaluated quality (0.0-1.0)
  generationMetrics:
    duration: number # Generation time in seconds
    modelUsed: string
    tokensConsumed: number
    iterations: number
  characters: array # Characters featured in story
subscribers:
  - Campaign Manager (make story available for campaigns)
  - Memory Service (create story memories for characters)
  - Analytics Service (track story quality and generation metrics)
  - Notification Service (notify requestor of completion)
```

#### StoryQualityAssessed
```yaml
eventType: "narratives.story.quality-assessed"
eventVersion: "1.0.0"
description: "Story quality has been evaluated by AI or human reviewers"
payload:
  storyId: uuid
  qualityScore: number
  assessmentCriteria:
    coherence: number
    engagement: number
    characterDevelopment: number
    plotStructure: number
    languageQuality: number
  assessor: "ai|human"
  assessorId: uuid
  feedback: string
subscribers:
  - Story Engine (improve generation algorithms)
  - Analytics Service (track quality metrics)
  - Content Moderation (flag low-quality content)
```

### Plot Development Events

#### PlotPointReached
```yaml
eventType: "narratives.plot.point-reached"
eventVersion: "1.0.0"
description: "Story has reached a significant plot point"
payload:
  storyId: uuid
  plotPoint: "inciting-incident|rising-action|climax|falling-action|resolution"
  description: string
  characters: array # Characters involved in plot point
  consequences: array # Expected story consequences
  timestamp: datetime
subscribers:
  - Characters Service (trigger character development)
  - Interactions Service (generate character reactions)
  - Memory Service (create significant memories)
```

#### NarrativeConflictIntroduced
```yaml
eventType: "narratives.narrative.conflict-introduced"
eventVersion: "1.0.0"
description: "New conflict has been introduced to the narrative"
payload:
  storyId: uuid
  conflictId: uuid
  conflictType: "character-vs-character|character-vs-nature|character-vs-society|character-vs-self"
  description: string
  involvedCharacters: array
  severity: "minor|moderate|major|critical"
  expectedResolution: string
subscribers:
  - Characters Service (prepare character responses)
  - Story Engine (track conflict resolution)
  - Campaign Manager (integrate conflict into active campaigns)
```

---

## Campaigns Domain Events

### Campaign Lifecycle Events

#### CampaignCreated
```yaml
eventType: "campaigns.campaign.created"
eventVersion: "1.0.0"
description: "New campaign has been created"
payload:
  campaignId: uuid
  name: string
  description: string
  configuration: object
  createdBy: uuid
  initialParticipants: array # User IDs
  worldState: object # Initial world configuration
subscribers:
  - Characters Service (prepare campaign characters)
  - Story Engine (generate campaign narratives)
  - Memory Service (initialize campaign memory space)
  - Notification Service (notify participants)
```

#### CampaignStarted
```yaml
eventType: "campaigns.campaign.started"
eventVersion: "1.0.0"
description: "Campaign has officially begun"
payload:
  campaignId: uuid
  startTime: datetime
  participants: array # Active participants
  initialScene: object
  gamemaster: uuid
subscribers:
  - Session Manager (create first session)
  - Story Engine (begin narrative generation)
  - Characters Service (activate campaign characters)
  - Analytics Service (track campaign start metrics)
```

#### CampaignCompleted
```yaml
eventType: "campaigns.campaign.completed"
eventVersion: "1.0.0"
description: "Campaign has reached its conclusion"
payload:
  campaignId: uuid
  completionTime: datetime
  finalScene: object
  outcomes: object # Campaign results and achievements
  statistics:
    duration: number # Total campaign duration
    sessionsCount: number
    participantsCount: number
    storiesGenerated: number
  completionReason: "natural-conclusion|early-termination|player-request"
subscribers:
  - Memory Service (archive campaign memories)
  - Analytics Service (compile campaign statistics)
  - Notification Service (notify participants of completion)
  - Characters Service (process character final development)
```

### Session Management Events

#### SessionStarted
```yaml
eventType: "campaigns.session.started"
eventVersion: "1.0.0"
description: "New campaign session has begun"
payload:
  campaignId: uuid
  sessionId: uuid
  sessionNumber: number
  startTime: datetime
  participants: array # Active participants
  gamemaster: uuid
  initialState: object
subscribers:
  - Story Engine (prepare session narratives)
  - Characters Service (activate session characters)
  - Interactions Service (enable character interactions)
  - Memory Service (prepare session memory context)
```

#### WorldStateChanged
```yaml
eventType: "campaigns.world.state-changed"
eventVersion: "1.0.0"
description: "Campaign world state has been modified"
payload:
  campaignId: uuid
  sessionId: uuid
  changes: object # State changes
  previousState: object # Previous world state
  changeReason: string
  changedBy: uuid
  timestamp: datetime
subscribers:
  - Story Engine (adapt narratives to new state)
  - Characters Service (update character contexts)
  - Memory Service (record state change memories)
  - Session Manager (persist world state)
```

---

## Interactions Domain Events

### Character Interaction Events

#### InteractionInitiated
```yaml
eventType: "interactions.interaction.initiated"
eventVersion: "1.0.0"
description: "Character has initiated an interaction"
payload:
  interactionId: uuid
  campaignId: uuid
  sessionId: uuid
  initiatingCharacterId: uuid
  targetCharacterIds: array
  interactionType: "dialogue|action|combat|skill-check"
  intent: string
  context: object
subscribers:
  - Characters Service (prepare character responses)
  - Story Engine (generate interaction outcomes)
  - Memory Service (prepare interaction memories)
  - Rules Engine (validate interaction legality)
```

#### DialogueExchanged
```yaml
eventType: "interactions.dialogue.exchanged"
eventVersion: "1.0.0"
description: "Characters have exchanged dialogue"
payload:
  interactionId: uuid
  campaignId: uuid
  speakerId: uuid
  listenerId: uuid
  message: string
  tone: "friendly|hostile|neutral|romantic|authoritative"
  context: object
  timestamp: datetime
subscribers:
  - Memory Service (create dialogue memories)
  - Characters Service (process character reactions)
  - Story Engine (integrate dialogue into narrative)
  - Sentiment Analysis (analyze dialogue tone)
```

#### ActionPerformed
```yaml
eventType: "interactions.action.performed"
eventVersion: "1.0.0"
description: "Character has performed an action"
payload:
  interactionId: uuid
  campaignId: uuid
  actingCharacterId: uuid
  actionType: "movement|skill-use|item-interaction|environmental"
  actionDescription: string
  targetIds: array # Characters/objects affected
  success: boolean
  outcomes: object
  consequences: array
subscribers:
  - World State Manager (update world state)
  - Characters Service (process action consequences)
  - Story Engine (incorporate action into narrative)
  - Memory Service (create action memories)
```

### Interaction Resolution Events

#### InteractionResolved
```yaml
eventType: "interactions.interaction.resolved"
eventVersion: "1.0.0"
description: "Interaction has been completed and resolved"
payload:
  interactionId: uuid
  campaignId: uuid
  participants: array # All participating characters
  resolution: object # Final interaction outcomes
  duration: number # Interaction duration
  consequences: array # Story/character consequences
  narrativeImpact: string
subscribers:
  - Memory Service (finalize interaction memories)
  - Story Engine (continue narrative with resolution)
  - Characters Service (apply character development)
  - Analytics Service (track interaction patterns)
```

---

## Orchestration Domain Events

### Workflow Coordination Events

#### WorkflowStarted
```yaml
eventType: "orchestration.workflow.started"
eventVersion: "1.0.0"
description: "Multi-service workflow has been initiated"
payload:
  workflowId: uuid
  workflowType: "story-generation|campaign-creation|character-interaction"
  steps: array # Planned workflow steps
  context: object
  initiatedBy: uuid
  priority: "low|normal|high|critical"
subscribers:
  - Workflow Engine (track workflow progress)
  - Resource Manager (allocate necessary resources)
  - Monitoring Service (track workflow performance)
```

#### ResourceAllocated
```yaml
eventType: "orchestration.resource.allocated"
eventVersion: "1.0.0"
description: "System resource has been allocated for operation"
payload:
  resourceId: uuid
  resourceType: "ai-model|database-connection|cache-space|compute-instance"
  allocationAmount: number
  allocatedTo: string # Service or operation
  duration: number # Expected allocation duration
  priority: string
subscribers:
  - Resource Manager (track resource usage)
  - Monitoring Service (monitor resource utilization)
  - Scaling Service (adjust capacity if needed)
```

#### ServiceCoordinationRequired
```yaml
eventType: "orchestration.service.coordination-required"
eventVersion: "1.0.0"
description: "Multiple services need to coordinate for operation"
payload:
  coordinationId: uuid
  services: array # Services that need coordination
  operation: string
  dependencies: object # Service dependencies
  timeout: number # Maximum coordination time
subscribers:
  - Service Coordinator (orchestrate service calls)
  - Monitoring Service (track coordination performance)
  - Failure Handler (handle coordination failures)
```

---

## Shared Domain Events

### System-Wide Events

#### UserAuthenticated
```yaml
eventType: "shared.user.authenticated"
eventVersion: "1.0.0"
description: "User has successfully authenticated"
payload:
  userId: uuid
  email: string
  authenticationMethod: "password|oauth2|api-key"
  sessionId: uuid
  timestamp: datetime
  ipAddress: string
  userAgent: string
subscribers:
  - Session Manager (create user session)
  - Analytics Service (track user activity)
  - Security Service (log authentication event)
  - Notification Service (send login notifications if enabled)
```

#### SystemHealthChanged
```yaml
eventType: "shared.system.health-changed"
eventVersion: "1.0.0"
description: "System health status has changed"
payload:
  component: string
  previousHealth: "healthy|degraded|unhealthy"
  currentHealth: "healthy|degraded|unhealthy"
  details: object
  timestamp: datetime
subscribers:
  - Monitoring Dashboard (update health displays)
  - Alerting Service (send health alerts)
  - Auto-scaling Service (adjust capacity)
  - Load Balancer (adjust routing)
```

#### DataBackupCompleted
```yaml
eventType: "shared.data.backup-completed"
eventVersion: "1.0.0"
description: "Scheduled data backup has completed"
payload:
  backupId: uuid
  backupType: "full|incremental|differential"
  dataSize: number # Backup size in bytes
  duration: number # Backup duration in seconds
  success: boolean
  location: string # Backup storage location
  timestamp: datetime
subscribers:
  - Backup Monitor (track backup success/failure)
  - Storage Manager (manage backup retention)
  - Compliance Service (maintain backup compliance)
```

---

## Event Handling Patterns

### Event Processing Strategies

#### Immediate Processing
- **Use Case**: Critical business events requiring immediate action
- **Examples**: User authentication, payment processing, security events
- **Implementation**: Synchronous event handlers with immediate response
- **Guarantees**: Strong consistency, immediate feedback

#### Asynchronous Processing
- **Use Case**: Non-critical events that can be processed later
- **Examples**: Analytics updates, notification sending, cache updates
- **Implementation**: Event queues with background processing
- **Guarantees**: Eventual consistency, high throughput

#### Batch Processing
- **Use Case**: High-volume events that can be processed in groups
- **Examples**: Log aggregation, metrics calculation, reporting
- **Implementation**: Event batching with scheduled processing
- **Guarantees**: High efficiency, delayed processing

### Error Handling and Resilience

#### Retry Patterns
```yaml
retryPolicy:
  maxAttempts: 3
  backoffStrategy: "exponential"
  baseDelay: 1000ms
  maxDelay: 30000ms
  retryableErrors:
    - "network-timeout"
    - "service-unavailable"
    - "temporary-failure"
```

#### Dead Letter Queues
- **Purpose**: Handle events that cannot be processed after retries
- **Implementation**: Dedicated queues for failed events
- **Monitoring**: Alert on dead letter queue accumulation
- **Recovery**: Manual review and reprocessing capabilities

#### Compensation Patterns
- **Saga Pattern**: Distributed transaction management
- **Compensation Events**: Undo operations for failed transactions
- **Idempotency**: Safe event replay and duplicate handling
- **State Recovery**: Restore consistent state after failures

### Event Versioning and Evolution

#### Schema Evolution
```yaml
eventSchema:
  version: "1.0.0"
  compatibilityMode: "backward-compatible"
  changes:
    - type: "field-added"
      field: "newField"
      optional: true
    - type: "field-deprecated"
      field: "oldField"
      removalVersion: "2.0.0"
```

#### Version Migration
- **Backward Compatibility**: New versions can process old events
- **Forward Compatibility**: Old versions can process new events (with defaults)
- **Migration Strategies**: Gradual rollout with version support
- **Deprecation Policy**: Clear timeline for version deprecation

---

## Integration Guidelines

### Event Publishing

#### Publisher Responsibilities
- **Event Completeness**: Include all necessary data in event payload
- **Event Ordering**: Maintain causal ordering for related events
- **Error Handling**: Handle publishing failures gracefully
- **Schema Compliance**: Validate events against published schemas

#### Publishing Best Practices
```python
# Example event publishing pattern
async def publish_character_created_event(character: Character):
    event = CharacterCreatedEvent(
        eventId=generate_uuid(),
        aggregateId=character.id,
        timestamp=datetime.utcnow(),
        payload={
            "characterId": character.id,
            "name": character.name,
            "type": character.type,
            "personalityTraits": character.personality_traits,
            "background": character.background,
            "configuration": character.configuration,
            "createdBy": character.created_by
        }
    )
    await event_bus.publish(event)
```

### Event Subscription

#### Subscriber Responsibilities
- **Idempotency**: Handle duplicate events safely
- **Error Handling**: Implement proper error handling and retries
- **Performance**: Process events efficiently to avoid backlogs
- **State Management**: Maintain consistent state from events

#### Subscription Patterns
```python
# Example event subscription pattern
@event_handler("characters.character.created")
async def handle_character_created(event: CharacterCreatedEvent):
    try:
        # Initialize character memory
        await memory_service.create_character_memory(
            character_id=event.payload.characterId,
            initial_profile=event.payload
        )
        
        # Register with story engine
        await story_engine.register_character(
            character_id=event.payload.characterId,
            character_data=event.payload
        )
        
    except Exception as e:
        logger.error(f"Failed to handle character created event: {e}")
        raise  # Event will be retried
```

### Monitoring and Observability

#### Event Metrics
- **Publishing Metrics**: Event publication rates, failures, latency
- **Processing Metrics**: Event processing rates, failures, backlog size
- **Business Metrics**: Domain-specific event patterns and trends
- **System Metrics**: Event store performance, queue depths, errors

#### Event Tracing
- **Correlation IDs**: Track event flows across services
- **Causation IDs**: Understand event cause-and-effect relationships
- **Distributed Tracing**: Trace event processing across system boundaries
- **Event Lineage**: Track event origins and transformations

---

## Conclusion

This domain events catalog provides the foundation for event-driven communication within Novel Engine M1. The catalog will evolve as new domains are added and existing domains mature, maintaining consistency with the overall system architecture.

### Implementation Priorities
1. **Core Events**: Implement essential lifecycle events for each domain
2. **Integration Events**: Establish cross-domain communication patterns
3. **Monitoring Events**: Add observability and operational events
4. **Advanced Events**: Implement complex workflow and orchestration events

### Maintenance Guidelines
- **Regular Reviews**: Quarterly review of event catalog completeness
- **Schema Management**: Maintain event schema registry with versioning
- **Documentation Updates**: Keep event documentation synchronized with implementation
- **Performance Monitoring**: Monitor event processing performance and optimize as needed

---

**Document Version**: 1.0.0  
**Last Review**: 2025-08-26  
**Next Review**: 2025-11-26  
**Schema Registry**: [Event Schema Registry URL]  
**Reviewers**: Architecture Team, Domain Experts, Development Team