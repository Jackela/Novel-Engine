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

## Progressive disclosure under the injection budget (#445)

The gate decides **whether** an entry may inject; it says nothing about
**how much** injects. Unbounded full-text injection scaled linearly with the
number of stable hits: a project whose outline references many characters
shipped every referenced body verbatim, and the lorebook section could
overwhelm the manuscript it exists to serve.

The adjudicated strategy, and the alternatives refused:

- **Summary line first, budgeted promotion** (progressive disclosure): every
  matched entry enters the lorebook section as `### Title (summary only)`
  plus one flattened line from the entry's own opening paragraph, then
  entries are promoted to full text greedily while the rendered section fits
  the injection budget. Promotion priority is deterministic: title hits
  before alias hits, ties in the documents' reading order. Summaries are the
  floor — an entry the budget cannot hold stays visible as a summary line
  and is never silently dropped; the heading suffix marks the withholding so
  the model cannot mistake a summary for the whole entry.
- **Summary source is an existing field**: the entry's own markdown opening
  (first prose paragraph after leading headings, flattened; the full
  flattened body when the text opens with nothing but headings). No new
  author-required field, no migration. A hand-maintained `summary` column
  was refused: it adds authoring burden and a second text to drift against
  for a value the opening paragraph already carries.
- **Budget is measured in characters, on the rendered section**: the unit is
  the assembled lorebook block itself (headers, headings, bodies, summary
  lines), so what is measured is exactly what is rendered. Token estimates
  were refused as a hidden model-dependent conversion. The budget bounds the
  section, not a hard cut: summaries survive any budget, so no input size
  can silently erase canon.
- **Single assembly point**: the plan-and-render runs inside
  `triggeredLoreSections` behind `buildProposalUserPrompt`, which every
  proposal pipeline (synchronous draft, SSE stream, retry, and the
  whole-book loop built on them) already shares. The budget never forks the
  prompt assembly.
- **Default `4000` characters** (`DEFAULT_LOREBOOK_BUDGET_CHARACTERS`,
  env `LLM_LOREBOOK_BUDGET_CHARACTERS`, positive integer): a typical
  proposal prompt at this scale runs roughly 10k–40k characters (resident
  context of outline, per-chapter digests, a 1200-character tail, plus the
  manuscript), so 4000 characters is a deliberate ceiling of roughly
  10–15% of a typical prompt — about 1.0k–1.3k tokens at the conservative
  ~3–4 characters per token for mixed Chinese/English prose. It holds full
  text for roughly 5–10 typical entries or summary lines for dozens, which
  covers realistic per-chapter key-hit counts while an unbounded section can
  exceed the manuscript itself. Operators with bigger lorebooks raise the
  env value; the budget is a prompt-share dial, not a correctness knob.

### Consequences of this section

- Match results now carry a rank (`title` vs `alias`) so promotion priority
  is computable; selection semantics (substring, case-insensitive, either
  corpus) are unchanged.
- Without a key hit nothing renders, exactly as before; below the budget the
  section renders full text exactly as before, so pre-#445 prompts are
  unchanged when lore fits. Only over-budget sections demote to summaries.
- The lorebook env budget joins the server config seam (`LlmServerConfig`);
  the shared mirror constant is kept in step with
  `lore_injection.ts` deliberately (shared never imports bounded contexts).
