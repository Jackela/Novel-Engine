# character-service Specification

## Purpose
Define the canonical behavior for character CRUD endpoints and simulation inputs when operating on user-created characters (including validation and error handling).
## Requirements
### Requirement: Authenticated Character Management
- **CHANGE**: “authenticated” requests MAY be satisfied by a first-party guest session. Character CRUD MUST be scoped to the current session/workspace boundary.

#### Scenario: Guest session can create a character
- **GIVEN** a guest session is established
- **WHEN** the session POSTs to `/api/characters` with a valid payload
- **THEN** the API persists the character inside the guest workspace and returns 201 with the created record.

#### Scenario: Guest session lists only its own characters
- **GIVEN** two guest sessions exist and each has created characters
- **WHEN** one session GETs `/api/characters`
- **THEN** it receives only the characters owned by that session/workspace (plus any documented defaults), and never sees the other session’s characters.

### Requirement: Simulation supports user characters
The system SHALL allow simulations to run with user-created characters instead of only seeded names.

#### Scenario: Simulation with user characters
- **WHEN** an authenticated request POSTs to `/simulations` with `character_names` that include user-created characters
- **THEN** the simulation accepts them and returns a story payload that references those characters

#### Scenario: Simulation rejects unknown characters
- **WHEN** a request POSTs to `/simulations` with character names that do not exist or are not accessible
- **THEN** the API returns 4xx with a message listing missing characters and does not start the simulation

