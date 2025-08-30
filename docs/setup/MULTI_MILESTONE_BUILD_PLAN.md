# Major Multi-Milestone Build Plan: M5, M6, M7

## 🏗️ Wave 1: Architecture Analysis & Planning

**Objective**: Design complete bounded contexts following established DDD patterns

### Context Architecture Analysis

Based on existing **Character** and **World** contexts, established patterns:

#### Domain Layer Structure:
```
domain/
├── __init__.py
├── aggregates/
│   ├── __init__.py
│   └── [aggregate].py          # Aggregate roots
├── entities/
│   ├── __init__.py
│   └── [entity].py            # Domain entities
├── events/
│   ├── __init__.py
│   └── [context]_events.py    # Domain events
├── repositories/
│   ├── __init__.py
│   └── [aggregate]_repository.py  # Repository interfaces
└── value_objects/
    ├── __init__.py
    ├── [context]_id.py        # Identity value objects
    └── [domain_concept].py    # Value objects
```

#### Application Layer Structure:
```
application/
├── __init__.py
├── commands/
│   ├── __init__.py
│   ├── [context]_commands.py      # Command DTOs
│   └── [context]_command_handlers.py  # Command handlers
├── queries/
│   ├── __init__.py
│   └── [context]_queries.py       # Query handlers
└── services/
    ├── __init__.py
    ├── [context]_application_service.py  # Main app service
    └── [domain]_service.py        # Domain services
```

#### Infrastructure Layer Structure:
```
infrastructure/
├── __init__.py
├── persistence/
│   ├── __init__.py
│   └── [context]_models.py     # SQLAlchemy ORM models
└── repositories/
    ├── __init__.py
    └── [aggregate]_repository.py  # Repository implementations
```

## 🎯 Wave 2: M5 Subjective Context Implementation

### New Context: `contexts/subjective/`

**Primary Aggregate**: `TurnBrief`
- Represents subjective game state from a character's perspective
- Manages fog of war, perception, knowledge, and awareness

**Domain Service**: `FogOfWarService`
- Handles visibility calculations and information filtering
- Manages knowledge propagation and revelation mechanics

