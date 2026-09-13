# Repository simplification evidence — 2026-09-08

## Candidate and scope

- Fixed baseline: `df44d957d4b244afdac3d060df293ff9828ca335`.
- Candidate: `ec6d21538d692afc4d80a463eca557e441f4935b`.
- Three commits: `93911e08` (dead beat helper and wiki reference),
  `12165677` (wiki reconciliation), `ec6d2153` (frontend scripts/config).
- Baseline-to-HEAD diff: 11 files, 18 insertions, 43 deletions.
- Existing product features are preserved. No dependency or lockfile changes.
- Product-removal candidates remain pending explicit selection. Generic wrappers
  and retry helpers were retained where simplification had weak net gain.
- Root `AGENTS.md` changes and `.zcode/` were pre-existing and excluded.

## Validation evidence

The source files were frozen before the candidate commits. Checks ran in the
shared working tree, not a clean isolated checkout of the candidate SHA;
therefore these are local working-tree results, not clean-SHA claims.

| Command | Result | Log |
| --- | --- | --- |
| `pnpm --dir server type-check` | pass | [`type-check`](/tmp/novel-engine-type-check-20260908.log) |
| `pnpm --dir server lint` | pass; one existing CookieJar warning at `server/tests/api/studio_structure_capacity_scalars.test.ts:14` | [`lint`](/tmp/novel-engine-lint-20260908.log) |
| `pnpm --dir server arch` | pass; 235 modules, 996 dependencies | [`arch`](/tmp/novel-engine-arch-20260908.log) |
| `pnpm --dir server gates` | pass | [`gates`](/tmp/novel-engine-gates-20260908.log) |
| `pnpm --dir server test` | pass; 212 files, 1324 tests | [`test`](/tmp/novel-engine-test-20260908.log) |
| `pnpm --dir frontend lint` | pass | [`frontend lint`](/tmp/ne-frontend-lint.out) |
| `pnpm --dir frontend format:check` | pass | [`frontend format`](/tmp/ne-frontend-format.out) |
| `pnpm --dir frontend type-check` | pass | [`frontend typecheck`](/tmp/ne-frontend-typecheck.out) |
| `pnpm --dir frontend test:unit` | pass; 103 files, 562 tests | [`frontend unit`](/tmp/ne-frontend-unit.out) |
| `pnpm --dir frontend build` | pass; build identity verified | [`frontend build`](/tmp/ne-frontend-build.out) |
| `pnpm --dir frontend test:e2e:smoke` | pass; 3 tests | [`e2e smoke`](/tmp/ne-frontend-e2e-smoke.out) |
| `pnpm spec:validate` | pass; 2/2 | recorded in task log |

Additional alias checks passed: `pnpm --dir frontend run test src/app/productBuildConfig.test.ts`
and `pnpm --dir frontend run test:unit src/app/productBuildConfig.test.ts` each ran 2/2 tests.
`pnpm --dir frontend run test:e2e --list` and
`pnpm --dir frontend run test:e2e:ts --list` each listed 23 tests in 8 files.
An accidental `-- --list` invocation ran the full E2E suite (23 pass) twice;
this was an invocation error, not intentional extra assurance.

## Review and residual gates

- Standards review of tools/backend diff: clean. Wiki changes were excluded
  from independent author review because the wiki author reviewed that scope.
- Independent Spec review found stale `tsconfig.node` and wiki references;
  both were fixed and the rereview passed.
- API-types drift, React Doctor, container persistence, hosted CI, push,
  human acceptance, and release authorization were not run. They remain open
  with the integrator/owner and must close on the final candidate before release.

This record is a documentation-only follow-up to the candidate above.

## Wave 2 evidence

- Fixed baseline: `1617eeec5856ebc067dbd18b9b325cf6dd648947`.
- Candidate: `c4c7b062b4b10b59b38fe887991e82981215afac`; commits `37313ea7`
  (remove two dead helpers, 38 lines) and `c4c7b062` (daily usage parser fix,
  17 production lines and 73 lines of regression tests).
- Scope was limited to the two proven dead backend helpers and the frontend
  usage contract boundary. No product-cut decisions or dependency changes.
- Working-tree validation was not clean-SHA validation; user `AGENTS.md` and
  `.zcode/` changes were excluded. No push or release action occurred.
- Server baseline/targeted three-file review, type-check, lint, arch, gates,
  and test evidence is recorded in `/tmp/wave2-server-*.log` (full run:
  212 files, 1324 tests); lint retained the existing CookieJar warning.
