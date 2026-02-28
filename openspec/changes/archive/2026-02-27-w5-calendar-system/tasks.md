## 1. Domain Layer - Events & Ports

- [x] 1.1 Create `src/contexts/world/domain/events/time_events.py` with `TimeAdvancedEvent` domain event
- [x] 1.2 Create `src/contexts/world/domain/ports/calendar_repository.py` with `CalendarRepository` protocol

## 2. Domain Layer - Calendar Entity

- [x] 2.1 Create `src/contexts/world/domain/entities/calendar.py` with `WorldCalendar` entity
- [x] 2.2 Implement date validation (month 1-12, day 1-30, year >= 1)
- [x] 2.3 Implement `advance_days(n)` method with rollover logic
- [x] 2.4 Implement `display_string` property
- [x] 2.5 Emit `TimeAdvancedEvent` from `advance_days` method

## 3. Domain Layer - Tests

- [x] 3.1 Create `tests/unit/contexts/world/domain/test_calendar.py`
- [x] 3.2 Write tests for date validation constraints
- [x] 3.3 Write tests for day advancement within month
- [x] 3.4 Write tests for month rollover
- [x] 3.5 Write tests for year rollover
- [x] 3.6 Write tests for backward time prevention
- [x] 3.7 Write tests for event emission

## 4. Application & Infrastructure Layer

- [x] 4.1 Create `src/contexts/world/infrastructure/persistence/in_memory_calendar_repository.py`
- [x] 4.2 Create `src/contexts/world/application/services/time_service.py` with `get_time()` and `advance_time(days)`
- [x] 4.3 Write integration tests for `TimeService`

## 5. API Layer - Schemas & Router

- [x] 5.1 Update `src/api/schemas/world_schemas.py` with `WorldTimeResponse` schema
- [x] 5.2 Add `AdvanceTimeRequest` schema with validation (days > 0)
- [x] 5.3 Create `src/api/routers/world_time.py` with GET `/api/world/time` endpoint
- [x] 5.4 Add POST `/api/world/time/advance` endpoint
- [x] 5.5 Register world_time router in `src/api/main_api_server.py`

## 6. API Layer - Tests

- [x] 6.1 Create `tests/integration/api/test_world_time.py`
- [x] 6.2 Write test for GET time endpoint
- [x] 6.3 Write test for POST advance endpoint
- [x] 6.4 Write tests for validation error responses

## 7. Frontend - Types & API Client

- [x] 7.1 Update `frontend/src/types/schemas.ts` with `WorldTimeResponse` and `AdvanceTimeRequest` types
- [x] 7.2 Create `frontend/src/features/world/api/timeApi.ts` with TanStack Query hooks
- [x] 7.3 Implement `useWorldTime()` query hook
- [x] 7.4 Implement `useAdvanceTime()` mutation hook

## 8. Verification

- [x] 8.1 Run `pytest tests/unit/contexts/world/domain/test_calendar.py -v`
- [x] 8.2 Run `pytest tests/integration/api/test_world_time.py -v`
- [x] 8.3 Run `npm run type-check` in frontend
- [x] 8.4 Run `./scripts/ci-check.sh` for full CI validation
