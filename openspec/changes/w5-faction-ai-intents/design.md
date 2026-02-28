## Context

The world simulation now has a connected Time-Geopolitics system (Operation Bridge) that triggers `FactionTickService` when time advances. However, the faction tick service currently has placeholder methods - it doesn't actually make decisions.

This design adds AI-driven decision-making for factions, using the existing RAG pipeline (`RetrievalService`) to fetch relevant context (lore, relationships, recent events) and the LLM infrastructure to generate intent options.

### Current State
- `FactionTickService.process_tick()` exists but has placeholder methods
- `RetrievalService` provides RAG capabilities for context retrieval
- LLM infrastructure exists in `src/contexts/ai/`
- EventBus is wired for `world.time_advanced` events

## Goals / Non-Goals

**Goals:**
- Enable factions to generate strategic intents based on their current state
- Use RAG to provide rich context (relationships, lore, events) to the LLM
- Generate 3 intent options per decision cycle with rationale
- Display AI reasoning in frontend for transparency
- Support action types: EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE

**Non-Goals:**
- Automatic intent execution (intents are recommendations, not actions)
- Real-time multiplayer synchronization
- Complex goal planning beyond immediate intents
- Learning/improvement from past decisions

## Decisions

### 1. Intent Entity Design

**Decision**: `FactionIntent` is a domain entity (not just a DTO) with status lifecycle.

**Rationale**: Intents have identity, lifecycle (PROPOSED → SELECTED → EXECUTED/REJECTED), and can be queried historically. An entity allows tracking intent history and outcome analysis.

```python
class FactionIntent:
    id: str
    faction_id: str
    action_type: ActionType  # EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE
    target_id: str | None  # Location, faction, or resource
    rationale: str  # AI-generated explanation
    priority: int  # 1-3 ranking
    status: IntentStatus  # PROPOSED, SELECTED, EXECUTED, REJECTED
    created_at: datetime
```

**Alternatives considered**:
- Value Object: Rejected because intents need identity for history tracking
- Event-sourced: Overkill for current needs, can evolve later

### 2. Decision Service Architecture

**Decision**: `FactionDecisionService` is an application-layer service that orchestrates RAG + LLM calls.

**Rationale**: Following hexagonal architecture, the service coordinates:
1. Fetch faction context via `RetrievalService`
2. Build prompt with context + faction state
3. Call LLM for intent generation
4. Parse and validate responses
5. Store intents and emit events

```
┌─────────────────────────────────────────────────────────────┐
│                   FactionDecisionService                     │
├─────────────────────────────────────────────────────────────┤
│  1. Build Context:                                          │
│     - Faction resources (gold, food, military)              │
│     - Diplomatic relationships                              │
│     - Recent events (via RAG)                               │
│     - Relevant lore (via RAG)                               │
│                                                             │
│  2. Call LLM:                                               │
│     - Prompt with context + action type definitions         │
│     - Request 3 intent options with rationale               │
│                                                             │
│  3. Post-process:                                           │
│     - Validate response format                              │
│     - Check resource constraints                            │
│     - Store intents, emit IntentGeneratedEvent              │
└─────────────────────────────────────────────────────────────┘
```

### 3. Low Resource Handling

**Decision**: Include explicit resource constraints in prompts and validate responses.

**Rationale**: A faction with low resources should prioritize TRADE or STABILIZE over ATTACK. The prompt will include:
- Current resource levels with thresholds
- Explicit guidance: "If food < 100, prioritize TRADE or STABILIZE"
- Post-LLM validation to reject infeasible intents

### 4. Frontend Integration

**Decision**: Create `FactionIntelPanel` component that shows AI reasoning.

**Rationale**: Transparency into AI decision-making helps users understand world dynamics and creates narrative engagement.

**Component structure**:
- Faction selector dropdown
- "Generate Intents" button
- Intent cards showing: action type, target, rationale, priority
- History accordion for past intents

## Risks / Trade-offs

### Risk: LLM Latency
- **Risk**: Intent generation may take 2-10 seconds, blocking user interaction
- **Mitigation**: Use async generation with loading state; cache results; consider background pre-generation

### Risk: Inconsistent Intent Quality
- **Risk**: LLM may generate unrealistic or contradictory intents
- **Mitigation**: Structured output parsing with validation; fallback to rule-based intents if parsing fails

### Risk: Cost at Scale
- **Risk**: Many factions × frequent decisions = high LLM costs
- **Mitigation**: Batch processing; decision cooldown periods; cheaper models for simple factions

### Trade-off: No Auto-Execution
- **Trade-off**: Intents are recommendations only, not automatically executed
- **Benefit**: User retains control; prevents runaway AI behavior
- **Cost**: Requires manual intent selection for execution

## Migration Plan

1. **Phase 1**: Implement domain entities and events
2. **Phase 2**: Implement `FactionDecisionService` with prompt templates
3. **Phase 3**: Add API endpoint and integrate with existing faction routes
4. **Phase 4**: Build frontend `FactionIntelPanel`
5. **Phase 5**: Integrate with `FactionTickService` for automatic generation on time advance

No rollback needed - this is additive functionality.

## Open Questions

1. **Intent TTL**: How long before proposed intents expire? (Suggest: 7 in-game days)
2. **Max Intents**: How many intents to store per faction? (Suggest: 10 active, unlimited history)
3. **LLM Model**: Which model for intent generation? (Suggest: Start with default, allow config)
