## ADDED Requirements

### Requirement: API returns current world time

The system SHALL provide a `GET /api/world/time` endpoint that returns the current in-world date.

#### Scenario: Successful time retrieval

- **WHEN** GET /api/world/time is called
- **THEN** the response SHALL have status 200
- **AND** the body SHALL contain:
  ```json
  {
    "year": <integer>,
    "month": <integer 1-12>,
    "day": <integer 1-30>,
    "era_name": "<string>",
    "display_string": "<formatted date>"
  }
  ```

#### Scenario: Default time on fresh system

- **GIVEN** a fresh system with no time set
- **WHEN** GET /api/world/time is called
- **THEN** the response SHALL return the default calendar state (year=1, month=1, day=1, era_name="First Age")

---

### Requirement: API advances world time

The system SHALL provide a `POST /api/world/time/advance` endpoint that advances the in-world time by a specified number of days.

#### Scenario: Successful time advancement

- **GIVEN** current time at year=1042, month=5, day=10
- **WHEN** POST /api/world/time/advance is called with body `{"days": 5}`
- **THEN** the response SHALL have status 200
- **AND** the body SHALL contain the updated time with day=15
- **AND** subsequent GET /api/world/time SHALL return the updated time

#### Scenario: Advancing across month boundary

- **GIVEN** current time at year=1042, month=5, day=28
- **WHEN** POST /api/world/time/advance is called with body `{"days": 5}`
- **THEN** the response SHALL contain month=6, day=3

#### Scenario: Invalid days parameter rejected

- **WHEN** POST /api/world/time/advance is called with body `{"days": 0}`
- **THEN** the response SHALL have status 422 (Validation Error)
- **AND** the error message SHALL indicate days must be positive

#### Scenario: Negative days rejected

- **WHEN** POST /api/world/time/advance is called with body `{"days": -5}`
- **THEN** the response SHALL have status 422 (Validation Error)

#### Scenario: Missing days parameter rejected

- **WHEN** POST /api/world/time/advance is called with body `{}`
- **THEN** the response SHALL have status 422 (Validation Error)

---

### Requirement: Request and response schemas

The API SHALL use the following Pydantic schemas defined in `world_schemas.py`:

#### WorldTimeResponse Schema
```python
class WorldTimeResponse(BaseModel):
    year: int
    month: int
    day: int
    era_name: str
    display_string: str
```

#### AdvanceTimeRequest Schema
```python
class AdvanceTimeRequest(BaseModel):
    days: int = Field(..., gt=0, description="Number of days to advance")
```

#### Scenario: Response matches schema

- **WHEN** any world time endpoint returns data
- **THEN** the response SHALL validate against WorldTimeResponse schema

---

### Requirement: Frontend types match API schemas

The frontend SHALL have TypeScript types in `frontend/src/types/schemas.ts` that match the API schemas exactly.

#### Scenario: TypeScript type generation

- **WHEN** the frontend imports WorldTimeResponse type
- **THEN** it SHALL have properties: year (number), month (number), day (number), era_name (string), display_string (string)

#### Scenario: TypeScript type for advance request

- **WHEN** the frontend imports AdvanceTimeRequest type
- **THEN** it SHALL have property: days (number)
