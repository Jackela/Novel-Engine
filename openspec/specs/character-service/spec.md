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

### Requirement: Normalized character list payload
`GET /api/characters` MUST return an array of character objects (not just names) including `id`, `name`, `status`, `type`, `updated_at`, and `workspace_id`, ordered deterministically (e.g., newest `updated_at` first) and scoped to the caller’s workspace.

#### Scenario: List returns normalized objects in order
- **GIVEN** a workspace with three characters updated at different times
- **WHEN** the client calls `GET /api/characters`
- **THEN** the response contains objects with `id`, `name`, `status`, `type`, `updated_at`, `workspace_id`
- **AND** the array is sorted by `updated_at` descending
- **AND** characters from other workspaces do not appear.

### Requirement: Detail/list field parity with cache hints
The list response MUST include the minimal fields required to render dashboard tiles without extra detail calls, and responses SHOULD emit cache validators (ETag/Last-Modified) so clients can reuse data across list/detail requests.

#### Scenario: Dashboard renders from list response alone
- **WHEN** the frontend consumes the list response to populate the world map/dashboard tiles
- **THEN** it can render names, status/type, and last-updated timestamps without issuing immediate per-character detail fetches
- **AND** the server provides ETag or Last-Modified so unchanged lists can be cached client-side.

