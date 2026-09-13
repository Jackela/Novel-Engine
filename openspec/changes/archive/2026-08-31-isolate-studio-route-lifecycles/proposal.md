# Isolate Studio route and request lifecycles

## Why

The Studio currently lets the URL and component state compete for Inspector
selection. On route-owned panels, a tab can receive focus without becoming
selected; on authoring routes, the same panel can change without a URL change.
Project and document hooks also retain unscoped state while route identities
change, so late responses can appear in or mutate the wrong workbench.

The canonical load-failure requirement is also stale: it requires every
failure to disappear behind a redirect, while the implementation intentionally
keeps operational failures visible but offers no working retry action.

## What changes

- Make the URL the only owner of Inspector selection. Review, History, Export,
  and Settings remain path sections; Copilot, Jobs, and Usage use a validated
  `inspector` query value on an authoring section.
- Treat `projectId` as the lifecycle key for the complete Studio workbench and
  scope asynchronous publication to the originating project/document/request.
- Abort proposal, whole-book, search, jobs, usage, revision, and project loads
  when their owner changes wherever the transport supports cancellation.
- Classify initial load failures: unauthenticated returns to entry, missing
  projects return to the library, and operational failures stay visible with
  Retry and Back actions.
- Keep route-owned panels exclusive, contain all six Inspector tabs, and keep
  the native Inspector disclosure reachable at every supported width.

## Non-goals

- No new router, state-management, or component dependency.
- No persistence of drafts or Inspector state outside the URL.
- No change to the atomic server-side semantics of proposal acceptance.

## Validation

- Route integration tests for click, keyboard, deep-link, Back, and Forward.
- Deferred and reverse-completion tests across project/document identity
  changes.
- Browser geometry checks for tabs and responsive disclosure recovery.
- Frontend full checks, React Doctor, production browser workflows, and strict
  OpenSpec validation.
