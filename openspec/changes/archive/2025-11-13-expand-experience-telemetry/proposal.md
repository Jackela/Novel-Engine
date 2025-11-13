# Proposal: expand-experience-telemetry

## Why
- The current Experience Report is Markdown-only and lives in CI artifacts; stakeholders want an HTML view with visual status badges for CTA/Offline outcomes.
- Connection indicator logs now emit to console, but there is no structured telemetry channel (window event bus / API) to aggregate outages over time.
- Docs mention the report at a high level, yet lack step-by-step instructions for downloading artifacts, reading HTML summaries, or tapping into the telemetry stream.

## What
1. Evolve the Experience Report generator to emit both Markdown and HTML, with summary tables/screenshots and an optional JSON snippet for downstream automation.
2. Provide a lightweight telemetry dispatcher so connection indicator events are sent to `window.__novelEngineTelemetry` (or HTTP hook) for future ingestion, satisfying devtools/observability needs.
3. Expand documentation/onboarding with concrete instructions to download reports from CI, interpret the HTML widgets, and subscribe to telemetry events.

## Success Criteria
- New requirements captured in `frontend-quality`, `devtools-audit`, and `docs-alignment` specs.
- `tasks.md` outlines implementation steps for dual-format reports, telemetry dispatcher, CI artifact upload, and doc updates.
- `openspec validate expand-experience-telemetry --strict` passes.
