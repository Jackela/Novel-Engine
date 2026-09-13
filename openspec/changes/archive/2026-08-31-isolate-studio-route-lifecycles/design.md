# Design: Studio route and request lifecycle ownership

## Ownership

The route owns visible project identity and Inspector selection. A keyed
project workbench prevents project-local component state from surviving a
`projectId` change. Hooks still guard late completions with an owner identity or
request epoch so correctness does not depend only on React ignoring an
unmounted update.

## Route model

- Path sections: `manuscript`, `outline`, `characters`, `world`, `review`,
  `history`, `export`, `settings`.
- Local Inspector query values: `copilot`, `jobs`, `usage`.
- Copilot is the default and is represented without a query value.
- Selecting Review, History, or Export navigates to that path. Selecting a
  local panel keeps the current authoring path, or returns from a route-owned
  panel to `manuscript`.
- Unknown paths and Inspector values fail closed to the canonical manuscript /
  Copilot state.

## Request lifecycle

Each async owner captures its project/document identity and a monotonically
changing request epoch. Cleanup aborts the transport when supported. Stale read
results may publish no state, errors, revision baselines, or aggregates after
their identity or epoch changes.

Writes use a stricter two-level rule because transport cancellation does not
undo a server commit. A project owner controls aggregate refresh and cache
publication; a document owner controls only active-editor state and focus. If a
save, restore, or proposal acceptance commits after the author leaves document
A, the project owner reconciles A by identity while the document owner prevents
that completion from replacing document B. A per-document draft cache retains
unpersisted text and its base revision across A → B → A. Reconciliation adopts a
new committed baseline for a clean draft; when newer local edits exist, it keeps
them and exposes conflict recovery instead of overwriting them.

A revision restore remains an optimistic write. If its base revision is stale,
the Studio marks the retained local draft as conflicted, refreshes the latest
revision baseline, and leaves a readable retry path; it does not repeatedly
submit the same stale base or silently discard local text.

Whole-book generation uses the streaming proposal transport so Stop and
project changes can abort an in-flight draft without landing a job or usage
event. If atomic acceptance has already started, it may finish and remains a
preserved completed chapter; no later chapter starts.

Export owns its create, catalog, blob, object URL, and synthetic-click stages as
one project-scoped invocation. A project switch aborts every cancellable stage
and invalidates the rest, so the old project can publish neither a catalog nor a
download into the new workbench. Every object URL is revoked on success,
failure, or owner cleanup.

## Load failures

- HTTP 401: replace to `/` for authentication.
- HTTP 404: replace to `/projects` because the addressed project is absent.
- Network, timeout, and server failures: keep the requested URL, show the
  server-authored/readable error, and expose Retry plus Back to projects.

## Accessibility and layout

The APG tab activation callback changes the route before the controlled
selection changes. Arrow/Home/End continue moving focus to the destination
tab. The six tabs use an explicit contained layout with no fixed one-row
height. Native `details`/`summary` remains the disclosure primitive and the
summary stays reachable across responsive transitions.

Pending state belongs to the exact command invocation, not to every control in
the same group. Related controls can be disabled while an invariant-changing
request runs, but only the initiator is announced as busy. Command focus
restoration records both the initiator and the focus state at invocation time;
completion restores focus only when the author has not moved it deliberately.
If the initiator is removed or disabled by the result, the command supplies a
stable workflow-local fallback. Whole-book progress and Stop sit outside the
selected Inspector panel so switching surfaces cannot hide cancellation.
