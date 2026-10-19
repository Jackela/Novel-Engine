# CI Gates — Inventory and Failure Runbooks

Reference for what each CI gate enforces and what to do when it goes red.
The authoritative definition of every gate is the workflow files under
`.github/workflows/`; this document explains behavior and response playbooks.
Record validation status using [Change Evidence](change-evidence.md).

Since the #277 cutover the tree is TypeScript-only. The Python tree at tag
`python-final` is history, not a current validation twin or fallback. Resolve
current commands from the pnpm package scripts and live workflows.

## Gate inventory

| Gate (workflow / step) | Enforces | Red means |
| --- | --- | --- |
| `CI` / Validate dependency security | `pnpm audit --audit-level high --prod` (production deps only) | The PR introduces or keeps a *production* dependency with a known high advisory |
| `Dependency Audit` (scheduled, daily 03:17 UTC + manual dispatch) | Full audit including dev tooling; tracks failures in one reusable issue until green | A new upstream advisory affects any locked dependency, including dev-only paths |
| `CI` / `validate` job | Dependency security; server SSOT, hygiene, size, migration, llms-txt, error-codes, and OpenAPI gates, architecture, TypeScript, Biome, type-aware lint, and full tests; strict OpenSpec; frontend Biome, TypeScript, type-aware lint, unit tests, build, generated API-type drift, React diagnostics, and the browser workflow | One or more validation surfaces failed; inspect the failing step on that exact SHA |
| `CI` / Validate React static diagnostics | `react-doctor` with **zero tolerance: warnings fail too**, not just errors | Any diagnostic, including `warning` severity (`unused-export`, `async-defer-await`, …) |
| `CI` / Validate frontend | Biome check and format, TypeScript, Vitest, and Vite build | Conventional lint, format, type, test, or build failure |
| `CI` / Validate server + frontend types and lint (`pnpm lint:types`) | The oxlint type-aware pass (tsgolint on `typescript-go`) over the rules Biome cannot express — see the scope policy below | A type-aware finding: an unhandled promise, a promise in a `void` slot, or a dropped `cause` |
| `CI` / Check generated API types drift | regenerates `frontend/generated/api-types.ts` from `server/qa-baselines/openapi.current.json` and compares byte-identical | The committed generated types are stale — run `pnpm --dir frontend gen:api-types` |
| `CI` / Validate Studio workflow against the TS backend | Playwright (`playwright.ts.config.ts`) against the emitted CLI serving `frontend/dist` | A browser-level Studio workflow or content-acceptance assertion broke |
| `CI` / `server` job | Duplicate server gates, dependency-cruiser, TypeScript, Biome, and Vitest validation retained as defense in depth | A server contract or conventional check failed independently of the `validate` job |
| `gate:error-codes` (server package script, part of `pnpm --dir server gates`) | `docs/agents/error-codes.md` catalog rows stay in lockstep with `ERROR_CODES` and `ERROR_HTTP_STATUS`: the code set and every HTTP status must match exactly in both directions | The error-code catalog drifted from the TS sources; align the docs table or the TS declarations (the diff message names the offending code) |
| `CI` / container | `docker build` + fresh install, persistence across restart, deep link, drizzle-migration table check | The production image fails to boot, persist, or serve the SPA |
| `CodeQL` | javascript-typescript analysis over `server/` + `frontend/` | A CodeQL alert on the TS workspace |

## Runbook: a neutral CodeQL configuration comparison

The `github-advanced-security` app can add a `CodeQL` check alongside the
`Analyze (javascript-typescript)` workflow job. Read its summary on the exact
PR commit: a neutral result is not evidence that the workflow failed, nor that
all expected configurations reported results.

