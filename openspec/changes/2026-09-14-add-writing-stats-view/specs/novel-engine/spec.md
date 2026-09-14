## ADDED Requirements

### Requirement: Local writing statistics

The Studio MUST offer a project-scoped writing statistics view as an
Inspector tab with URL-backed activation, computed server-side by one
owner-guarded read-only endpoint. All word figures MUST use the unified
word-count definition. Daily and weekly word counts MUST be attributed by
Revision source so author edits and accepted proposal text are
distinguishable: each Revision MUST contribute the word-count delta against
its parent revision, attributed to that Revision's source, with a first
Revision attributed in full to its own source. Every calendar bucket —
daily rows, weekly rollups, and streak days — MUST use UTC days, the same
anchor as the existing usage aggregation's daily buckets. The view MUST
show the chapter count and the share of chapters with non-empty current
content, MUST show a writing streak defined as consecutive UTC days, ending
on the current UTC day or the one before, each containing at least one
`author` Revision, and MUST present an AI usage summary reusing the
existing project usage aggregation rather than a second accounting. The
statistics MUST be derived only from already-recorded data — Revisions,
project structure, and usage events — and the feature MUST NOT add data
collection, telemetry, or any outbound network request.

#### Scenario: Daily words split by source

- **GIVEN** a project where on one UTC day the author saves 500 new words by hand and accepts a proposal adding 300 words
- **WHEN** the statistics view renders
- **THEN** that UTC day shows 500 words attributed to author edits and 300 words attributed to accepted proposal text
- **AND** both figures use the unified word-count definition

#### Scenario: Weekly rollup matches its days

- **GIVEN** daily word counts for the UTC days of one week
- **WHEN** the weekly figure renders for that week
- **THEN** it equals the sum of that week's per-day attributed figures

#### Scenario: Streak counts author writing days only

- **GIVEN** the author saved an `author` revision every UTC day for five consecutive UTC days, and the previous UTC day ended with only an accepted proposal
- **WHEN** the streak renders
- **THEN** UTC days containing only AI-accepted text do not extend the streak
- **AND** the chain counts consecutive `author`-revision UTC days ending on the current UTC day or the one before it

#### Scenario: Chapter completion reflects existing content

- **GIVEN** a project with ten chapter documents of which seven have non-empty current content
- **WHEN** the statistics view renders
- **THEN** it reports ten chapters and a 7-of-10 started share
- **AND** no word-count target or plan input is requested or stored

#### Scenario: Usage summary reuses the usage aggregation

- **GIVEN** a project with recorded usage events
- **WHEN** the statistics view renders its AI usage summary
- **THEN** request and token figures match the existing project usage aggregation for the same project
- **AND** its daily buckets use the same UTC days as the statistics view's day rows
- **AND** no second accounting path exists

#### Scenario: Empty project renders a defined state

- **GIVEN** a project with no revisions and no usage events
- **WHEN** the statistics view renders
- **THEN** it shows defined zero states for words, chapters, streak, and usage instead of errors or placeholders

#### Scenario: Statistics stay local

- **GIVEN** the statistics view is open
- **WHEN** it renders and refreshes
- **THEN** it issues no network request beyond the Studio's own read-only statistics endpoint
- **AND** nothing is recorded that did not already exist as a Revision, job, or usage event
