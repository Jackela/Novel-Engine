# Fix Lore status editor identity and completion semantics

## Why

The Studio Lore status editor keeps its selected value in local React state,
but the component is currently reused when the active Lore document changes.
An unsaved selection from document A can therefore appear for document B and
be submitted against B. The page model also discards the save Promise, so the
form's focus-restoration contract completes before the remote save finishes.

Lore lifecycle status is a canon gate: only `stable` entries participate in
generation context. The editor must bind every draft and save to one explicit
document identity.

## What Changes

- Define a document-scoped Lore status editor contract in the
  `novel-engine` capability.
- Replace the editor's broad `StudioDocument` input with the minimum view
  model: document identity, saved status, pending state, and an asynchronous
  submit function.
- Make the Lore module enforce React identity internally so callers cannot
  forget the document reset boundary.
- Preserve the existing action owner for API calls, pending state, project
  updates, and error publication; return its real Promise to the form.
- Add regression coverage for cross-document draft isolation and save
  completion ordering.

## Impact

- Frontend-only change under `frontend/src/features/studio/`.
- No API, OpenAPI, database, migration, provider, or Lore injection change.
- Existing `draft | stable | deprecated` semantics and ADR-0006 remain
  authoritative.
- The public component seam becomes smaller and strictly asynchronous.
