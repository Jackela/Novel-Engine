# Restore project settings update

## Why

The Studio exposes a Project settings form and its frontend client already
attempts `PATCH /api/projects/:projectId`, but the TypeScript backend has no
matching route. Saving a title, description, or provider therefore reaches a
404 instead of persisting the edit. This is a confirmed compatibility gap: the
surface appears complete, yet reload returns the old project state.

The repair needs its own contract because it is a write boundary, not another
exception to the bounded Project shell. A settings mutation must be scoped to
the Owner, protected by the existing CSRF double submit, preserve omitted
fields, and return only project scalars so editing one field never rematerializes
document structure or bodies.

## What Changes

- Add CSRF-protected `PATCH /api/projects/:projectId` for an authenticated Owner.
- Accept a strict top-level object with optional `title`, `description`, and
  `settings`, requiring at least one of them. Trim and validate title and
  description under the same constraints as project creation; reject unknown
  top-level fields and non-object settings.
- Preserve every omitted project field. An included `settings` object replaces
  the complete stored settings object; callers that want to retain other keys
  must include them, matching the current frontend's merge-before-send behavior.
- Commit the selected scalar changes and one new `updated_at` atomically through
  an Owner-scoped store operation, then return the strict scalar Project payload
  with no `documents`, `volumes`, revision data, or bodies.
- Merge the returned scalars into the current frontend Project shell without
  replacing structural arrays or the active Document. Give the settings request
  project/intent ownership, explicit pending and failure state, stale-response
  rejection, and accessible focus recovery.
- Regenerate the deliberate OpenAPI baseline and frontend types, then verify
  title, description, and provider persistence through a real reload.

## Impact

- Adds one write operation to the existing project resource path and one
  application/store update seam.
- Affects project request schemas, project routes/service/store ports, OpenAPI,
  generated frontend types, API contract parsing, Settings action lifecycle,
  and tests.
- The response deliberately uses the existing strict scalar Project payload,
  not Project shell. Frontend consumers merge it into their current shell.
- No schema migration, dependency, environment variable, document/revision
  contract, project-shell shape, or Provider configuration contract changes.

## Non-goals

- No PUT replacement route, JSON Patch, per-key settings merge, settings schema
  registry, provider credential editing, provider health check, or optimistic
  concurrency token.
- No document, volume, Review, Export, Job, Usage, or active-body refresh after
  a settings save.
- No rewriting of ADR-0003. The missing route is recorded as a historical
  cutover compatibility gap; this change specifies the repair in current
  product terms.

## Validation

- Contract-first real API/store tests for each field alone and together,
  preservation of omitted fields, complete settings replacement, trimming,
  request bounds, empty/unknown/invalid bodies, updated timestamp, exact scalar
  response shape, and atomic failure.
- Authorization tests proving unauthenticated and CSRF-invalid requests do not
  mutate, and missing/cross-Owner projects share one 404 envelope after the
  write guards pass.
- Frontend tests for scalar-only parsing/merge, pending and duplicate-submit
  behavior, project/intent stale responses, independent error recovery, and
  focus that respects deliberate user movement.
- OpenAPI/generated-type drift plus a TypeScript-backend Playwright workflow
  that saves title, description, and provider and observes all three after page
  reload.
- Full server/frontend gates, strict OpenSpec, required CI, and independent
  fixed-SHA standards/security/UX review before archive.
