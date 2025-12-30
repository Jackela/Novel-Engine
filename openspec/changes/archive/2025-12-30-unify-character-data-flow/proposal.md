# Change: Unify character data flow

## Why
- The character listing/detail APIs and frontend queries return mixed shapes (names vs. objects), causing redundant transforms and cache misses.
- Dashboard tiles and orchestration flows need consistent ordering and workspace scoping to avoid empty states in guest/mock contexts.

## What Changes
- Standardize `/api/characters` to return normalized objects (id, name, status/type, updated_at) in deterministic order, scoped per workspace.
- Define minimal required fields for dashboard datasets and ensure downstream transforms align.
- Add cache/etag hints so clients can reuse list/detail data without duplicate fetches.

## Impact
- Affected specs: `character-service`
- Affected code: character API list/detail endpoints, DTO transforms, React Query keys/cache hydration.
