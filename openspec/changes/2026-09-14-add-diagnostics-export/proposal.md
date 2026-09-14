# Opt-in diagnostics export

## Why

A self-hosted author who hits a problem has no good way to attach
environment evidence to a bug report: the useful facts (product version,
runtime summary, configuration state, database health) are scattered across
the `doctor` CLI output, the settings panel, and the release notes, and
some of them need shell access the target audience — a non-technical author
running one compose command — does not have. Iteration-3 item C11 closes
this with an explicit, opt-in export in the product UI. The trust posture
is the campaign's A2-07 finding: Novel Engine's language is physical data
ownership, and diagnostics follows it — the file is generated only when the
author clicks, lands only on the author's machine through the browser's own
download, and goes nowhere unless the author decides to send it. Zero
telemetry is a positioning commitment, not just a default; this change must
not erode it.

## What Changes

- The project Settings panel gains an "Export diagnostics" action. One
  click requests a diagnostics summary from the Studio's own read-only
  project-scoped endpoint and saves it locally as a downloadable JSON file
  with a client-derived filename (`novel-engine-diagnostics-<date>.json`),
  following the existing client-derived export download behavior.
- The diagnostics summary contains: product identity and version (the
  release-version SSOT), a runtime environment summary (platform and
  runtime versions), a configuration summary (resolved provider selection
  with its human-readable label, and the set/unset state of recognized
  configuration keys), a recent error summary drawn from the current
  project's most recent failed Jobs when any exist, and a database health
  summary with the same field family as `doctor` (integrity check, journal
  mode, foreign-key enforcement, owner status).
- The error summary presents only what Jobs durably record — each failed
  Job's persisted error message. The HTTP envelope's error `code` exists
  only at response time and is not persisted, so it is not presented;
  provider failures stay inside the provider failure diagnostics boundary
  and no provider response body reaches the export.
- Redaction is absolute and structural: the summary schema contains no
  field capable of carrying a secret value — secret values (the session
  secret and any provider API key) never appear in the export, not
  masked, not truncated — and configuration state is reported as
  configured/unconfigured or set/unset booleans only, proven by tests that
  seed real-looking secrets and assert their absence from the serialized
  output.
- The database health summary reproduces `doctor`'s field family through
  the app's own database handle — the API never shells out to the CLI.
- The action surface displays the privacy statement (copy below) before
  and during use, so the author always knows what the file contains and
  that nothing is sent anywhere.
- Zero telemetry, zero upload: generating the export performs no network
  activity beyond the Studio's own read-only endpoint, and the product
  never transmits the file — where it goes is entirely the author's
  decision.
- The summary is assembled server-side by one new owner-guarded read-only
  endpoint scoped to the current project (matching its Settings-panel
  mount point), so the redaction rules and health fields have one
  implementation; no manuscript content, document bodies, or Lore entries
  are included — diagnostics describes the machine, never the book.

## Impact

- Frontend: one Settings panel action, privacy statement, download flow in
  `frontend/src/features/studio/`; generated API types regenerate. Backend:
  one diagnostics assembly service and one owner-guarded read-only
  project-scoped route (`/api/projects/:projectId/diagnostics`, matching
  the project Settings mount point).
- The OpenAPI baseline regenerates (route-adding change), serially with
  any other route-adding change in the same window.
- No database migration, no new dependency, no environment variable, no
  change to `doctor`, backup, restore, or any existing CLI command.
- Spec: one added requirement (Opt-in diagnostics export) in the
  `novel-engine` capability.
- Campaign linkage: iteration-3 item C11, built on the A2-07
  physical-data-ownership trust language recorded in
  `docs/agents/productization-2026-09-13.md`.

## Privacy statement copy

The action surface displays this statement (English UI, matching the
#615/#634 dictionary family; the zh-CN dictionary ships the parallel
translation):

> Diagnostics contains version, environment, configuration status, recent
> error summaries, and database health — nothing you wrote, no API keys.
> It is saved as a file on your computer; Novel Engine never sends it
> anywhere. Share it only if you choose to.

## Non-goals

- No telemetry, crash reporting, or update pings — the product keeps
  making zero outbound requests of its own.
- No database export, backup, or manuscript content in the file — data
  export stays with the existing backup/export capabilities.
- No diagnostics history, diffing, or automatic attach-to-issue
  integration.
- No new CLI surface; `doctor` remains as-is.
