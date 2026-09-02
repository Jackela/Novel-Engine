# Tasks

## 1. Capacity policy and digest boundary

- [x] 1.1 Add a typed immutable generation-capacity policy for 8,388,608 UTF-8
      prompt bytes and a closed `prompt_bytes` resource/error envelope with
      safe integer and saturated-observation tests.
- [x] 1.2 Add red digest tests for 60/61 words, 512/513 code points, Chinese
      without spaces, emoji, mixed whitespace, and unpaired surrogates.
- [x] 1.3 Enforce both digest dimensions without changing short benign digests,
      prior-chapter coverage, ordering, or empty placeholders.

## 2. Linear Lore planning

- [x] 2.1 Add exact-budget and plus-one fixtures preserving summary floor,
      title-before-alias priority, reading-order ties, and byte-identical benign
      rendering after prompt-data encoding.
- [x] 2.2 Add deterministic instrumentation for M and 2M matches proving each
      summary/full representation is computed once and no whole-plan candidate
      copy/render occurs per promotion.
- [x] 2.3 Replace the quadratic planner with precomputed fragments, incremental
      promotion deltas, stable rank passes, and one final render.

## 3. Bounded task assembly

- [x] 3.1 Add a bounded prompt writer that accounts for system text, user text,
      separators, and UTF-8 multi-byte input before retaining the next fragment.
- [x] 3.2 Add exact and plus-one task tests proving accepted prompts are
      byte-identical and refusal retains no oversized joined prompt.
- [x] 3.3 Route resident/Lore/manuscript assembly through the single writer and
      complete admission before Provider factory construction.

## 4. Entry points and persistent retry evidence

- [x] 4.1 Add fresh sync and pre-SSE API tests for exact/plus-one capacity,
      stable 422 JSON/OpenAPI, no Provider construction, and no Job, event,
      usage, proposal, or revision evidence.
- [x] 4.2 Add keyed retry tests for one failed retry Job/event, closed structured
      capacity result, byte-identical same-key replay without context/Provider
      work, and a distinct-key attempt after content reduction.
- [x] 4.3 Add whole-book tests proving capacity refusal stops the loop, preserves
      earlier accepted chapters, and starts no later chapter.
- [x] 4.4 Regenerate OpenAPI and frontend types and pass drift/CORS/error-catalog
      checks without changing success payloads.

## 5. Integrated evidence

- [ ] 5.1 Run resident/Lore/provider/pipeline/retry/whole-book tests, server
      type-check/lint/arch/size/full tests, frontend type/unit/build, Playwright,
      API-types drift, and strict OpenSpec.
- [ ] 5.2 Record fixed-SHA evidence and all skips. Keep coherent proposal-context
      transactions, retry base-revision semantics, and project/catalog
      pagination as named later changes.
- [ ] 5.3 Keep the change active until required CI is green, then merge it into
      the canonical specification and archive it.
