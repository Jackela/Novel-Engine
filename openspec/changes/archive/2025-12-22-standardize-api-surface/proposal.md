# Proposal: Standardize API Surface (Paths + Versioning)

## Why
- The repo currently contains a mix of `/api/*` and `/api/v1/*` references across code and docs, and some modules advertise paths they do not actually implement.
- Frontend-backend drift has already happened (e.g., mismatched “endpoint maps”, docs, and hooks). Without a single, explicit API surface policy, this will keep recurring.
- Long-term refactors (guest filesystem workspaces, typed clients, real UI flows) need a stable contract foundation.

## What Changes
1. **Define a single Product API policy**
   - Canonical “product API” prefix: `/api/*`.
   - No path-based versioning (`/api/v1`, `/api/v2`, …) for first-party product clients.
2. **Unify API discovery + docs**
   - Ensure any “endpoints map” or API reference documents only list routes that exist.
   - Align example code and environment defaults (frontend + scripts) to the canonical paths.
3. **Compatibility rules**
   - Document what `/api` means (current stable product API) and explicitly avoid misleading placeholder version paths.

## Impact
- Touches documentation, configuration, and route registration so the product API is consistently served under `/api/*` only.
- Reduces breakage risk for downstream consumers and enables a typed “SSOT” client later.

## Out of Scope
- Large-scale backend module refactors (handled by `refactor-backend-api-platform`).
- Guest workspace persistence (handled by `add-filesystem-guest-workspaces`).