#### M5 Domain Layer:
- **Aggregates**: `TurnBrief` (character's subjective view of game state)
- **Value Objects**: `SubjectiveId`, `PerceptionRange`, `KnowledgeLevel`, `Awareness`
- **Events**: `TurnBriefCreated`, `PerceptionUpdated`, `KnowledgeRevealed`
- **Repository**: `ITurnBriefRepository`

#### M5 Application Layer:
- **Commands**: `CreateTurnBrief`, `UpdatePerception`, `RevealKnowledge`
- **Services**: `SubjectiveApplicationService`, `FogOfWarService`
- **Query Handlers**: `GetTurnBrief`, `GetPerceptionRange`

#### M5 Infrastructure Layer:
- **Models**: `TurnBriefORM`, `PerceptionORM`, `KnowledgeORM`
- **Repository**: `SQLAlchemyTurnBriefRepository`

## 🤝 Wave 3: M6 Interaction Context Implementation

### Existing Context: `contexts/interactions/` (enhance)

**Primary Aggregate**: `NegotiationSession`
- Represents ongoing negotiations between entities
- Manages negotiation states, proposals, and outcomes

#### M6 Domain Layer:
- **Aggregates**: `NegotiationSession` (negotiation process management)
- **Entities**: `NegotiationParty`, `Proposal` 
- **Value Objects**: `InteractionId`, `NegotiationStatus`, `ProposalTerms`
- **Events**: `NegotiationStarted`, `ProposalMade`, `NegotiationCompleted`
- **Repository**: `INegotiationSessionRepository`

#### M6 Application Layer:
- **Commands**: `StartNegotiation`, `MakeProposal`, `AcceptProposal`, `RejectProposal`
- **Services**: `InteractionApplicationService`, `NegotiationService`
- **Query Handlers**: `GetNegotiationSession`, `GetNegotiationHistory`

#### M6 Infrastructure Layer:
- **Models**: `NegotiationSessionORM`, `NegotiationPartyORM`, `ProposalORM`
- **Repository**: `SQLAlchemyNegotiationSessionRepository`

## 📖 Wave 4: M7 Narrative Context Implementation

### Existing Context: `contexts/narratives/` (enhance)

**Primary Aggregate**: `NarrativeArc`
- Represents story progressions and narrative structures
- Manages plot points, character development, and story beats

**Domain Service**: `CausalGraph`
- Handles cause-and-effect relationships in narrative
- Manages story dependency tracking and consequence propagation

#### M7 Domain Layer:
- **Aggregates**: `NarrativeArc` (story progression management)
- **Entities**: `PlotPoint`, `StoryBeat`, `CharacterDevelopment`
- **Value Objects**: `NarrativeId`, `ArcType`, `PlotStatus`, `CausalLink`
- **Events**: `NarrativeStarted`, `PlotPointReached`, `ArcCompleted`
- **Repository**: `INarrativeArcRepository`

#### M7 Application Layer:
- **Commands**: `StartNarrativeArc`, `AdvancePlot`, `TriggerStoryBeat`
- **Services**: `NarrativeApplicationService`, `CausalGraphService`
- **Query Handlers**: `GetNarrativeArc`, `GetStoryProgress`

#### M7 Infrastructure Layer:
- **Models**: `NarrativeArcORM`, `PlotPointORM`, `StoryBeatORM`, `CausalLinkORM`
- **Repository**: `SQLAlchemyNarrativeArcRepository`

## 🔍 Wave 5: Cross-Context Validation & Fixing

**Objective**: Ensure structural soundness and DDD compliance

### Validation Checklist:
- [ ] All aggregates follow established patterns
- [ ] Domain events properly defined and raised
- [ ] Repository interfaces and implementations aligned
- [ ] Command/query separation maintained
- [ ] Value objects are immutable and self-validating
- [ ] Application services coordinate properly
- [ ] Infrastructure layer properly separated from domain

### Validation Tasks:
1. **Structural Validation**: Directory structure matches patterns
2. **Code Quality**: Consistent naming, imports, error handling
3. **DDD Compliance**: Proper aggregate boundaries, event sourcing
4. **Integration Points**: Cross-context dependencies managed
5. **Error Handling**: Consistent exception patterns
6. **Performance**: Repository query optimization

## 🧪 Wave 6: Integration Testing & Final Validation

**Objective**: Comprehensive testing and system integration

### Testing Strategy:
1. **Unit Tests**: Domain logic and value object validation
2. **Integration Tests**: Repository and database operations
3. **Application Tests**: Command/query handler functionality
4. **Cross-Context Tests**: Inter-bounded context communication
5. **End-to-End Tests**: Complete workflow validation

### Final Validation:
- [ ] All contexts can be imported without errors
- [ ] Database models can be created and migrated
- [ ] Application services handle commands correctly
- [ ] Repository implementations work with database
- [ ] Domain events are properly published and handled
- [ ] Cross-context integration points function correctly

## 📊 Success Criteria

**Wave Completion Metrics**:
- ✅ Wave 1: Complete architectural blueprint
- ✅ Wave 2: M5 Subjective context fully implemented
- ✅ Wave 3: M6 Interaction context fully implemented  
- ✅ Wave 4: M7 Narrative context fully implemented
- ✅ Wave 5: All validation checks pass
- ✅ Wave 6: Integration tests pass, system ready for production

**Deliverables**:
- 3 Complete bounded contexts (15+ domain classes each)
- 45+ Python files across domain/application/infrastructure layers
- Complete repository interfaces and implementations
- Comprehensive command/query handlers
- SQLAlchemy ORM models for all aggregates
- Domain event system integration
- Cross-context validation and testing

**Quality Gates**:
- DDD pattern compliance: 100%
- Import/syntax errors: 0
- Test coverage: Domain logic 90%+
- Code consistency: Follows established patterns
- Performance: Repository operations < 100ms
- Documentation: All public APIs documented