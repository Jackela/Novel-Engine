## MODIFIED Requirements

### Requirement: Usage accounting for AI requests

Every completed AI proposal request and every successful retry MUST record a
usage event capturing prompt and completion token counts with an estimated
cost. A provider-reported token count MUST be used exactly only when it is a
non-negative JavaScript safe integer from zero through
`9,007,199,254,740,991`. A missing, negative, fractional, non-finite, or unsafe
provider count MUST be treated as absent and MUST fall back to the unified
word-count estimate. The same rule MUST apply to synchronous, streaming, and
retry outcomes.

Every persisted token count MUST remain a non-negative safe integer. An unsafe
usage input that bypasses provider normalization MUST be rejected atomically
with its paired completed-job or retry transition: neither the terminal job
change nor the usage event may commit. Valid counts, including zero and the
maximum safe integer, MUST NOT be rounded, clamped, or replaced by estimates.

#### Scenario: Provider-reported usage is recorded

- **GIVEN** a provider reports prompt and completion counts that are non-negative safe integers
- **WHEN** a synchronous proposal, stream, or retry completes
- **THEN** the usage event records those counts exactly
- **AND** zero and `9,007,199,254,740,991` remain unchanged

#### Scenario: Missing usage falls back to word counts

- **GIVEN** a provider reports a missing, negative, fractional, non-finite, or unsafe token count
- **WHEN** a synchronous proposal, stream, or retry completes with valid generated prose
- **THEN** that count is derived from the unified word-count definition
- **AND** no rounded, clamped, non-finite, or null token value is persisted

#### Scenario: Unsafe direct usage input is atomic

- **GIVEN** an internal usage write supplies a count outside the non-negative safe-integer range
- **WHEN** it attempts to complete a proposal job or retry outcome
- **THEN** the usage write is rejected
- **AND** neither the usage event nor its paired terminal job transition commits

### Requirement: Project usage surface

The API MUST expose `GET /api/projects/:projectId/usage` to the owner,
aggregating the project's recorded usage events: total prompt tokens, total
completion tokens, request count, a per-model breakdown, and the established
trailing daily buckets. Every successful count and sum MUST be exact and
representable as a non-negative JavaScript safe integer. The API MUST retain
its existing successful response shape and MUST NOT emit rounded counts,
non-finite values, or JSON `null` for integer fields.

If a stored token value or aggregate cannot be represented exactly in that
range, the read MUST fail loudly through the existing opaque
`INTERNAL_ERROR` response rather than returning fabricated usage.

#### Scenario: Aggregates reflect recorded events

- **GIVEN** safe usage events across two models and multiple days
- **WHEN** the usage surface is read
- **THEN** project, per-model, and daily totals equal the exact recorded sums
- **AND** the successful response shape and per-model separation are unchanged

#### Scenario: Corrupt or unsafe aggregate fails loudly

- **GIVEN** historical ledger data contains a non-integer, non-finite, negative, unsafe, or collectively unsafe token total
- **WHEN** the usage surface is read
- **THEN** the request fails with the opaque `INTERNAL_ERROR` envelope
- **AND** no rounded number, `Infinity`, or JSON `null` is returned as usage
