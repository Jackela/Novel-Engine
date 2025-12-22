# Design: API Surface Standardization

## Scope
This change standardizes the **product API surface** (the set of endpoints used by the app frontend and core product integrations). It does not attempt to reorganize internal tooling/observability endpoints unless they overlap with product routes.

## Policy

### Canonical Prefix
- Canonical prefix for the product API is **`/api`**.
- The API MUST NOT require path-based versioning for first-party clients.

### Versioned Alias
- A versioned alias **`/api/v1`** MUST exist for v1 endpoints.
- `/api/v1/*` MUST behave identically to `/api/*` for the v1 surface.

### Version Semantics
- `/api/*` is defined as “current stable product API”.
- Introducing a new stable version (e.g., v2) requires:
  - explicit proposal
  - migration guidance
  - compatibility window for `/api/v1`

## Practical Outcomes
- Frontend defaults to `/api` to avoid churn when a new version is introduced.
- External consumers can pin to `/api/v1` when stability is required.

## Backward Compatibility
- If any legacy paths exist (e.g., `/characters`), they MUST either:
  - remain as thin redirects/aliases with deprecation signals, or
  - be removed with an explicit breaking-change proposal.

