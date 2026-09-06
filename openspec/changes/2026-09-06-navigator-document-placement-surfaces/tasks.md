# Tasks

## 1. Command hooks and shell merges

- [x] 1.1 Add failing hook tests for deletion: confirmation-independent
      command succeeds and removes only its document row, clears the
      active id when it pointed at the deleted document, keeps the row
      when the server refuses (snapshot conflict) with a readable inline
      error, ignores responses after the project owner changed, and
      exposes single-flight busy identity (`Deleting <title>` naming).
- [x] 1.2 Add failing hook tests for placement: success patches only
      `volume_id`, `position`, and `updated_at` on the captured
      document's summary row; a newer revision on the shell row rejects
      the late response; a newer placement intent supersedes an older
      in-flight one; failures (422 capacity envelope, network) surface a
      per-document inline error with capacity details; duplicate intent
      coalesces.
- [x] 1.3 Implement `useStudioDocumentDeletion` and
      `useStudioChapterPlacement` plus their `projectState` merge
      helpers (`removeProjectDocument`,
      `mergeProjectDocumentPlacement`) against those tests.

## 2. Navigator surfaces

- [x] 2.1 Add failing component tests for the delete surface: trigger
      opens the inline confirmation naming the document and the Draft
      loss; confirm and cancel behave oppositely; Escape cancels; busy
      naming disables the mutation conflict group; focus moves to the
      confirm control, restores to it on failure, and falls back to a
      surviving neighbor row on success.
- [x] 2.2 Add failing component tests for the placement surface: the
      select lists only other volumes, never the chapter's current one;
      choosing a volume issues the command once and returns to the
      neutral placeholder; busy and error naming follow the row command
      discipline.
- [x] 2.3 Implement `StudioNavigatorRowActions` and rewire
      `StudioNavigatorDocumentRows`/`StudioNavigator` (one optional
      `rowCommands` prop) with BEM styles; widen
      `useCommandFocusRestoration`'s trigger type to include selects.
- [x] 2.4 Add failing page-model wiring tests proving both commands and
      their lifecycle state reach the Navigator model from
      `useStudioActions`, then wire them.

## 3. Browser workflows

- [x] 3.1 Add a TypeScript-backend Playwright workflow for deletion:
      confirm removes the row and selection falls back; cancel leaves the
      row; a routed 409 snapshot-conflict refusal surfaces inline and
      recovers; focus lands on a surviving row after success.
- [x] 3.2 Add a TypeScript-backend Playwright workflow for placement:
      the chapter moves into the other volume's group in the Navigator,
      survives reload, busy naming appears during the request, and a
      routed 422 capacity refusal surfaces inline with retry.

## 4. Evidence and release boundary

- [x] 4.1 Run targeted hook/component/page-model tests, then frontend
      lint, format:check, type-check, full unit suite, build, and React
      static diagnostics (zero); run the smoke workflow, the new
      workflows, and the full shared-init TypeScript-backend e2e suite;
      run strict OpenSpec validation. Record exact results and every
      skip.
- [ ] 4.2 Keep the change active until required CI is green, then merge
      it into the canonical specification and archive it.
