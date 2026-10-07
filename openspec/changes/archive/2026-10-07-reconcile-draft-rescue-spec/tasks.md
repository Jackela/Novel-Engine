# Tasks

## T1: Draft the reconciliation deltas

- [x] T1.1 Modify `In-memory document drafts`: a departure hands the
      departing Document's newest content and title to one rescue write before
      the local Draft is discarded, the rescue is read back only as an accepted
      revision, a failed/conflicting/lost rescue stays silent, and an
      unresolved conflict Draft never enters the rescue path; add departure,
      read-back, conflict-exception, and silent-failure scenarios. Acceptance:
      delta steps match `useDocumentDraftRescue.ts` (rescue on owner change and
      unmount, conflict gate, identical in-flight skip, silent catch) and the
      unit cases in `useDocumentDraft.selection` (`:84`, `:129`, `:204`),
      `.lifecycle` (`:93`), `.reconciliation` (`:101`), `.external` (`:167`),
      `.autosave-recovery` (`:235`).
- [x] T1.2 Modify `Project-scoped Studio resource lifecycle`: the switch
      paragraph hands a non-conflicted Draft to its one rescue write before
      discarding (conflict Draft stays out), and the `An unpersisted draft does
      not survive document navigation` and late-completion scenarios state the
      rescued-revision carve-out and the originating-identity binding.
      Acceptance: delta text matches `studio_switch.spec.ts:44-106` — one PUT to
      A, zero to B, no late duplicate past the debounce, rescued text on reopen
      with no further save, B's body untouched.
- [x] T1.3 Cross-check every reconciled step against the browser workflow
      assertions above and against `documentDraftPersistence.ts`
      (`autosave: true`, base revision) so no step describes a behavior the
      pins do not have.

## T2: Validate

- [x] T2.1 `pnpm spec:validate` passes with the change present.

## T3: Archive

- [x] T3.1 Archive the change; deltas merge into
      `openspec/specs/novel-engine/spec.md` and the change folder moves to
      `openspec/changes/archive/`; `pnpm spec:validate` passes again and the
      spec diff is limited to the two reconciled requirements.
