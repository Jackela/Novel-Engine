---
name: openspec-change
description: Run a product change through this repository's OpenSpec workflow — draft a dated change folder with proposal, design, tasks, and spec deltas written as Requirements with GIVEN/WHEN/THEN scenarios, then pass the strict OpenSpec validation gate. Use when adding or changing product behavior that belongs in the Novel Studio capability specification.
---

# OpenSpec change workflow

`openspec/specs/novel-studio/spec.md` is the product single source of truth.
Behavior changes land as OpenSpec change folders before or alongside the code
that implements them.

## Drafting a change

1. Create `openspec/changes/YYYY-MM-DD-<kebab-slug>/` with today's date and a
   short imperative slug.
2. Write `proposal.md` with three sections: `## Why` (the problem in product
   terms), `## What Changes` (bullet list of behavior deltas), `## Impact`
   (breaking changes, migrations, affected surfaces).
3. Add `design.md` only when the change is architectural — options considered
   and the chosen approach. Skip it for mechanical changes.
4. Write `tasks.md` as numbered checkbox groups, one group per area of work.
   Each task is one small verifiable step (a test, a route, a panel), matching
   the repo's one-task-one-finding discipline.
5. Put spec deltas in `specs/<capability>/spec.md` inside the change folder,
   using `## ADDED Requirements` / `## MODIFIED Requirements` sections. Each
   `### Requirement:` uses RFC-2119 keywords (MUST/SHOULD) and each
   `#### Scenario:` follows GIVEN/WHEN/THEN, in the style of the main spec.

## Validating and archiving

- Validate with `corepack pnpm spec:validate` (runs `openspec validate --all
  --strict`); it must pass before a change counts as drafted.
- After implementation, when CI is green, archive the change: the deltas are
  applied into `openspec/specs/` and the change folder moves unchanged to
  `openspec/changes/archive/`. See the archived
  `2026-06-13-consolidate-novel-studio-0-3` change for a scale reference.

## Boundaries

- The spec describes observable product behavior, not implementation.
  Persistence and layering details belong in `design.md`, never in
  Requirements.
- During a live change, edit the change folder — do not edit
  `openspec/specs/` directly; deltas merge at archive time.
