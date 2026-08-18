# CI Gates — Inventory and Failure Runbooks

Reference for what each CI gate enforces and what to do when it goes red.
The authoritative definition of every gate is the workflow files under
`.github/workflows/`; this document explains behavior and response playbooks.

## Gate inventory

| Gate (workflow / step) | Enforces | Red means |
| --- | --- | --- |
| `CI` / Validate dependency security | `pip-audit` (full Python env) + `pnpm audit --audit-level high --prod` (frontend production deps only) | The PR introduces or keeps a *production* dependency with a known high advisory |
| `Dependency Audit` (scheduled, daily 03:17 UTC + manual dispatch) | Full audit including dev tooling; tracks failures in one reusable issue until green | A new upstream advisory affects any locked dependency, including dev-only paths |
| `CI` / Check AI regression diff | `scripts/ai/regression_check.py` (main's copy) against the PR diff | The diff deletes safety-keyword lines, adds dangerous patterns, touches forbidden zones, or weakens the guardrail |
| `CI` / Validate React static diagnostics | `react-doctor` with **zero tolerance: warnings fail too**, not just errors | Any diagnostic, including `warning` severity (`unused-export`, `async-defer-await`, …) |
| `CI` / Validate backend / frontend | ruff, bandit, mypy, lint-imports, pytest+coverage, vitest, build | Conventional test/lint/type failures |
| `CI` / python-freeze | `server/scripts/qa/python_freeze_check.mjs` (run by the job with `--base-ref`/`--head-ref`): PR diffs must not touch `src/**`, `tests/**`, `alembic/**`, `scripts/**`, `pyproject.toml`, or `uv.lock` unless the PR is labeled `python-freeze-exception` | The PR modifies the frozen Python implementation outside an approved exception |
| `CI` / Validate workspace gates (server) | Node twins of the Python QA gates (`server/scripts/qa/`, run via `pnpm --dir server gates`): SSOT, repo hygiene, file-size budgets over the pnpm workspace | Version/identity drift, forbidden residues, or a file over the 300 code-line budget in `server/` or `frontend/` |
| `CI` / Validate server architecture | dependency-cruiser (`pnpm --dir server arch`): the six `.importlinter` contract twins plus the two audit gap closures — interface must not import shared infrastructure (F-8) and the ai context is a leaf reachable only through its application ports | A `server/src` module breaks layering or reaches into `contexts/ai` past its ports |
| `CI` / Validate server types and lint / Test server | `tsc --strict`, Biome (server only), vitest with Fastify `inject()` | Conventional test/lint/type failures in the TS backend |

## Runbook: python-freeze exceptions

The Python tree is frozen for the TS rewrite (#260): PRs touching
`src/**`, `tests/**`, `alembic/**`, `scripts/**`, `pyproject.toml`, or
`uv.lock` fail the `python-freeze` job. The `python-freeze-exception`
label is reserved for security and data-loss fixes in the frozen tree
(and for the Python gates' own retirement at cutover):

1. Apply the label only on a PR whose changes are strictly within the
   exception's purpose; the label exempts the whole PR, so keep such PRs
   minimal.
2. Say why the label is warranted in the PR description, citing the
   advisory or incident.
3. The label is read from the PR event; if you add it after a red run,
   re-run the job (push or re-run `python-freeze` only).

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

## Runbook: safety-keyword deletions in large refactors

`Check AI regression diff` fails when a diff deletes lines containing
`raise / validate / sanitize / escape / auth / permission` keywords. For
planned, reviewed refactors (e.g. repo-wide renames) that must touch such
lines, add an entry to `scripts/ai/regression_check_exemptions.txt` in the
same PR:

```text
src/legacy/auth_wiring.py :: auth :: planned rename, ref #250
```

The registry is version-controlled so reviewers see the exemption next to the
deletion it permits. Entries must cite a tracking issue, only exempt one
exact path+keyword pair, and should be removed once the refactor lands. The
guardrail file itself cannot be exempted; malformed entries fail closed.

## Dependabot status

Dependabot version updates are **disabled** (#238): it updated
`frontend/package.json` without regenerating the root `pnpm-lock.yaml`,
so every run died at `pnpm install --frozen-lockfile`
(`ERR_PNPM_OUTDATED_LOCKFILE`) and cascaded into CodeQL failures. If it is
ever re-enabled, restrict it to the `github-actions` ecosystem, or use a
bot that regenerates pnpm workspace lockfiles (Renovate).
