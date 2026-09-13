# Refactor Handoff — 2026-09-05

## Candidate

- Branch: `codex/project-design-refactor`
- Comparison baseline: `2a1d959fc0afb644de0bfbde9f6fa840ace58da4`
- Code candidate: `67c339929a224d4ac21a253b6e26dff3118bfa19`
- Scope: the current 160-commit engineering and AI-coding-practice refactor series,
  including lifecycle/capacity hardening, project-shell/current-document separation,
  revision pagination, settings update, and lazy Inspector histories.
- Worktree at final review: clean.

This is a review candidate, not a release. Required CI and human acceptance have
not been recorded on the candidate SHA.

## Final local evidence

All results below were collected read-only on the exact code candidate unless a
different SHA is named.

| Level | Surface | Result |
|---|---|---|
| Targeted | Cross-resource shell publication regression | 18/18 tests passed; failed or cancelled Inspector rechecks cannot invalidate Document convergence |
| Targeted | Settings, current-document, pagination, and lazy Inspector suites | Passed during their owning changes; final frontend full suite includes them |
| Local full | `pnpm --dir server gates` | Passed: SSOT, hygiene, size (619 files), migration channel, llms-txt, and OpenAPI snapshot |
| Local full | Frontend lint / format / type check | Passed: lint 213 files, format 212 files, type check clean |
| Local full | `pnpm --dir frontend test:unit` | Passed: 82 files, 456 tests |
| Local full | Frontend build and identity check | Passed: 1,929 modules; Novel Engine 0.6.0 verified in HTML and seven JS bundles |
| Local full | Generated API type drift | Passed |
| Local full | React Doctor | 100/100, 200 files, zero issues |
| Local full | `pnpm --dir frontend test:e2e:ts` | Passed: 9/9 workflows |
| Local full | `pnpm spec:validate` | Passed: 19/19 strict changes |
| Historical supporting evidence | Full server test suite at `cbe69543` | Passed: 202 files, 1,269 tests; server product code did not change after this SHA |
| Independent agent review | Standards/spec/concurrency review of `2a1d959f..67c33992` | No P0, P1, or P2 finding |

The earlier isolated E2E invocation timeout is not a product failure: that suite
depends on the sibling owner setup and does not support selection in isolation.
The complete TS E2E suite subsequently passed on the candidate SHA.

## Evidence not closed

| Level | State | Owner / closure condition |
|---|---|---|
| CI required | Not run | Push the exact candidate (or its review-only successor) and require every live branch-protection context to pass on that SHA |
| Human acceptance | Not run | Product owner exercises project open, editing/autosave, History restore, Review/Export lazy loading, settings save, keyboard focus, and error/retry flows |
| Release authorization | Not granted | Owner explicitly approves integration/release after CI and human acceptance |

Local green checks do not substitute for these gates.

## Active OpenSpec state

Keep all active changes under `openspec/changes/` unarchived until required CI is
green. In particular:

- `2026-09-03-paginate-revision-history`: validation/CI/archive tasks remain open.
- `2026-09-03-restore-project-settings-update`: integrated validation and
  CI/archive tasks remain open.
- `2026-09-03-split-project-shell-document-body`: several implementation and
  validation boxes remain conservatively unchecked even though the candidate now
  contains shell-first bootstrap, bounded Document convergence, lazy Review/Export
  histories, and regression coverage. Reconcile each box against the exact
  implementation and evidence before checking it; do not bulk-close by inference.

## Next owner sequence

1. Re-read live branch-protection requirements and open a review from
   `codex/project-design-refactor` without rewriting the candidate history.
2. Run required CI on the exact review SHA. Treat any follow-up commit as a new
   candidate and rerun affected evidence.
3. Perform the human workflows listed above, recording owner, date, surface, and
   result according to `docs/agents/change-evidence.md`.
4. Reconcile the remaining OpenSpec checkboxes, then archive only the changes whose
   CI and human gates are actually closed.
5. Address later audit frontiers as separate small changes: project catalog
   pagination, review-history pagination/N+1 removal, export catalog
   pagination/quadratic work removal, and authoring-structure capacity. They were
   identified but intentionally not added to this accelerated closeout.

## Recent closeout commits

- `94722e42` — isolate successful shell publication from failed/cancelled reads.
- `b240bbac` — split oversized modules and remove render-time ref writes.
- `67c33992` — select a genuinely stale revision in the conflict E2E fixture.

The requested Matt orchestration skills were not available in this checkout's
installed skill set. The work used the repository's OpenSpec, domain-design,
specialist implementation, independent review, and evidence contracts instead;
no Matt skill files were changed.
