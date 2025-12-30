# Design: Frontend API SSOT + Usable Flows

## Target State
- A single API module (`frontend/src/lib/api/*`) owns:
  - base URL resolution
  - session bootstrap (guest)
  - request/response typing
  - error normalization
- Feature code uses hooks that compose the SSOT client and expose:
  - `data` / `isLoading` / `error`
  - stable query keys
  - cancellation and retry policies

## UX Flows (guest-first)
1. Landing (`/`)
   - “Continue as guest” starts/resumes a guest session.
2. Workspace/Dashboard (`/dashboard`)
   - Shows workspace status (guest badge, save indicator).
   - Lists characters with create/edit/delete.
3. Run (`/runs/:id` or inline panel)
   - Starts a simulation and renders the resulting narrative.

## Error Handling
- All API errors are normalized into a small set of categories (validation, auth/session, network, server).
- UI renders consistent empty/loading/error patterns with actionable guidance.