- Frontend evidence is in `/tmp/ne-usage-{unit,typecheck,build,api-types,server-sizes}.out`;
  full frontend tests passed 104 files / 567 tests; corrected targeted usage
  tests passed 5/5, with corrected lint/format logs.
  The full frontend suite was not repeated after the assertion-only change.
- The red run `/tmp/ne-usage-red.out` had three failures, including one
  over-strict legacy optional-key assertion. The fix preserves normal daily
  usage and rejects malformed responses. Stricter frontend safe-integer/date
  checks were reviewed and deferred because backend canonical validation and
  existing `numberField` semantics remain authoritative.
- Browser/CI/container/React Doctor checks were not rerun this wave. Final
  integration review and release authorization remain open.

## Wave 3 evidence

- Fixed baseline: `849fc0b3cb4a83bb28b9c26b66df90dc64761bc7`.
- Candidate: `9bdc27d94e715697748330ba25eb2571e71a0f38`; scope is the new
  `frontend/tests/e2e-ts/workflows/studio_usage.spec.ts` only. No product,
  schema, dependency, or lockfile changes.
- Frozen test file SHA-256:
  `934552e9391240ee20abe15d5ffcb1f0bf3eaa77cc4c906f1c28a5e557a8ce79`.
- The three planned browser scenarios are covered: initial zero usage then
  real generation and daily UI; one exact usage-route 503 with retained data,
  recovery, and focus; delayed real A response followed by stable zero-usage B
  before and after releasing A.
- Static checks passed: frontend lint, format, type-check, unit tests (104
  files / 567 tests), OpenSpec validation, server size gate, frontend build,
  and server build. Logs: `/tmp/ne-wave3-{lint,format-check,type-check,
  test-unit,spec-validate,server-gate-sizes,frontend-build,server-build}.out`.
- Targeted command with `LLM_PROVIDER=mock`, one worker, and Chromium passed
  6 tests: `/tmp/ne-wave3-targeted-final.out`.
- Historical proof was replayed against `37313ea7179d4d777bb1d378e78c18553bcd3d37`
  using the same test file and dependency links; it exited 1 as expected:
  1 pass / 1 fail because daily rows were expected at 30 but rendered 0.
  Details and the retained old trace path are recorded in
  `/tmp/ne-wave3-old-proof-verified.txt`; the old test file hash is identical.
- Full E2E with `LLM_PROVIDER=mock` and one worker had 21 pass, 1 fail, and
  4 not run due to existing owner-init ordering at `studio_content`; its trace
  was lost on rerun. The corrected default run passed 26 tests in 42.9s:
  `/tmp/ne-wave3-full-e2e-default.out`.
- Independent Standards and Spec review: zero findings. Validation used the
  shared working tree with user `AGENTS.md`/`.zcode/` excluded, not a clean
  isolated SHA. No CI, container, human acceptance, push, or release evidence.

Replay commands (repository root unless stated otherwise):

```bash
pnpm --dir frontend build
pnpm --dir server build
pnpm --dir frontend lint
pnpm --dir frontend format:check
pnpm --dir frontend type-check
pnpm --dir frontend test:unit
pnpm spec:validate
pnpm --dir server gate:sizes
LLM_PROVIDER=mock pnpm --dir frontend exec playwright test --config=playwright.ts.config.ts --workers=1 tests/e2e-ts/studio-ts.spec.ts tests/e2e-ts/workflows/studio_usage.spec.ts --project=chromium
LLM_PROVIDER=mock pnpm --dir frontend test:e2e:ts --workers=1
LLM_PROVIDER=mock pnpm --dir frontend test:e2e:ts
```

The penultimate command is the failed scheduling experiment, logged in
`/tmp/ne-wave3-full-e2e.out`; only the final default-concurrency run passed.
The historical checkout built its own frontend/server outputs with the same
build commands above. From `/tmp/ne-wave3-before-daily-37313ea7/frontend`,
the actual historical test command was:

```bash
LLM_PROVIDER=mock TS_E2E_DATA_DIR=/tmp/ne-wave3-old-data.gy4utn /tmp/ne-wave3-before-daily-37313ea7/frontend/node_modules/.bin/playwright test --config=playwright.ts.config.ts --workers=1 tests/e2e-ts/studio-ts.spec.ts tests/e2e-ts/workflows/studio_usage.spec.ts --project=chromium --grep 'owner setup, editing|renders empty usage'
```

