# Two-layer generation context: resident layer + keyword-triggered lorebook

---
status: accepted
---

AI generation prompts for a chapter MUST assemble a **two-layer context**:

1. **Resident context** — always injected: the project outline (with the
   current beat position), a rolling summary covering every prior chapter in
   reading order, and the tail of the most recent chapter. This solves the
   cold-start problem (the first generation has no prior text to trigger on)
   and guarantees narrative continuity is never left to chance.
2. **Keyword-triggered lorebook** — character and world documents act as
   lore entries; keys are the document title plus aliases declared in the
   document's metadata, content is the document's current markdown. An entry
   is injected only when one of its keys occurs in the resident context or
   the target manuscript.

## Rationale

The 2026-08-27 audit against popular open-source AI-novel projects found the
single biggest capability gap: our prompts carried only the target chapter,
so continuation was amnesiac. Every mature project assembles character/world
context; SillyTavern's world-info mechanism is the field's reference design
for doing it within a bounded prompt.

The user adjudication is **effectiveness over token economy** — cost is not
the driver. Keyword triggering was still chosen over static full injection
for *attention* reasons: injecting every document dilutes the model's focus
on the material relevant to the scene being written. The resident layer
keeps continuity deterministic while the triggered layer keeps entries
precise. Document-as-entry (rather than a finer-grained entry entity) was
chosen because the character/world document kinds already exist and a new
CRUD surface would be complexity without a demonstrated need; a dedicated
entry entity remains a possible evolution if alias-per-passage precision is
ever required.

## Consequences

- Document metadata gains a product-facing alias list (the lorebook keys).
- The rolling summary is a derived artifact: regenerated as chapters change,
  never author-persisted content; its exact assembly (which model, which
  budget) is implementation detail owned by the proposal pipeline.
- The generation prompt contract is now part of the spec
  (`Resident context injection`, `Keyword-triggered lore entries`);
  changes to layer composition are spec changes, not refactors.
- SSE streaming (#308) depends on this contract and follows it.
