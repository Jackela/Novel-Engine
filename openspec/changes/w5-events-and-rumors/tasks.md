# Implementation Tasks: Events & Rumors

## Block 1: Application Layer (Sub-agent A)
- [ ] 1.1 Create `RumorPropagationHandler` class
  - Subscribe to `world.time_advanced` event
  - Call `RumorPropagationService.propagate_rumors()`
  - Add proper error handling and logging
  - Ensure isolation from other handlers
- [ ] 1.2 Create `EventRecordingHandler` (optional - for auto-generating events from faction actions)
  - Listen to intent execution events
  - Create HistoryEvent records
  - Generate initial rumors
- [ ] 1.3 Register handlers in startup.py
  - Add to EventBus alongside TimeAdvancedHandler

## Block 2: Infrastructure Layer (Sub-agent B)
- [ ] 2.1 Create `EventRepository` port interface
  - Methods: get_by_id, get_by_world_id, save, delete, list with pagination
- [ ] 2.2 Create `InMemoryEventRepository` adapter
- [ ] 2.3 Create `RumorRepository` port interface
  - Methods: get_by_id, get_active_rumors, get_by_world_id, save, save_all, delete
- [ ] 2.4 Create `InMemoryRumorRepository` adapter
- [ ] 2.5 Verify `LocationRepository.find_adjacent()` implementation
  - Should use parent_id, child_location_ids, and connections
- [ ] 2.6 Register repositories in DI container (startup.py)

## Block 3: API Layer (Sub-agent C)
- [ ] 3.1 Create `routers/world_events.py`
  - GET /api/world/events - List events with pagination
  - POST /api/world/events - Create manual event
  - GET /api/world/events/{id} - Get single event
- [ ] 3.2 Create `routers/world_rumors.py`
  - GET /api/world/locations/{id}/rumors - Get location rumors
  - GET /api/world/rumors/{id} - Get single rumor
- [ ] 3.3 Update `world_schemas.py`
  - HistoryEventResponse schema
  - RumorResponse schema
  - CreateEventRequest schema
- [ ] 3.4 Wire routers in `app.py`

## Block 4: Frontend (Sub-agent D)
- [ ] 4.1 Create/update Zod schemas
  - HistoryEventResponseSchema
  - RumorResponseSchema
- [ ] 4.2 Create TanStack Query hooks
  - useWorldEvents
  - useLocationRumors
  - useCreateEvent
- [ ] 4.3 Create `WorldTimeline.tsx` component
  - Vertical chronological list
  - Event cards with expand/collapse
  - Significance-based styling
- [ ] 4.4 Create `TavernBoard.tsx` component
  - Location-specific rumor display
  - Truth value visual indicators
  - Loading and empty states
- [ ] 4.5 Integrate components into existing pages

## Block 5: Testing & Verification (Swarm)
- [ ] 5.1 Unit tests for RumorPropagationHandler
  - Event subscription works
  - Service called correctly
  - Error handling
- [ ] 5.2 Integration tests for API endpoints
  - Event CRUD operations
  - Rumor retrieval
- [ ] 5.3 Frontend type-check
  - `npm run type-check`
- [ ] 5.4 Frontend lint
  - `npm run lint`
- [ ] 5.5 Run full pytest suite
  - Ensure no regressions
  - Verify EventBus multi-handler behavior
- [ ] 5.6 Silent-failure verification
  - Verify rumor propagation failures don't affect faction ticks
  - Check error logging

## Verification Checklist
- [ ] All 5 blocks complete
- [ ] Tests passing (backend + frontend)
- [ ] Manual test: Create event → Advance time → Verify rumor spread
- [ ] UI renders correctly in both light/dark mode
- [ ] No console errors
