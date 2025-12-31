## ADDED Requirements
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
