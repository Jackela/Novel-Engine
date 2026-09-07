# Bound generation context capacity

## Why

The proposal response is bounded, but the prompt sent to a Provider is not.
The nominal 60-word prior-chapter digest does not truncate Chinese or other
text without spaces, every prior chapter is retained, and all matching Lore
summaries remain even when the Lore promotion budget is one character. A
legacy import can therefore build a resident prompt near the 64 MiB workspace
limit, while API-created projects can continue accumulating documents.

Lore promotion also rebuilds and rerenders the entire plan for each matched
entry. Ten thousand matches perform roughly one hundred million plan visits
and repeatedly scan entry bodies before a Provider is called.

## What Changes

- Cap each prior-chapter digest at 60 words and 512 Unicode code points.
- Cap the complete Provider prompt (`systemPrompt` plus `userPrompt`) at
  8,388,608 UTF-8 bytes, including all fixed labels and delimiters.
- Fail before Provider construction with a stable permanent 422 capacity error
  whose observed value is bounded to `limit + 1`.
- Keep every matched Lore entry represented by its summary; never silently
  drop canon to fit the aggregate limit. Reject the whole generation when the
  complete prompt cannot fit.
- Replace repeated whole-plan Lore rendering with one precomputation,
  deterministic title/alias passes, incremental promotion deltas, and one
  final render.
- Persist keyed-retry capacity failure as one failed retry Job/event with a
  replayable structured outcome; same-key replay performs no Provider or
  context work and returns byte-identical 422 evidence.

## Impact

- Normal prompts remain byte-identical. Extremely large existing projects fail
  loudly and permanently until their generation context is reduced.
- Synchronous and pre-stream requests receive a normal JSON 422 without a Job,
  event, usage row, proposal, or Provider instance. Whole-book generation
  stops at the refused chapter and preserves earlier accepted work.
- No database migration, dependency, environment variable, route, or success
  payload change is required. The HTTP error catalog and OpenAPI gain one
  stable capacity envelope.

## Non-goals

- No truncation of the target manuscript, outline, Lore body, or matched-entry
  set.
- No configurable aggregate prompt limit or Provider-specific token estimate.
- No change to Lore matching, lifecycle eligibility, summary source, promotion
  priority, or the 4,000-character default promotion budget.
- No coherent-revision read transaction or retry-base correction; those are a
  separate consistency change.

## Validation

- Exact and plus-one UTF-8 prompt boundaries with ASCII, Chinese, emoji, fixed
  labels, and delimiters included.
- 60-word/512-code-point digest cross-product, including no-space text and
  unpaired surrogates.
- Fresh sync/stream, keyed retry/replay, and whole-book refusal evidence.
- Deterministic large-M planner instrumentation proving each matched body and
  summary is rendered once without wall-clock assertions.
- OpenAPI/type drift, server/frontend tests, architecture/size gates, strict
  OpenSpec, and fixed-SHA evidence.
