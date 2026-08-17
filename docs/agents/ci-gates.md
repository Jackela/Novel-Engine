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
