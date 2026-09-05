# Draft selection closeout — 2026-09-05

## Fixed candidate and scope

- Refactor baseline: `2a1d959fc0afb644de0bfbde9f6fa840ace58da4`.
- Finding baseline: `52741fbf1872a80e398639cba68c05bbab6eaeb7`.
- First repair: `d60f558c472dacbb22f4b9dc4ff3498a559a832f`.
- Reviewed code candidate: `b2019baec05485c9ae4aa930cdeb6e8dccba48ee`.
- Branch: `codex/project-design-refactor`.
- Owner: shell change task 3.5 and ADR-0008's component-local Draft contract.

The fix discards unsaved body/title/conflict state on deliberate Document
selection changes. Selection identity comes from the shell summary, so a body
loading/retry gap for the same Document does not discard its Draft. Late
successful mutations still update their original Document's accepted revision;
inactive bodies and Drafts are not cached. An old lifecycle's error cannot
publish into a new lifecycle, including A → B → A.

Independent review of the first repair found a blocked-autosave edge: a new A
Draft could exhaust its debounce while the old A request held the save lock.
The second repair makes request completion wake the current Document's save
check without exposing the obsolete failure. Other Documents' completions do
not restart its debounce. Ordinary autosave retains its 1.5-second delay.

No public HTTP schema, generated API type, migration, dependency, root package,
lockfile, README, container configuration, or protected source was changed by
this two-commit finding repair.

## Replayable evidence

Environment: macOS arm64, Node.js 24.19.0, pnpm 11.6.0. Results below name the
code candidate; a later documentation-only commit is a distinct review SHA.

| Level / candidate | Exact command or surface | Result |
| --- | --- | --- |
| Failing baseline `52741fbf` plus regression assertion only | `pnpm --dir frontend test:unit src/features/studio/hooks/useDocumentDraft.reconciliation.test.tsx -t 'pre-debounce draft'` | 1 failed, 7 skipped: expected accepted A, received discarded local A text |
| Review regression on `d60f558c` plus assertion extension only | `pnpm --dir frontend test:unit src/features/studio/hooks/useDocumentDraft.selection.test.tsx -t obsolete` | 409/500 cases failed: expected a second save carrying new A, observed only the original save |
| Targeted `b2019bae` | `pnpm --dir frontend test:unit src/features/studio/hooks/useDocumentDraft` | 6 files, 35 tests passed |
| Local full `b2019bae` | `pnpm --dir frontend lint`; `pnpm --dir frontend format:check`; `pnpm --dir frontend type-check` | Passed |
| Local full `b2019bae` | `pnpm --dir frontend test:unit` | 83 files, 463 tests passed |
| Local full `b2019bae` | `pnpm --dir frontend build`; `pnpm --dir frontend check:api-types` | Build/identity passed; no API type drift |
| Local full `b2019bae` | `pnpm --dir frontend exec react-doctor --json` | Score 100; zero diagnostics; 201 files |
| Local full `b2019bae` | `pnpm --dir server gates`; `pnpm spec:validate`; `pnpm --dir server build` | Passed; 620 size-gated files; 19 strict OpenSpec items |
| Browser `b2019bae` | `pnpm --dir frontend test:e2e:ts` | Complete suite: 9 passed, 18.3 seconds |
| Independent Standards `52741fbf...b2019bae` | Static standards/concurrency review of the finding's changed paths | Earlier P2 closed; no remaining actionable finding in this scope |
| Independent Spec `52741fbf...b2019bae` | Static task 3.5 / Draft lifecycle review | Earlier P2 closed; no remaining confirmed defect in this scope |

Local logs are in `/tmp/novel-engine-draft-closeout-20260905/`:
`targeted-b2019bae.log`, `frontend-b2019bae.log`, `gates-b2019bae.log`, and
`e2e-b2019bae.log`. They are local supporting artifacts, not portable CI URLs.
The two reviewers did not independently rerun the suites. Their review does
not close unrelated shell task 3.4 or the full browser/UX matrix.

## Outstanding gates and exact-SHA accounting

- Server full/type/lint/architecture were not rerun locally for this
  frontend-only repair. The `cbe69543` server full run remains historical
  supporting evidence; the PR's live CI will execute the current server jobs.
- At this document's creation, required CI is `not run; awaiting the final PR SHA`.
  The PR evidence table must record its exact head SHA, run URLs, and actual
  outcomes. Do not infer CI from the local results above.
- Live main protection was read on 2026-09-05: required contexts were
  `Analyze (javascript-typescript)`, `validate`, and `container`, with strict
  base synchronization. Resolve them again before integration.
- Human acceptance is **not run**. Use
  [the isolated acceptance packet](refactor-human-acceptance-2026-09-05.md).
- Integration/release authorization is not granted. No merge, release, or
  OpenSpec archive is performed by this closeout.

The original refactor handoff remains historical. The three active changes'
validation records now map their remaining tasks to implementation, evidence,
and explicit gaps; only task 3.5 is closed by this finding repair.
