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
- [x] Register FactionIntentRepository in DI container
- [x] Wire FactionDecisionService with LLM and RAG services (stub for future)
- [x] Add EventBus integration for IntentGeneratedEvent

### Task 12: Write Tests
- [x] Unit tests for FactionIntent entity
- [x] Unit tests for FactionDecisionService
- [x] Integration tests for API endpoints
- [ ] Component tests for FactionIntelPanel (deferred - requires Playwright setup)
- [x] Add test fixtures for faction contexts

## Verification Checklist

- [x] Frontend typecheck passes: `cd frontend && npm run type-check`
- [x] Frontend lint passes: `cd frontend && npm run lint`
- [x] CI pipeline green: `./scripts/ci-check.sh`

---

## Code Review Fixes Applied (2026-03-02)

### Phase 1: CRITICAL (Issues 1-5)

#### Issue 1: Fallback Repository Masks DI Failures
- [x] Updated `get_repository()` in `faction_intel.py` to only use fallback in testing mode
- [x] Raises `RuntimeError` in production when repository not configured

#### Issue 2: Event Publishing Failure Swallowed
- [x] Added `event_published: bool` field to `GenerateIntentsResponse` schema
- [x] Endpoint now tracks and returns event publication status

#### Issue 3: Startup Initialization Continues on Error
- [x] Added `faction_intent_repository_available` flag to `app.state`
- [x] Updated startup.py to set flag based on registration success

#### Issue 4: Missing Prompt Template YAML
- [x] Created `src/contexts/world/infrastructure/prompts/faction_intents.yaml`
- [x] Includes resource constraint guardrails and historical grievance context

#### Issue 5: No LLM Response Parsing/Validation
- [x] Added `_parse_llm_response()` with multi-strategy JSON parsing
- [x] Added `_validate_intents()` for action type validation and resource constraint filtering

### Phase 2: HIGH (Issues 6-9)

#### Issue 6: Global EventBus Race Condition
- [x] Removed global `_event_bus` variable and `set_event_bus()` function
- [x] Added `_get_event_bus(request)` that reads from `request.app.state.event_bus`
- [x] Updated startup.py to remove `set_event_bus()` call

#### Issue 7: RAG Failure Silently Continues
- [x] Modified `_enrich_context_with_rag()` to return `tuple[DecisionContext, bool]`
- [x] Added `rag_enriched: bool` field to `IntentGeneratedEvent` dataclass
- [x] Event payload now includes RAG status

#### Issue 8: No LLM Timeout Handling
- [x] Added `LLM_TIMEOUT_SECONDS = 30` constant
- [x] Documented `asyncio.wait_for()` pattern in `_try_llm_generation()`

#### Issue 9: RAG Query Not Specific for Grievances
- [x] Updated query to include specific keywords: "conflicts wars betrayals grievances battles alliances treaties"

### Phase 3: MEDIUM (Issues 10-12)

#### Issue 10: Missing Repository Tests
- [x] Created `tests/unit/contexts/world/infrastructure/persistence/test_in_memory_faction_intent_repository.py`
- [x] Tests for thread safety, max intents constraint, expiry, action type filtering

#### Issue 11: Missing API Validation Tests
- [x] Extended `tests/integration/api/test_faction_intel_api.py`
- [x] Tests for invalid context_hints type, empty faction_id, terminal state selection

#### Issue 12: Missing EventBus Integration Tests
- [x] Created `tests/integration/events/test_intent_event_bus.py`
- [x] Tests for handler receiving events, event validation (max 3 intents), rag_enriched field
