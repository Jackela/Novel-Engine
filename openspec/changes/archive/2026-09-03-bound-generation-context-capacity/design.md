# Design: bounded prompt assembly and linear Lore promotion

## Capacity unit and threshold

The owned resource is the actual UTF-8 request text passed to the Provider, so
capacity is measured as `Buffer.byteLength(systemPrompt) +
Buffer.byteLength(userPrompt)`. The fixed limit is 8,388,608 bytes. This is
large enough for the existing 4 MiB maximum imported chapter plus resident and
Lore context, while remaining an eightfold, explicit ceiling relative to the
HTTP request-body limit. It is a server safety bound, not a promise that every
Provider model accepts that context window.

The typed domain error carries `limit` and a saturated `observed` value of at
most `limit + 1`. HTTP maps it to status 422, code
`GENERATION_CAPACITY_EXCEEDED`, fixed message `Generation capacity exceeded.`,
and details `{resource:"prompt_bytes",limit,observed}`. No input excerpt,
document id, path, provider secret, or partial prompt appears in the envelope.

## Bounded prompt writer

One application-layer `BoundedPromptWriter` hides UTF-8 accounting and final
joining. It is initialized with the already-counted system prompt, accepts
ordered prompt lines/fragments, includes separators in the count, and stops at
the first fragment that would exceed the limit. It never retains text after
refusal and reports only `limit + 1`.

The writer is the only materialization path behind `buildProposalTask`; callers
cannot obtain an unchecked prompt. Resident and Lore rendering feed this
builder in their existing order. The capacity decision completes before
Provider factory construction, SSE response hijacking, or fresh Job evidence.
Existing stored source strings may already occupy bounded database-read memory;
this change does not claim to paginate project reads.

## Digest bound

`chapterDigest` first flattens prose, then retains at most 60 whitespace words
and at most 512 Unicode code points, appending one ellipsis when either limit
truncates. The code-point pass handles Chinese and emoji without splitting a
surrogate pair; an unpaired surrogate counts as one code point. Every prior
chapter still receives one ordered digest or the existing empty placeholder.

## Lore planner

For each already-matched entry, the planner computes the encoded heading,
summary body, full body, complete summary fragment, complete full fragment,
and their rendered lengths once. It computes the all-summary floor once and
uses two stable passes over the original match order: title matches, then alias
matches. A promotion is accepted when its `full - summary` delta keeps the
rendered Lore section inside the configured character budget. The plan is
rendered once after decisions.

This makes planning `O(total rendered bytes + M)` and linear auxiliary memory
for `M` matches. Matching complexity and substring semantics are unchanged.
Tests instrument content/summary rendering calls rather than timing the host.

The Lore promotion budget remains a soft full-text budget: summaries are the
floor even if they exceed it. The aggregate 8 MiB prompt bound is the hard
safety boundary. If the summary floor or any other complete context crosses
that boundary, generation fails rather than dropping an entry.

## Entry-point and retry behavior

- Fresh synchronous generation assembles and admits the task before creating a
  Provider. Capacity refusal leaves no Job/event/usage/proposal evidence.
- Streaming generation performs the same work before the route hijacks SSE, so
  the caller receives the normal JSON 422 envelope.
- A keyed retry may claim its attempt before rebuilding the prompt. Its first
  permanent capacity refusal lands exactly one failed retry Job and event with
  a closed structured capacity outcome, then returns 422. Same-key replay
  reconstructs the same public error without assembling context or constructing
  a Provider. A different key is a new attempt and may succeed after content is
  reduced.
- Whole-book uses streaming generation. A refusal stops at that chapter,
  preserves all already accepted revisions, and starts no later chapter.

## Options rejected

- Four MiB would make an exact-limit imported target chapter undraftable once
  unavoidable prompt framing is included.
- A configurable aggregate limit creates deployment-dependent correctness and
  another tuning surface; the existing Lore budget already controls attention.
- Token estimates are Provider/model dependent and do not directly bound local
  string or transport memory.
- Dropping matched summaries violates the current canon-visibility contract.
- Wall-clock performance tests are flaky and cannot prove algorithmic work.
- Checking only after `lines.join()` permits the oversized allocation this
  change is meant to prevent.
