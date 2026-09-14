# Local writing statistics view

## Why

Everything a writing-statistics view needs is already recorded — every save
creates an immutable Revision stamped with a server-assigned source
(`author`, `ai-accepted`, or `restore`), every AI request lands in the usage
aggregation, and the volume/chapter structure knows what a finished book
looks like — but none of it is visible to the author as writing progress.
The author cannot answer "how much did I write this week, how much of that
was me versus accepted AI text, am I still on a streak" without opening the
database. The 2026-09-13 productization campaign already positioned usage
transparency as a direct anti-subscription differentiator (competitor matrix
A2-03: per-project token/cost usage versus credit black boxes); iteration-3
item C12 extends that from provider usage to the author's own writing
rhythm. Novel Engine's self-hosted, single-author positioning (A2-07
physical-data-ownership trust language) makes this strictly local: the view
derives from data on the author's machine and collects nothing.

## What Changes

- The Studio Inspector gains a `stats` tab (route-backed, like every
  Inspector surface) showing project-scoped writing statistics derived
  entirely from existing data.
- Daily and weekly word counts, attributed by Revision source so author
  writing and accepted AI text are distinguishable wherever the data can
  tell them apart: each Revision contributes the word-count delta against
  its parent, computed with the unified word-count definition, attributed
  to that Revision's source (`author` = the author's own edits,
  `ai-accepted` = accepted proposal text). Revisions whose source cannot
  support attribution are never silently re-labeled.
- One time anchor for every calendar bucket: days are UTC days, the same
  anchor the existing usage aggregation's daily buckets already use — one
  definition, zero new configuration, and honest for a self-hosted studio
  whose author, server, and browser share one machine. The streak's
  "today" and "yesterday" are judged on the current UTC day.
- Chapter count and completion: the number of chapter documents and the
  share of chapters that have been started (non-empty current content).
  Completion is defined against existing content only — no word-count
  targets, no plans, no new author input.
- A writing streak: the count of consecutive UTC days, ending on the
  current UTC day or the one before, on which the project received at
  least one `author` revision. Days with only AI-accepted text do not
  extend the streak; the streak is display-only and derives from the same
  revision history.
- An AI usage summary reusing the existing project usage aggregation
  (request count, prompt/completion tokens, per-model and daily buckets) —
  the same authority as the usage panel, not a second accounting, and the
  same UTC buckets so stats days and usage days line up.
- The statistics are computed server-side by one new owner-guarded
  read-only endpoint so the attribution rules and the UTC bucketing have
  exactly one implementation, and the tab renders lazily on first
  activation like the usage panel.
- Purely local derivation: no new data collection, no telemetry, no
  outbound network requests, and no behavior change to how revisions,
  jobs, or usage are recorded.

## Impact

- Frontend: one new Inspector tab, panel component, and data hook in
  `frontend/src/features/studio/`; generated API types regenerate. Backend:
  one studio application statistics aggregation service and one read-only
  route under the existing thin-route discipline.
- The `stats` tab touches three frontend families shared with the
  lorebook-wizard change's `lore` tab — the Inspector tab union
  (`studioConstants.ts`), route state (`studioRouteState.ts`), and the
  Inspector panels (`StudioInspectorPanels.tsx` /
  `studioInspectorTypes.ts`); the two changes serialize on those files
  (stats first, lore second) rather than editing them in parallel.
- The OpenAPI baseline regenerates (route-adding change), serially with
  any other route-adding change in the same window.
- No database migration, no new dependency, no environment variable, no
  change to revision recording, usage accounting, job semantics, or the
  export/import surfaces.
- Spec: one added requirement (Local writing statistics) in the
  `novel-engine` capability.
- Campaign linkage: iteration-3 item C12, extending the A2-03 usage
  transparency finding and the A2-07 local-trust positioning recorded in
  `docs/agents/productization-2026-09-13.md`.

## Non-goals

- No writing goals, targets, or plan tracking — completion is defined
  against existing chapter content only.
- No cross-project or global dashboards; the view is project-scoped.
- No export of statistics to a file (the export capability stays about
  manuscripts).
- No change to usage accounting itself; the stats view consumes the
  existing aggregation.
- No telemetry of any kind, ever.
