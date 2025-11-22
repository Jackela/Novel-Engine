## ADDED Requirements
### Requirement: Authenticated Character Management
The system SHALL provide authenticated endpoints for users to create and retrieve their characters without relying on seeded demo data.

#### Scenario: Create character succeeds
- **WHEN** an authenticated request POSTs to `/api/characters` with a valid payload (name, background, traits, optional skills/relationships)
- **THEN** the API persists the character for that user and returns 201 with the created record (id, timestamps, sanitized fields)

#### Scenario: Create character validation fails
- **WHEN** an authenticated request POSTs to `/api/characters` with missing required fields or invalid data (e.g., overly long name/traits)
- **THEN** the API returns 400 with a clear error message and does not persist the character

#### Scenario: List characters returns user data
- **WHEN** an authenticated request GETs `/api/characters`
- **THEN** the response includes user-created characters plus baseline defaults (if any) without duplicates, and omits characters the user lacks access to

### Requirement: Simulation supports user characters
The system SHALL allow simulations to run with user-created characters instead of only seeded names.

#### Scenario: Simulation with user characters
- **WHEN** an authenticated request POSTs to `/simulations` with `character_names` that include user-created characters
- **THEN** the simulation accepts them and returns a story payload that references those characters

#### Scenario: Simulation rejects unknown characters
- **WHEN** a request POSTs to `/simulations` with character names that do not exist or are not accessible
- **THEN** the API returns 4xx with a message listing missing characters and does not start the simulation
