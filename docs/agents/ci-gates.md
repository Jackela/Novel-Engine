# CI Gates — Inventory and Failure Runbooks

Reference for what each CI gate enforces and what to do when it goes red.
The authoritative definition of every gate is the workflow files under
`.github/workflows/`; this document explains behavior and response playbooks.

Since the #277 cutover the tree is TypeScript-only (pnpm workspace
`frontend/` + `server/`); the Python gates and the `python-freeze` guard
were retired with the Python tree (git tag `python-final`).

## Gate inventory

| Gate (workflow / step) | Enforces | Red means |
| --- | --- | --- |
| `CI` / Validate dependency security | `pnpm audit --audit-level high --prod` (production deps only) | The PR introduces or keeps a *production* dependency with a known high advisory |
| `Dependency Audit` (scheduled, daily 03:17 UTC + manual dispatch) | Full audit including dev tooling; tracks failures in one reusable issue until green | A new upstream advisory affects any locked dependency, including dev-only paths |
| `CI` / Validate SSOT, hygiene, and OpenSpec | `pnpm --dir server gates` + `pnpm spec:validate` | Version/identity drift (release version authority is `server/package.json`), forbidden residues, file-size budget breach, migration-channel violations, llms.txt link drift (a raw URL whose path is missing from git HEAD, or a link not matching the expected raw URL shape), OpenAPI snapshot drift, or invalid OpenSpec deltas |
| `CI` / Validate React static diagnostics | `react-doctor` with **zero tolerance: warnings fail too**, not just errors | Any diagnostic, including `warning` severity (`unused-export`, `async-defer-await`, …) |
| `CI` / Validate frontend | eslint `--max-warnings=0`, prettier, tsc, vitest, vite build | Conventional test/lint/type failures |
| `CI` / Check generated API types drift | regenerates `frontend/generated/api-types.ts` from `server/qa-baselines/openapi.current.json` and compares byte-identical | The committed generated types are stale — run `pnpm --dir frontend gen:api-types` |
| `CI` / Validate Studio workflow against the TS backend | Playwright (`playwright.ts.config.ts`) against the emitted CLI serving `frontend/dist` | A browser-level Studio workflow or content-acceptance assertion broke |
| `CI` (server job) / gates, architecture, types, tests | Node QA gates, dependency-cruiser, `tsc --strict`, Biome, vitest with Fastify `inject()` | A `server/` module breaks layering or a conventional test/lint/type failure |
| `CI` / container | `docker build` + fresh install, persistence across restart, deep link, drizzle-migration table check | The production image fails to boot, persist, or serve the SPA |
| `CodeQL` | javascript-typescript analysis over `server/` + `frontend/` | A CodeQL alert on the TS workspace |

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
   (`pnpm install` at the repo root). Note: `undici` must stay `<8` for
   jsdom 29 compatibility.
3. Merge; the next scheduled run closes the tracking issue automatically once
   the audit is green.

If a *production* dependency advisory lands, PRs may legitimately fail the
`--prod` audit — that is the gate working as intended; fix via overrides the
same way.

## Runbook: React Doctor zero tolerance

`Validate React static diagnostics` fails on any diagnostic count > 0,
**including `warning` severity**. This is deliberate (both blocked PRs in
2026-07 were warning-level: `unused-export`, `async-defer-await`). Fix the
diagnostic in the code; do not add suppressions (the diff check also rejects
`# type: ignore`-style suppressions).

## Runbook: OpenAPI baseline changes

Any route-affecting server change must regenerate the frozen baseline with
`pnpm --dir server openapi:snapshot` in the same PR; the drift gate and the
frontend api-types drift gate both fail otherwise. Regeneration is
deliberate — never hand-edit `server/qa-baselines/openapi.current.json` or
`frontend/generated/api-types.ts`.

## Policy: file-size gate — split first, baseline exceptional

The file-size gate (`server/scripts/qa/check_file_sizes.mjs`, run as part of
`pnpm --dir server gates`) enforces a **300 code-line budget** per file
(non-empty, non-`//`-comment lines) across the TS workspace scan roots:
`server/src/`, `server/tests/`, `server/scripts/`, `frontend/src/`,
`frontend/tests/`, `frontend/scripts/`. The budget exists to keep modules
small and orchestration split out; the file-size gate in CI red means the
tree breached it.

The policy is **split-first, baseline exceptional**: when a file reaches the
limit, split it. `LEGACY_LIMITS` in the checker (a relative-path → allowed
count map, currently empty) is the only exception channel, reserved for
intentional legacy files that genuinely cannot be split yet. It is never a
way to raise the default limit for new or conveniently-large code.

### Enabling a legacy baseline

Beware when first populating `LEGACY_LIMITS`: the checker performs a
two-way stale-baseline validation (`legacyLimitViolations`). A baseline
entry fails loudly — even with **zero** size violations elsewhere — if:

- the file has shrunk to at or below the default 300-line limit, or
- the file's current code-line count differs from the configured value.

So the first run with a new baseline entry that no longer matches reality
fails with `[file-size] invalid legacy baselines:` — this is expected
behavior, **not a gate malfunction**. Baselines must be regenerated
deliberately (with review evidence) whenever the file changes; see the
failure hint printed by the gate itself.

### At-limit watch list

These files sit exactly at the 300-line limit — any growth turns the gate
red, so prefer splitting them proactively:

- `server/tests/api/studio_proposals.test.ts`
- `server/src/contexts/studio/application/provider_scaffold.ts`
- `server/src/contexts/studio/application/ports/studio_store.ts`

## Dependabot status

Dependabot version updates are **disabled** (#238): it updated
`frontend/package.json` without regenerating the root `pnpm-lock.yaml`,
so every run died at `pnpm install --frozen-lockfile`
(`ERR_PNPM_OUTDATED_LOCKFILE`) and cascaded into CodeQL failures. If it is
ever re-enabled, restrict it to the `github-actions` ecosystem, or use a
bot that regenerates pnpm workspace lockfiles (Renovate).
