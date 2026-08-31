# Design: document-scoped Lore status editor

## Constraints

- A Lore status draft belongs to exactly one `character` or `world` document.
- The server-observed status remains the saved baseline; the form owns only
  the unsaved selection.
- The existing `useStudioActions` mutation path continues to own transport,
  pending state, project patching, and error publication.
- The save callback must settle only after that mutation path finishes.
- Switching documents while a request is pending must not focus or mutate the
  newly selected document's form.
- No new dependency, generic workflow engine, result union, or server change.

## Current design

`StudioLoreStatusPanel` receives a full `StudioDocument` and initializes local
state once. Its comment assumes a parent-provided React `key`, but the
composition does not provide one. Separately, `useStudioPageModel` wraps the
async action in a callback that returns `void`. These two shallow seams make
correct identity and completion behavior optional at the call site.

## Selected design

The page model adapts the active domain document into a concrete, nullable
Lore editor model:

```ts
interface InspectorLoreStatusModel {
  readonly documentId: string;
  readonly savedStatus: LoreStatus;
  readonly submit: (status: LoreStatus) => Promise<void>;
}
```

Eligibility remains concrete in the page model. Non-Lore documents produce
`null`; the form never receives a document kind or an entire domain object.

`StudioLoreStatusPanel` accepts the same three values plus the existing
pending flag. It renders a private stateful form with
`key={documentId}`. The public module therefore owns the identity reset: a
caller cannot accidentally reuse document A's draft for document B. The
private form awaits `submit` before restoring focus. If it unmounts during the
request, its ref is null and it cannot steal focus from the new document.

`useStudioPageModel` uses a pure adapter that binds `submit` to the active
document ID captured by that render and directly returns
`changeLoreStatus(...)`. The current action keeps its functional project
update, global Inspector error behavior, and duplicate submission guard.

The private form records a completion-time focus request, then restores focus
from an effect only after React has committed `isSaving=false`. This avoids
targeting a still-disabled button when the mutation Promise settles before the
parent pending-state render. If the form unmounts, the request disappears with
that document identity and cannot move focus in the next form.

## Alternatives considered

### Parent-only `key`

This is the fewest changed lines, but it repeats the exact failure mode: the
module's correctness depends on every composition site remembering an
invisible React identity rule. Rejected in favor of an internally enforced
key.

### Effect-based state synchronization

Synchronizing local state in an effect can expose a stale render and can
overwrite a same-document unsaved draft when unrelated props update. A keyed
private form expresses document identity directly.

### Generic document workflow status port

A generic enum/status renderer could abstract options, labels, and target
kinds. Lore is currently the only production instance, so this would create a
hypothetical seam and move Lore rules into configuration. Rejected until a
second genuinely matching workflow exists.

### Form-owned cross-document operation registry

Keeping pending/error/retry records for several hidden documents would deepen
the form but duplicate the existing action owner and expand this P0 repair
into a new state subsystem. The current global mutation guard deliberately
allows one Lore status save at a time, so this is out of scope.

## Verification

- A component regression test changes an unsaved selection for document A,
  rerenders the same public module for document B, and observes B's saved
  status immediately.
- A deferred submit test proves focus restoration occurs after, not before,
  Promise settlement.
- A pending-state harness proves focus waits for the committed idle render;
  another regression settles document A after switching to B and proves A
  cannot steal B's focus.
- Action tests prove the correct document ID/status are sent, pending spans
  the request, success patches only the target, and failure leaves project
  state unchanged while publishing the error.
- A page-model adapter test proves the exact mutation Promise is returned, and
  an Inspector regression proves a Lore failure remains visible even while the
  contextual Export tab is selected.
- Frontend lint, format, type-check, unit tests, build, repository gates, and
  strict OpenSpec validation remain green.
