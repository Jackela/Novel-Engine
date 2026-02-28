# Implementation Tasks

## Phase 1: Domain Layer

### Task 1: Create FactionIntent Entity
- [x] Create `src/contexts/world/domain/entities/faction_intent.py`
- [x] Define `ActionType` enum (EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE)
- [x] Define `IntentStatus` enum (PROPOSED, SELECTED, EXECUTED, REJECTED)
- [x] Define `FactionIntent` entity with all required attributes
- [x] Add validation for priority (1-3) and status transitions

### Task 2: Create IntentGeneratedEvent
- [x] Create `src/contexts/world/domain/events/intent_events.py`
- [x] Define `IntentGeneratedEvent` with faction_id, intent_ids, timestamp
- [x] Register event type as `faction.intent_generated`

### Task 3: Create FactionIntentRepository Port
- [x] Create `src/contexts/world/domain/ports/faction_intent_repository.py`
- [x] Define abstract methods: `save()`, `find_by_faction()`, `find_by_id()`, `find_active()`

## Phase 2: Application Layer

### Task 4: Implement FactionDecisionService
- [x] Create `src/contexts/world/application/services/faction_decision_service.py`
- [x] Implement context assembly (resources, diplomacy, territories)
- [x] Integrate with RetrievalService for RAG context
- [x] Build LLM prompt with faction state and action definitions
- [x] Implement intent generation with validation
- [x] Add low-resource constraint handling
- [x] Add fallback behavior for LLM failures

### Task 5: Create FactionIntentRepository Implementation
- [x] Create `src/contexts/world/infrastructure/persistence/in_memory_faction_intent_repository.py`
- [x] Implement all repository methods
- [x] Add max active intents constraint (10 per faction)
- [x] Add auto-expiry for old intents (7 in-game days)

## Phase 3: API Layer

### Task 6: Create Faction Intel API Schemas
- [x] Add schemas to `src/api/schemas/world_schemas.py`:
  - `FactionIntentResponse`
  - `GenerateIntentsRequest`
  - `GenerateIntentsResponse`
  - `SelectIntentResponse`

### Task 7: Create Faction Intel Router
- [x] Create `src/api/routers/faction_intel.py`
- [x] Implement `POST /api/world/factions/{faction_id}/decide`
- [x] Implement `GET /api/world/factions/{faction_id}/intents`
- [x] Implement `POST /api/world/factions/{faction_id}/intents/{intent_id}/select`
- [x] Add rate limiting (1 request per 60 seconds per faction)
- [x] Register router in `app.py`

## Phase 4: Frontend Layer

### Task 8: Add Frontend Types
- [x] Add types to `frontend/src/types/schemas.ts`:
  - `FactionIntent`
  - `ActionType`
  - `IntentStatus`
  - `GenerateIntentsRequest/Response`

### Task 9: Create API Hooks
- [x] Create `frontend/src/features/world/api/factionIntelApi.ts`
- [x] Implement `useGenerateIntents()` mutation
- [x] Implement `useFactionIntents()` query
- [x] Implement `useSelectIntent()` mutation
- [x] Add cache invalidation on generation

### Task 10: Create FactionIntelPanel Component
- [x] Create `frontend/src/features/world/components/FactionIntelPanel.tsx`
- [x] Implement faction selector dropdown
- [x] Implement "Generate Intents" button with loading state
- [x] Create IntentCard component with:
  - Color-coded action type icons
  - Target name display
  - Rationale text
  - Priority badge
  - Select button
  - Status indicator
- [x] Implement history accordion
- [x] Add error handling with retry button
- [x] Ensure WCAG 2.1 AA compliance

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

- [x] Frontend typecheck passes: `cd frontend && npm run type-check`
- [x] Frontend lint passes: `cd frontend && npm run lint`
- [ ] CI pipeline green: `./scripts/ci-check.sh`