On 2026-10-19, the [app check on PR #687](https://github.com/Jackela/Novel-Engine/runs/117882723883)
(candidate `c9632724c6ce8d58435beb45c826f6baf7e0f7c8`) named
`.github/workflows/codeql.yml:analyze/language:python` as present on `main` but
missing from the PR. Python was retired in the accepted
[TypeScript cutover](../adr/0003-cutover-execution.md); the workflow already
scans only `javascript-typescript`. The live default-setup API returned
`state: not-configured`, so disabling default setup would not resolve this
historical configuration comparison. This setting was checked with
`gh api repos/Jackela/Novel-Engine/code-scanning/default-setup` against the
repository at `b3ad2b91a2778a27168f4149ec4e73332233cd6d`. Settings are mutable;
this dated observation is not a substitute for reading their current value.
Earlier explanations attributing this
warning to two active setups must not substitute for a fresh diagnosis.

When this warning appears:

1. Read the app check summary and compare the named configuration with the
   current workflow, default-setup settings, and analyses for the base branch.
   Identify the exact ref, tool, and category; a language name alone is not
   a safe cleanup selector.
2. If the configuration is retired, preserve available analysis metadata,
   SARIF, and alert history before an authorized retirement. Record export
   failures and the effect on GitHub history; a local archive does not promise
   restoration of the original analysis IDs or alert timeline. Use GitHub's
   [configuration management](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/use-the-tools-status-page-for-code-scanning)
   or [analysis API](https://docs.github.com/en/rest/code-scanning/code-scanning),
   confined to the confirmed obsolete configuration.
3. Keep the current TypeScript workflow, scan paths, permissions, and required
   checks intact. Do not reintroduce retired source files or suppress scanning
   to make the comparison green.
4. Verify a new PR's app check and TypeScript analysis on its exact candidate
   SHA, then verify the merged `main` scan. Historical PR conclusions are
   historical evidence and need not be rewritten by a later configuration
   retirement.

## Runbook: dependency advisory flaps

PR CI audits **production dependencies only**, so a newly published advisory on
dev tooling (vite plugins, test runners, linters) cannot turn open PRs red.
Full-coverage auditing moved to the scheduled `Dependency Audit` workflow:

1. When the full audit fails, it creates or comments on a single tracking
   issue ("dependency audit: known advisories need attention"). Do not open
   separate issues.
2. Fix by adding or tightening an `overrides` entry in `pnpm-workspace.yaml`
   (see the precedent from #235: `undici`, `fast-uri`, `brace-expansion`,
   `postcss`, `nanoid`) and regenerating the lockfile
   (`pnpm install` at the repo root). The current `undici <8` override is a
   workspace compatibility constraint; verify the current lockfile and
   frontend package before changing it.
3. Merge; the next scheduled run closes the tracking issue automatically once
   the audit is green.

If a *production* dependency advisory lands, PRs may legitimately fail the
`--prod` audit — that is the gate working as intended; fix via overrides the
same way.

## Runbook: React Doctor zero tolerance

`Validate React static diagnostics` fails on any diagnostic count > 0,
**including `warning` severity**. This is deliberate (both blocked PRs in
2026-07 were warning-level: `unused-export`, `async-defer-await`). Fix the
diagnostic in the code. If a narrowly scoped `react-doctor-disable-next-line`
directive is necessary for an intentional pattern, keep it beside the code
and document the reason; the workflow checks the reported diagnostic count and
does not claim a blanket suppression ban.

## Runbook: OpenAPI baseline changes

Any route-affecting server change must regenerate the frozen baseline with
`pnpm --dir server openapi:snapshot` in the same PR; the drift gate and the
frontend api-types drift gate both fail otherwise. Regeneration is
deliberate — never hand-edit `server/qa-baselines/openapi.current.json` or
`frontend/generated/api-types.ts`.

## Policy: type-aware lint (oxlint) scope

Biome has no type-aware linter, so `lint:types` runs a second, deliberately narrow
pass: `oxlint --type-aware`, configured per package in `server/.oxlintrc.json` and
`frontend/.oxlintrc.json`. It is powered by tsgolint on `typescript-go`, which is
the only reason it can run here at all — the workspace pins TypeScript 7.0.x, which
ships no JS compiler API (`require("typescript")` exposes only `version` and
`versionMajorMinor`), so typescript-eslint cannot load. `server/.dependency-cruiser.cjs`
records the same TypeScript 7 constraint for its parser.

Every oxlint default category is off, so the pass reports nothing Biome already
reports; it exists only for rules Biome structurally cannot express. Enabled today:
`typescript/no-floating-promises`, `typescript/await-thenable`,
`typescript/no-misused-promises`, and `preserve-caught-error` (both packages).

Fix direction when it goes red: reach for the `void` operator to mark a deliberate
discard — that is the rule's own documented escape hatch — rather than loosening
the config.

Two scope decisions are recorded here with measured reasons rather than silence:

- **`require-await` (both packages, disabled)** — 265 findings, of which 195 are test
  doubles and the rest Fastify/React handlers declared `async` to satisfy an async
  contract without awaiting anything (for example `async () => ({ status: "alive" })`).
  Enabling it would push authors toward `Promise.resolve(...)` wrappers, which are
  strictly worse than an `async` function that fulfils an async contract.
- **`typescript/no-misused-promises` (frontend, narrowed)** — the full rule produced
  22 findings, none of them a defect: they all describe a promise-returning function
  placed in a `void` slot, which is the dominant React idiom and which this codebase
  already accepts as a convention (`StudioNavigator.tsx` types such callbacks
  `() => void | Promise<void>`). The four `checksVoidReturn` sub-checks that encode
  exactly that shape (`arguments`, `attributes`, `properties`, `variables`) are
  therefore off, while the `returns` sub-check stays **on** — it asks a different
  question (a promise returned where a synchronous value is expected) and is clean.
  The server runs the rule at full strength, where it caught a genuine contract
  mismatch (`reply.hijack()` returns the reply, not `void`).

Real floating rejections remain enforced in both packages by
`typescript/no-floating-promises`, so narrowing the frontend rule does not open that
gap.

## Policy: file-size gate — split at the limit

The file-size gate (`server/scripts/qa/check_file_sizes.mjs`, run as part of
`pnpm --dir server gates`) enforces a **300 code-line budget** per file
(non-empty, non-`//`-comment lines) across the TS workspace scan roots:
`server/src/`, `server/tests/`, `server/scripts/`, `frontend/src/`,
`frontend/tests/`, `frontend/scripts/`. The budget exists to keep modules
small and orchestration split out; the file-size gate in CI red means the
tree breached it.

Product components (`frontend/src/**/*.tsx`, excluding `.test.tsx`) have
the tighter **200 code-line budget**. Test files retain the default 300-line
limit. Both budgets accept a file exactly at the limit and reject the next
code line. When a file reaches its limit, split it; there are no per-file
exceptions.

### Current size evidence

Do not maintain an at-limit file list in documentation: it is an instantaneous
cache of repository state. Read the current checker output and inspect the
candidate file before editing. A clean historical run does not prove that a
later candidate remains within budget.

## Dependabot status

Dependabot version updates are **disabled** (#238): it updated
`frontend/package.json` without regenerating the root `pnpm-lock.yaml`,
so every run died at `pnpm install --frozen-lockfile`
(`ERR_PNPM_OUTDATED_LOCKFILE`) and cascaded into CodeQL failures. If it is
ever re-enabled, restrict it to the `github-actions` ecosystem, or use a
bot that regenerates pnpm workspace lockfiles (Renovate).
