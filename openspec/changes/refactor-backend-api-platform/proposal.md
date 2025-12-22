# Proposal: Refactor Backend API Platform (Best-Practice + AI-Friendly)

## Why
- The backend currently exposes multiple server entrypoints and mixed conventions, making it difficult to reason about “the real app” and increasing the risk of route/config drift.
- Business/domain logic is often interleaved with routing concerns, which makes testing and refactoring expensive.
- Long-term roadmap items (guest filesystem workspaces, typed API client, real UI flows, reliable event streaming) require a stable backend platform: app factory, clear module boundaries, consistent errors, and predictable configuration.

## What Changes
1. **Single canonical FastAPI app factory**
   - Introduce a `create_app()` entrypoint that registers routers, middleware, exception handlers, and dependencies without import-time side effects.
2. **Router + service boundaries**
   - Routes live in `routers/*`, domain operations in `services/*`, and persistence behind repository/store interfaces.
3. **Consistent contract + errors**
   - Standardize request/response models and error envelopes across all product endpoints.
4. **OpenAPI as a contract artifact**
   - Ensure the OpenAPI schema produced by the canonical app is consistent and suitable for generating a typed frontend client.

## Impact
- Moves backend code toward a predictable “platform + domains” layout.
- Enables reliable tests (unit + integration) and reduces cross-file coupling, making future features/refactors safer.

## Dependencies
- Should follow `standardize-api-surface` (so routes and docs are stabilized before refactor churn).
- Unblocks `add-filesystem-guest-workspaces` and `refactor-frontend-api-and-ux`.

## Out of Scope
- Large UI/UX work (handled by frontend proposal).
- Implementing filesystem workspaces (handled by `add-filesystem-guest-workspaces`).

