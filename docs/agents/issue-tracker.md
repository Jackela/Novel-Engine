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
