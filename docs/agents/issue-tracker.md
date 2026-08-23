# Issue tracker: GitHub Issues

Issues and specs for this repo live as GitHub issues at
`https://github.com/Jackela/Novel-Engine/issues`.

- Creating: `gh issue create --repo Jackela/Novel-Engine` with a title and
  body; label with the triage labels in `docs/agents/triage-labels.md`.
- Reading: `gh issue list --repo Jackela/Novel-Engine --state open`;
  `gh issue view <number>`.
- Closing: `gh issue close <number>` with a comment pointing at the resolving
  commit or PR.
- Specs produced by `/to-spec` are published as issues and linked from the
  change or PR that implements them; tickets produced by `/to-tickets` declare
  their `## Blocked by` edges in the body and as native blocking links when
  available.

## Skill conventions

- When a skill says to publish to the issue tracker, create a GitHub issue in
  `Jackela/Novel-Engine`.
- When a skill says to fetch a ticket, use `gh issue view <number> --comments`
  and inspect its labels.
- Apply the five canonical triage roles through the tracker-label mapping in
  `docs/agents/triage-labels.md`.

## Pull requests as a triage surface

**PRs as a request surface: no.** Work intake and triage use GitHub Issues;
PRs may be linked as implementation evidence but are not part of the triage
queue.

## Wayfinding operations

- The map is a single GitHub issue labeled `wayfinder:map`; its decision
  tickets are child issues of that map.
- Tickets are claimed by assignment (the assignee is the claim). Blocking
  edges prefer the tracker's native sub-issue/blocking relationships, with
  `## Blocked by` body sections as the fallback.
- Ticket types use `wayfinder:<type>` labels (for example
  `wayfinder:decision`, `wayfinder:research`, `wayfinder:task`).
- The map issue body carries `## Destination`, `## Not yet specified`, and
  `## Out of scope` sections; sessions update it in place.
