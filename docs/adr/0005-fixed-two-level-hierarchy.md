# Fixed two-level structure: volumes over chapters, chapters linked to beats

---
status: accepted
---

A project's manuscript structure is **fixed at two levels**: the project
holds an ordered list of **volumes**, each volume holds its chapters in
reading order, and every chapter belongs to exactly one volume. Projects
start with a single default volume (creation and legacy import included), so
no chapter is ever unplaced. Additionally, each chapter MAY link to exactly
one **beat** — a unit of the project's outline document — and generation for
that chapter includes the beat's content in its prompt.

## Rationale

The grilling session adjudicated "complete hierarchy" over a minimal
markdown-convention link, but completeness refers to the beat association
being a first-class, spec'd relationship — not to arbitrary nesting depth.
The alternatives considered:

- **Flat documents + markdown convention** (rejected): the chapter→beat link
  would be convention, not contract; nothing enforces it and generation
  cannot rely on it.
- **Arbitrary-depth section tree** (rejected): novels are written at
  volume/chapter granularity; a recursive tree buys nothing and costs
  reorder semantics, UI navigation, export assembly, and query complexity
  at every level.

Fixed two levels with a default volume keeps every invariant total (order is
always well-defined; exports and the library need no special cases), which
matters because `Stable list ordering` and `Snapshot-bound export` already
pin whole-set ordering semantics.

## Consequences

- New `volumes` table and volume/beat columns on chapters via a drizzle
  migration; reorder semantics extend to volume-level and in-volume moves.
- Exports, the library listing, and the whole-book generation loop all read
  volume order.
- Structural validation ("project needs at least one chapter before export")
  and the seeded `Chapter 1` behavior carry over unchanged; import lands
  chapters in the default volume.
- Deeper nesting (parts inside volumes) is a future spec change, deliberately
  not built now.
