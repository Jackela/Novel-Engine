## Why

Currently, the Novel Engine operates in a timeless void. Events happen, but there is no concept of "when," nor a mechanism to progress time. To support dynamic world simulation (Warzone 5), we need a foundational Time and Calendar system that provides a single source of truth for in-world dates and enables time-based events.

## What Changes

- Introduce a `WorldCalendar` aggregate/entity in the `world` context
- Create domain events for time advancement (`TimeAdvancedEvent`)
- Add API endpoints to get current world time and advance time
- Provide frontend hooks and API client for time state management

## Capabilities

### New Capabilities

- `world-calendar`: Core domain entity and value objects for tracking in-world dates (Year, Month, Day, Era). Includes validation rules (12 months, 30 days per month) and safe time advancement methods.

- `world-time-api`: REST API endpoints for retrieving current world time (`GET /api/world/time`) and advancing time (`POST /api/world/time/advance`). Returns structured responses with display formatting.

### Modified Capabilities

(None - this is a foundational feature with no existing spec changes)

## Impact

- **Domain Layer**: New `WorldCalendar` entity in `src/contexts/world/domain/entities/calendar.py`
- **Application Layer**: New `TimeService` in `src/contexts/world/application/services/time_service.py`
- **API Layer**: New router `src/api/routers/world_time.py`, updated schemas in `src/api/schemas/world_schemas.py`
- **Frontend**: New API client `frontend/src/features/world/api/timeApi.ts`
- **Infrastructure**: New repository port `CalendarRepository` and in-memory implementation
