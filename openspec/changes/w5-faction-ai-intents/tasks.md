# Implementation Tasks

## Phase 1: Domain Layer

### Task 1: Create FactionIntent Entity
- [ ] Create `src/contexts/world/domain/entities/faction_intent.py`
- [ ] Define `ActionType` enum (EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE)
- [ ] Define `IntentStatus` enum (PROPOSED, SELECTED, EXECUTED, REJECTED)
- [ ] Define `FactionIntent` entity with all required attributes
- [ ] Add validation for priority (1-3) and status transitions

### Task 2: Create IntentGeneratedEvent
- [ ] Create `src/contexts/world/domain/events/intent_events.py`
- [ ] Define `IntentGeneratedEvent` with faction_id, intent_ids, timestamp
- [ ] Register event type as `faction.intent_generated`

### Task 3: Create FactionIntentRepository Port
- [ ] Create `src/contexts/world/domain/ports/faction_intent_repository.py`
- [ ] Define abstract methods: `save()`, `find_by_faction()`, `find_by_id()`, `find_active()`

## Phase 2: Application Layer

### Task 4: Implement FactionDecisionService
- [ ] Create `src/contexts/world/application/services/faction_decision_service.py`
- [ ] Implement context assembly (resources, diplomacy, territories)
- [ ] Integrate with RetrievalService for RAG context
- [ ] Build LLM prompt with faction state and action definitions
- [ ] Implement intent generation with validation
- [ ] Add low-resource constraint handling
- [ ] Add fallback behavior for LLM failures

### Task 5: Create FactionIntentRepository Implementation
- [ ] Create `src/contexts/world/infrastructure/persistence/in_memory_faction_intent_repository.py`
- [ ] Implement all repository methods
- [ ] Add max active intents constraint (10 per faction)
- [ ] Add auto-expiry for old intents (7 in-game days)

## Phase 3: API Layer

### Task 6: Create Faction Intel API Schemas
- [ ] Add schemas to `src/api/schemas/world_schemas.py`:
  - `FactionIntentResponse`
  - `GenerateIntentsRequest`
  - `GenerateIntentsResponse`
  - `SelectIntentResponse`

### Task 7: Create Faction Intel Router
- [ ] Create `src/api/routers/faction_intel.py`
- [ ] Implement `POST /api/world/factions/{faction_id}/decide`
- [ ] Implement `GET /api/world/factions/{faction_id}/intents`
- [ ] Implement `POST /api/world/factions/{faction_id}/intents/{intent_id}/select`
- [ ] Add rate limiting (1 request per 60 seconds per faction)
- [ ] Register router in `app.py`

## Phase 4: Frontend Layer

### Task 8: Add Frontend Types
- [ ] Add types to `frontend/src/types/schemas.ts`:
  - `FactionIntent`
  - `ActionType`
  - `IntentStatus`
  - `GenerateIntentsRequest/Response`

### Task 9: Create API Hooks
- [ ] Create `frontend/src/features/world/api/factionIntelApi.ts`
- [ ] Implement `useGenerateIntents()` mutation
- [ ] Implement `useFactionIntents()` query
- [ ] Implement `useSelectIntent()` mutation
- [ ] Add cache invalidation on generation

### Task 10: Create FactionIntelPanel Component
- [ ] Create `frontend/src/features/world/components/FactionIntelPanel.tsx`
- [ ] Implement faction selector dropdown
- [ ] Implement "Generate Intents" button with loading state
- [ ] Create IntentCard component with:
  - Color-coded action type icons
  - Target name display
  - Rationale text
  - Priority badge
  - Select button
  - Status indicator
- [ ] Implement history accordion
- [ ] Add error handling with retry button
- [ ] Ensure WCAG 2.1 AA compliance

## Phase 5: Integration & Testing

### Task 11: Wire Dependencies
- [ ] Register FactionIntentRepository in DI container
- [ ] Wire FactionDecisionService with LLM and RAG services
- [ ] Add EventBus integration for IntentGeneratedEvent

### Task 12: Write Tests
- [ ] Unit tests for FactionIntent entity
- [ ] Unit tests for FactionDecisionService
- [ ] Integration tests for API endpoints
- [ ] Component tests for FactionIntelPanel
- [ ] Add test fixtures for faction contexts

## Verification Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Frontend typecheck passes: `cd frontend && npm run type-check`
- [ ] Frontend lint passes: `cd frontend && npm run lint`
- [ ] CI pipeline green: `./scripts/ci-check.sh`
