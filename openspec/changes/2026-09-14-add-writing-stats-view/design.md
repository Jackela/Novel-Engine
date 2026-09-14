# Design: local writing statistics view

## Context

The view has one hard rule: derive everything, record nothing. Its numbers
must be reproducible from data the product already persists, which makes
the attribution rules (not the rendering) the design surface. This document
fixes those rules so the server aggregation and the panel cannot drift.

## Word-count SSOT

The codebase already fixes one counting rule: the unified word-count
definition used by the usage fallback when a provider reports no usage
data. Every figure in the stats view — daily deltas, weekly rollups,
chapter non-emptiness — uses that same definition via the same helper.
A second counting rule would make the stats view disagree with usage
figures for identical text, which is exactly the drift this change exists
to prevent.

## Attribution: word-count deltas over immutable revisions

Revisions are immutable and server-stamped with `source` (`author`,
`ai-accepted`, `restore`). The attribution rule:

- Each revision contributes the word-count delta against its parent
  revision of the same document (created-at timestamp buckets it into a
  calendar day, project-local dates).
- The delta is attributed to that revision's `source`.
- A document's first revision has no parent; its full word count is
  attributed to its source as-is.
- `restore` revisions are rollback reads of prior content: they are
  attributed to `restore` and reported as their own line (they are history
  movement, not new writing). They neither extend the streak nor count
  toward author-written words.

This is honest about precision: AI-accepted text is "text the author
accepted", author text is "text saved from the editor" — exactly what the
data can prove, with no heuristic re-labeling.

## Streak definition

A writing day is a calendar day (project-local) with at least one
`author` revision. The streak is the length of the consecutive chain of
writing days ending today, or ending yesterday when today has no author
revision yet (so the streak survives until the day is over). Display-only;
no persistence, no notifications.

## Completion definition

The chapter completion share is started chapters (current content word
count > 0) over all chapter documents in reading order. No targets, no
per-chapter expected length — anything more invents author input this
change explicitly does not collect.

## Server-side aggregation, one endpoint

The rules above are implemented once, server-side, behind one
owner-guarded read-only project endpoint (`/api/projects/:projectId/stats`
shaped by the existing route family). Rationale: the attribution rules are
product semantics, and putting them client-side would force the frontend to
reconstruct revision chains through the paginated history endpoint
(bounded reads make full-history reconstruction impossible for real
projects anyway). The endpoint performs one bounded aggregation over
revisions, structure, and the existing usage aggregation, and returns the
rendered-ready summary the panel maps directly.
