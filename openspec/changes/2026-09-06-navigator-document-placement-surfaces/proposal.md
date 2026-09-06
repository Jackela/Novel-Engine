# Navigator document deletion and chapter volume placement

## Why

The #467 browser-workflow reconciliation (PR #476) triaged two frontend API
client methods with zero Studio UI callers as missing product UI, not dead
code: `api.deleteDocument` wraps a real, server-covered route, and
`api.moveChapterToVolume` wraps the chapter-placement route of the fixed
two-level hierarchy (ADR-0005). Today the author cannot remove a document
from the Studio without an API client, and moving a chapter into another
volume — the one structural move the hierarchy exists for — is reachable
only at the API level. The Navigator renders both structures read-only
beyond same-group reorder.

## What Changes

- Navigator document rows gain a per-row delete command. Because deletion
  is irreversible, the command runs an explicit inline confirmation step
  that names the document and warns that its unsaved Draft changes are
  lost; cancelling the confirmation (or pressing Escape) leaves the
  document untouched. The confirmation is keyboard operable, moves focus
  deliberately to its confirm control, reports busy as "Deleting
  <title>", and on settle returns focus to the trigger or, when the row
  disappeared, to a surviving neighbor row in the same reading group.
- Deletion stays document-level and server-authoritative. Immutable
  Revision and Snapshot semantics are unchanged: a document referenced by
  any snapshot refuses deletion with the server's snapshot-conflict
  envelope, surfaced inline on the initiating row where the author can
  retry or cancel; the server contract imposes no running-job gate, and
  the UI adds none.
- On success the deleted document disappears from the project shell
  without a full shell reload: only its row is removed. If it was the
  active document, selection falls back to the existing route-compatible
  document (or the documented no-document state) and its local Draft is
  discarded explicitly, matching the existing switch-document discard
  contract.
- Navigator chapter rows in projects with more than one volume gain a
  volume placement control listing the project's other volumes. Choosing
  a volume issues the existing placement command; the chapter lands at
  the target volume's tail per the existing route contract, and the
  shell updates causally from the response.
- Both commands apply to the shell under the #469 mutation contract:
  placement patches only the summary fields the command owns
  (`volume_id`, `position`, `updated_at`) and only while its captured
  revision still owns the shell row and its per-document intent is still
  the latest; a late or superseded response is ignored rather than
  rolling back newer authority. The control's current volume is never
  offered as a target, so the command cannot degrade into a hidden
  move-to-tail reorder.
- Transport, capacity, and refusal failures — including the permanent
  full-volume 422 capacity envelope (#461) and network errors — render
  inline on the initiating row with the error envelope's message and
  capacity details; re-invoking the command is the retry.

## Impact

- Frontend only: Navigator row actions, two command hooks, page-model
  wiring, styles, unit tests, and TypeScript-backend Playwright
  workflows. Zero server changes — both routes already exist with
  server-level coverage, and the OpenAPI baseline does not regenerate.
- No database migration, new dependency, environment variable, or change
  to save/restore/proposal response bodies, conflict resolution,
  immutable revisions, snapshot authority, volume CRUD semantics, or
  full-text search.
- Existing Navigator consumers keep compiling: the new commands arrive as
  one optional model prop; row rendering without it is unchanged apart
  from the added controls.

## Non-goals

- No volume create/rename/reorder/delete UI; those remain the separately
  triaged surface from #467.
- No bulk deletion, no undo or trash state, and no deletion of volumes or
  projects from the Navigator.
- No change to which documents the server allows to delete (snapshot
  references keep refusing) and no new client-side gating beyond the
  confirmation step.
- No placement targets beyond other existing volumes (no new-volume
  affordance inside the placement control).