Historical failure log: `/tmp/ne-wave3-old-red.out`. Retained trace:
`/tmp/ne-wave3-before-daily-37313ea7/frontend/test-results/workflows-studio_usage-stu-44dc1-erver-totals-and-daily-rows-chromium/trace.zip`.
These are local temporary artifacts, not committed release evidence.

## Wave 4 — Git tracking and documentation

- Baseline: `c0d814a1f7a42d784ae16227555f2e07f5cbc7eb`.
- Candidate: `978821fe9901a8ca75b9ddbc9017e501a71d91c7`, tree
  `0e4b840d4e39a5224c2687466ba406d310bb4ffa`.
- Scope: `.gitignore` and 12 documentation files. No application, API,
  database, dependency, workflow, or deployment behavior changed. Original
  `AGENTS.md` edits and `.zcode/` work were excluded from the commit.
- `.gitignore` decreased from 257 to 102 lines. Retired framework and one-off
  report patterns were removed; documents and JSONL fixtures remain visible.
  Environment secrets, application data, builds, dependencies, test outputs,
  and SQLite WAL/SHM files remain excluded.
- Added `docs/README.md` as the document index; expanded contribution guidance
  on focused commits, lockfiles, generated contracts, local exclusions, and
  evidence retention. Corrected setup/validation instructions, issue-template
  session labels, and CI runbooks against current scripts and workflows.
- Baseline inventory: 328 Markdown/text files, including 89 installed skill
  files and 192 OpenSpec files (187 archived, 4 active-change, 1 canonical
  specification). Installed skills and the forbidden historical audit were
  excluded from content scanning. Active first-party guides were checked
  against source; dated records retained their original meaning.
- Final link scan covered 239 first-party Markdown/text files and 110
  repository file/directory targets. It found and repaired 15 broken relative
  evidence links in three archived OpenSpec validation records. Final result:
  zero missing repository targets. Eleven existing absolute `/tmp` evidence
  links are local artifacts; heading anchors and external network availability
  were outside this scan.

Verification ran locally on the staged candidate tree above, with unrelated
user work still present; this is not clean isolated-checkout or hosted CI evidence.
Logs and temporary replay scripts are under `/tmp/ne-repo-hygiene-20260908/`:

| Executed command | Result | Evidence |
| --- | --- | --- |
| `python3 /tmp/ne-repo-hygiene-20260908/verify-ignore.py` | 45/45 cases: 25 ignored, 20 visible; 12 real old ignored paths still protected; zero tracked-but-ignored files | `ignore-verified.json` |
| `python3 /tmp/ne-repo-hygiene-20260908/check-doc-links.py` | 239 files, 110 repository targets, zero missing after repair | `doc-links.out`; failures retained in `doc-links-before-repair.out` |
| `pnpm --dir server gates` | All six gates passed; OpenAPI snapshot 1/1 | `server-gates.out` |
| `pnpm spec:validate` | 2/2 passed | `spec-validate.out` |
| `git diff --cached --check` | Passed before candidate commit | Local command result |

Evidence corrections: the first agent link scan missed the archived links.
The first ignore comparison copied the candidate into its supposed baseline
and did not fail on mismatches; `ignore-matrix.out` is invalid evidence. The
replacement verifier loads `.gitignore` from the fixed Git baseline and uses
assertions; only `ignore-verified.json` supports the counts above.

Luna performed implementation and separate Standards/Spec reviews; Astra
reviewed the combined diff and evidence. Review concerns about single-worker
ordering were resolved against the retained Wave 3 failure/default-pass logs:
the documented full-suite hazard is real. Generic extension-based secret-risk
claims had no repository evidence; JSONL visibility is intentional. Existing
`.zcode/plans/` remains user work, with its tracking policy unchanged. The
integrator found no remaining actionable defect in this documentation scope.

Full product/browser tests and container checks were not rerun: this change
affects documentation and ignore policy only. GitHub settings, push, merge,
hosted CI, human acceptance, and release were not performed. Local `/tmp`
artifacts have temporary retention and are not durable shared evidence.

Guidance consulted: [Git ignore semantics](https://git-scm.com/docs/gitignore),
[GitHub ignoring files](https://docs.github.com/en/get-started/git-basics/ignoring-files),
and [GitHub repository practices](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories).
