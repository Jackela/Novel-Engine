# Design: API Surface Standardization

## Scope
This change standardizes the **product API surface** (the set of endpoints used by the app frontend and core product integrations). It does not attempt to reorganize internal tooling/observability endpoints unless they overlap with product routes.

## Policy

### Canonical Prefix
- Canonical prefix for the product API is **`/api`**.
- The product API MUST NOT use path-based versioning (`/api/v1`, `/api/v2`, …).

### Version Semantics
- `/api/*` is defined as “current stable product API”.
- Introducing a new stable version requires an explicit proposal and migration plan, but this change does not introduce any versioned path prefixes.

## Practical Outcomes
- Frontend and docs default to `/api`.

## Backward Compatibility
- If any legacy paths exist (e.g., `/characters`), they MUST either:
  - remain as thin redirects/aliases with deprecation signals, or
  - be removed with an explicit breaking-change proposal.
