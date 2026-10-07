# Reconcile the draft chapter with the shipped rescue write

## Why

The 2026-10-01 devil's-advocate campaign fixed DR-002 — the most common data-loss
path, where a document switch or an editor unmount dropped edits still inside
the 1.5-second autosave debounce — and shipped a **rescue write**:
`frontend/src/features/studio/hooks/useDocumentDraftRescue.ts` hands the newest
local text to one detached, conflict-checked draft save when the author leaves
the Document. The browser workflow
`frontend/tests/e2e-ts/workflows/studio_switch.spec.ts` pins the observable
shape: exactly one save for the departing project, none for the next one, no
late duplicate after the debounce window, and the departing Document
rehydrating with the rescued text while re-entry saves nothing.

The spec still describes the pre-DR-002 contract in two requirements:

- `In-memory document drafts` states the Draft "MUST NOT persist per Document
  across selection changes, route departure, or page reload", lists route
  departure among the ways an active Draft simply ends, and its scenario
  "Switching documents discards the draft" stops at the discard with no rescue
  write.
- `Project-scoped Studio resource lifecycle` restates "A deliberate Document
  switch MUST discard an edited local Draft ... it MUST NOT persist that Draft
  by inactive Document", and its scenario "An unpersisted draft does not survive
  document navigation" asserts that Document A returns without the pre-switch
  text.

Shipped, tested behavior therefore contradicts the SSOT. This change reconciles
the requirement text and scenario steps with what the product does; it changes
no behavior.

## What Changes

- `In-memory document drafts`: a departure — a deliberate switch or leaving the
  Studio surface with the Document open — must hand the departing Document's
  newest content and title to one rescue write before the local Draft is
  discarded; the rescue's result is observable only as an accepted revision of
  that Document, read back on reopen; a rescue that fails, conflicts, or never
  lands stays silent; an unresolved conflict Draft never enters the rescue
  path. Adds scenarios for the Studio departure, the reopen read-back, the
  conflict exception, and silent rescue failure; the discard scenario and the
  requirement's "the Draft ends only by ..." list are reconciled with them.
- `Project-scoped Studio resource lifecycle`: the switch paragraph hands a
  non-conflicted Draft to its one rescue write before discarding, keeps the
  unresolved conflict Draft out of the rescue path, and binds a rescue write to
  the project and Document that own it; "An unpersisted draft does not survive
  document navigation" now states what does not survive (inactive client-side
  Draft state) and what can return instead (the revision an accepted rescue
  write committed); the late-completion scenarios count a rescue write as a
  covered save/completion.
- No other requirement text changes.

## Impact

- Spec-only: no code, no schema, no API shape, no migration, no dependency, no
  configuration. The described behavior already shipped in commit `a39e38d5`
  (`useDocumentDraftRescue.ts` plus `documentDraftPersistence.ts`; unit cases in
  `useDocumentDraft.selection`, `.lifecycle`, `.reconciliation`, `.external`,
  and `.autosave-recovery`; the browser workflow `studio_switch.spec.ts`) and is
  recorded as completed in `docs/audits/2026-10-01-devil-advocate-fix-backlog.md`
  (DR-002).
- Retroactive reconciliation: the DR-002 fix rewrote the tests that had fixed
  "switch discards" as expected behavior but left this spec text untouched;
  this change backfills the formal delta. Tasks are drafting, validation, and
  archiving only.
- Scenario names of both modified requirements are preserved verbatim: OpenSpec
  refuses a MODIFIED block that omits a scenario name the current spec still has
  ("archive refuses to drop them"), so the rescue semantics are carried by the
  requirement bodies and scenario steps; only the scenarios this change adds get
  new names.
- Out of scope: the `beforeunload` unsaved-edit guard (also DR-002) and the
  optional sessionStorage crash recovery are not part of this reconciliation.
