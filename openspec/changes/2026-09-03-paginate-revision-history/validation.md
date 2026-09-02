# Validation evidence

## Fixed points

- Comparison SHA: `c474c6e3039590067795d4980300a640b873d905`
- Persisted-count implementation SHA: `ea5fb6810eae32da30c24e538bda8c9fb5ab10ac`
- Final local candidate SHA: pending completion of the bounded API and frontend.
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Persisted revision word-count evidence

The migration was generated with
`pnpm --dir server db:generate --name persist-revision-word-count`. Its SQL adds
only the nullable upgrade-sentinel column; the generated snapshot and journal
were reviewed without manual edits. The migration-channel gate passed.

The exact prior Unicode counter now has one domain implementation. Focused
coverage pins ASCII, Chinese, punctuation, apostrophe, hyphen, numeric, empty,
and unpaired-surrogate behavior. Full Document and Revision projections consume
the stored value and reject null, negative, fractional, `NaN`, and unsafe
integers with the internal `RevisionWordCountInvariantError`.

The sole product revision insertion helper writes the count in the same
transaction for seeds, imports, saves, proposal acceptance, and restores. The
upgrade reconciler reads only `id` and body in stable batches of at most 256,
commits each batch atomically, resumes null rows after interruption, and runs
before export reconciliation and running-job recovery. Tests prove a 257-row
partial resume, 513-row checkpoints `[256, 512, 513]`, preservation of historic
revision fields, and fail-fast startup ordering.

| Validation surface | Result |
|---|---|
| Word-count and reconciliation tests | Passed: 2 files and 16 tests. |
| Seed/import/save/proposal/restore regressions | Passed: 7 files and 41 tests during implementation; independent review reran 29 API-path tests. |
| Server type-check, lint, architecture, size, gates, and build | Passed; architecture checked 216 modules / 895 dependencies and size checked 564 files. |
| Strict OpenSpec | Passed: 17 of 17 items before this evidence update. |
| Full server suite | One implementation-time run was intentionally interrupted after about two minutes with no observed failure; it is not recorded as a pass and remains due on the final fixed SHA. |

Two independent fixed-SHA reviews found no P0-P2 issue. The Standards review's
only P3 was a stale startup-order comment; the follow-up commit corrected it.
The specification review found tasks 2.1 through 2.4 complete. Agent review is
supporting evidence, not CI or release approval.

## Current release boundary

Tasks 1, 3, 4, and 5 remain open. Required GitHub checks were not run because
this task did not push or open a pull request. The change remains active and
unarchived until the bounded API/frontend implementation and final validation
are complete and required CI is green on the integration SHA.
