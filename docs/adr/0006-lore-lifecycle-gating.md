# Lore lifecycle gating: only stable entries inject

---
status: accepted
---

Lore entries (character and world documents, ADR-0004 layer 2) carry a
**lifecycle status** — a closed enum of `draft`, `stable`, and `deprecated`.
New lore entries start at `draft`. The keyword-triggered injection gate
admits **only `stable` entries**: a `draft` or `deprecated` entry is skipped
before any key evaluation, with no downweighting and no partial injection.
The status is document-level state (like the alias keys): it survives
metadata-replacing revision saves, and changing it mints no revision.

## Rationale

Before the gate, the only injection filter was "a key occurs and content is
non-empty" (`lorebook.ts` selection). A half-written character document whose
title was merely mentioned in an outline shipped its entire raw body into the
prompt — including notes the author never intended the model to see or rely
on. The lifecycle status makes canonization an explicit author act:
draft freely, then promote to `stable` when the entry is fit for generation.

The adjudicated choices, and the alternatives refused:

- **Binary gate over downweighting**: a `deprecated` entry that still leaks
  half its body at lower priority is worse than one that leaks nothing.
  Scoring injection strength would add a tuning surface without a
  demonstrated need.
- **Trust stays on `revision_source`**: no separate trust field. The revision
  source (author / ai-accepted / restore) remains the provenance signal;
  entry-level trust escalation is a future concern, deliberately out of
  scope, as are tags, links, and sources.
- **Status change is a dedicated revision-free write** (the lore surface,
  beside the alias keys), not a document save: a status flip is gating
  metadata, not authoring content. Routing it through the save channel would
  mint a history revision per toggle, require a base revision id (inviting
  bogus conflicts), and force conditional payload schemas that only lore
  kinds may carry the field.

**Existing entries migrate to `stable`.** Every lore document that predates
the gate was already serving as canon — it injected on key hits by the old
contract, and the author kept it in the project knowing that. Defaulting the
backfill to `draft` would silently strip every project's lore from
generation after upgrade: a behavior regression disguised as caution. The
migration therefore pins the adjudication explicitly: pre-gate lore entries
are author-approved canon and read `stable` after migration; `draft` is
reserved for entries created under the new contract. Non-lore kinds keep the
column at its default and ignore it — the lifecycle semantics never leak
beyond lore (`lore_status` reads as null for them in every payload).

## Consequences

- `documents` gains a `lore_status` column (migration `0011`); the payload
  SSOT exposes `lore_status` (closed enum, null for non-lore kinds) and the
  lore surface answers the status write.
- Prompt composition is now gated twice: lifecycle first, then content and
  key match. A `draft` entry with a matching title contributes nothing.
- The Studio Inspector shows a status selector for lore documents, and the
  navigator shows a per-entry status badge; the accessible row name carries
  the status.
- New lore entries no longer inject until promoted — this is the intended
  friction. Reviewers of prompt regressions should first check whether the
  entry is still `draft`.
- **Re-evaluation triggers**: if authors report stale-canon drift (entries
  that should retire but keep injecting), consider scheduled review prompts
  for `stable` entries; if per-passage precision is ever needed, revisit the
  document-as-entry choice (ADR-0004) together with this gate before adding
  finer-grained statuses; if a `planned` or `quarantined` state is ever
  proposed, it must justify itself against the three-state enum's failure
  modes, not as an additional bucket by default.
