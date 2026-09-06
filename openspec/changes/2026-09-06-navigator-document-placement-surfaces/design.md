# Design: Navigator deletion and placement command surfaces

## Server contract basis (read before designing; zero server changes)

Both commands wrap routes that already exist and are server-covered. The
product semantics below follow the server contracts, not assumptions:

- `DELETE /api/projects/:projectId/documents/:documentId`
  (`server/src/contexts/studio/interface/http/document_routes.ts:126` →
  `DocumentService.removeDocument` → `dropDocument`) answers 204 with no
  body. Its only refusal beyond auth/scope is `SnapshotConflict` (409
  `SNAPSHOT_CONFLICT`) when the document is referenced by any snapshot
  row: snapshot authority outranks removal. There is **no running-job
  gate** — the Job contract executes synchronously inside its request, so
  no server-side job outlives the delete request. The UI therefore adds
  no job gate; an SSE proposal stream against a deleted document fails
  through its existing failure surface.
- `PUT /api/projects/:projectId/documents/:documentId/volume`
  (`document_routes.ts:176` → `VolumeService.placeChapter` →
  `placeDocumentInVolume`) accepts `{ volume_id }` for **chapters only**
  (non-chapters refuse), lands the chapter at the target volume's tail,
  does **not** mint a revision (`current_revision_id` is unchanged), and
  returns the complete current Document. A missing target volume or
  document is 404; a full target volume refuses permanently with the 422
  `STRUCTURE_CAPACITY_EXCEEDED` envelope (#461).

## Confirmation and focus semantics (deletion)

Deletion is the Studio's only irreversible document command, so the
trigger alone must never execute it. Options considered:

1. `window.confirm` — rejected: unstyled, blocks the event loop, no
   deliberate focus movement, and opaque to role-based browser tests.
2. A modal dialog — rejected: heavier than the decision; the Navigator is
   a side rail, and a modal over a 44px row is disproportionate.
3. **Inline confirmation on the row** — chosen. Clicking Delete opens a
   confirm strip under the row: "Permanently delete <title>? Unsaved
   changes are lost." with `Confirm delete <title>` and
   `Cancel delete <title>` buttons. Escape cancels (the strip handles
   `Escape` while focus is inside it). Focus moves deliberately to the
   confirm control on open; on settle `useCommandFocusRestoration`
   returns focus to the confirm button (failure, strip retained for
   retry) or to a surviving neighbor row button (success, row gone).

The busy group is the Navigator's existing `documentMutationBusy` family:
while any document mutation (create/move/delete/place) is in flight,
every other row command renders disabled, and the initiator alone carries
`aria-busy` with "Deleting <title>" naming — the same conflict-group
discipline the Add and Move commands already follow.

## Draft, active selection, and fallback

The Draft is component-local and discarded on any document switch by
contract. Deleting the active document is an explicit switch: the
confirmation names the loss, and on success the shell row removal plus
`setActiveId(null)` let `useActiveDocument` derive the route-compatible
fallback (first remaining document, first of the section kind, or the
no-document state). No Draft is smuggled anywhere. A delete racing an
in-flight autosave resolves by SQLite authority: the save either commits
before the delete or 404s after it.

## Placement control and causal application

The placement control is a native `<select>` on chapter rows, offered only
when the project has more than one volume. Its value is a permanent
neutral placeholder ("Move to volume…"); the chapter's current volume is
never listed as a target — the server would otherwise accept it as a
hidden move-to-tail reorder, which is the Move command's job (#480), not
placement's. Choosing another volume fires the command once; the select
returns to the placeholder whether the command succeeds or fails.

Options considered for the control: a menu button with a popover (extra
open/close focus machinery) and a select-plus-Go pair (two controls for
one decision). The native select is the smallest keyboard-operable
surface; its immediate-change execution is acceptable because placement
is reversible and not destructive, unlike deletion.

The response applies under the #469 narrow-command discipline, modeled on
the Lore-status/beat intent epoch (`useNarrowSummaryField`'s semantics,
written for this command's shape because its response value differs from
its request value):

- each command captures project, document, and the summary's current
  revision, plus a per-document intent epoch;
- on success it patches **only** `volume_id`, `position`, and
  `updated_at` on that summary row — never title, word count, or revision
  identity — and only while the captured revision still owns the row and
  the intent is still latest;
- a late response that a newer save or a newer placement intent has
  outrun is ignored; the next shell read converges from SQLite authority.

The active accepted body is not rewritten: placement does not change the
revision the body is keyed to, and no editor surface renders
`volume_id`/`position` from the body. Sibling positions in the source
volume keep their stored values (the server leaves a gap); the shell
renders persisted positions, exactly as it already does after an
API-level placement and reload.

Deletion applies the same owner checks with idempotent row removal; a
late delete response for an already-removed row is a no-op filter.

## Error surface

Both commands report failures through per-document lifecycle state
rendered inline on the initiating row (`role="alert"`, aria-live), using
`toErrorMessage` so the 422 capacity envelope keeps its resource/limit
suffix and network failures keep their envelope message. This follows the
narrow-command precedent (#444/#466 — errors render next to the control
that caused them) rather than the shared project error channel used by
create/move, because the initiating control is a specific row; a far
panel alert would detach the failure from the row the author just acted
on. Re-invoking the command is the retry.

## Component and hook boundaries

- `useStudioChapterPlacement` — placement command hook: per-document
  intent epoch, revision capture, owned-field shell merge, per-document
  lifecycle (`isPlacing`, `attemptedVolumeId`, `error`).
- `useStudioDocumentDeletion` — deletion command hook: single-flight
  pending key, scoped `deletingDocument` identity, idempotent row
  removal, active-id clearing, per-document lifecycle (`isDeleting`,
  `error`).
- `StudioNavigatorRowActions` — one row's actions: the existing Move
  up/down buttons, the placement select, the delete trigger, and the
  inline confirmation strip. `StudioNavigatorDocumentRows` keeps row
  composition and the shared focus-restoration runner; both stay under
  the 200-line component discipline.
- `useCommandFocusRestoration` widens its trigger type from
  `HTMLButtonElement` to also accept `HTMLSelectElement`; its
  `canReceiveFocus` already handles selects, so no behavior changes for
  existing button callers.
- The Navigator receives the new commands as one optional `rowCommands`
  model prop, so existing consumers and tests compile unchanged; the
  page model passes it from `useStudioActions`, which composes the two
  hooks beside `useStudioDocumentActions`.

## Options rejected

- Adding a client-side running-job or proposal-audit gate before delete:
  the server contract has no such gate, and duplicating policy in the UI
  invents a rule the server does not enforce.
- A delete confirmation via `window.confirm`: breaks deliberate focus
  movement and busy naming, both required by the Navigator command
  discipline.
- Applying the placement response with the whole-summary
  `mergeProjectDocument`: a late response would overwrite title, word
  count, or revision identity a newer save had already advanced.
- Refreshing the whole shell after either command: the #469 contract
  applies mutation responses causally without a follow-up read.
- Offering the current volume as a placement target: turns a structural
  command into a hidden reorder and invites accidental move-to-tail.
