# Enforce safe usage-token accounting

## Why

Provider usage fields currently accept any non-negative JavaScript integer.
That includes numbers above `Number.MAX_SAFE_INTEGER`, such as `1e308`, whose
value cannot be persisted or added exactly. SQLite can store those values as
REALs, repeated totals can become `Infinity`, and JSON serialization can turn
the result into `null`. The usage ledger must never replace exact accounting
with rounded, non-finite, or schema-invalid values.

## What Changes

- Define an accepted token count as a non-negative JavaScript safe integer at
  the provider, application, and persistence boundaries.
- Treat a provider's negative, fractional, non-finite, or unsafe token value as
  absent usage and use the existing unified word-count fallback.
- Reject unsafe direct persistence inputs inside the same transaction that
  would land the completed job or retry outcome.
- Add database CHECK constraints that permit only non-negative safe integer
  prompt and completion counts, using a generated migration.
- Add exact checked aggregation so corrupt or unrepresentable stored totals
  fail loudly instead of rounding or rendering `Infinity`/`null`.

## Impact

- Valid provider counts from zero through `9,007,199,254,740,991` retain exact
  accounting and the current successful response shapes.
- Invalid provider usage no longer reaches SQLite; it follows the existing
  missing-usage fallback without failing an otherwise valid proposal.
- An internal caller that bypasses provider normalization and supplies an
  unsafe count fails atomically, so neither its usage row nor paired terminal
  job transition commits.
- Existing corrupt ledger data prevents the constraint migration or a usage
  aggregate from presenting invented values; it is not silently coerced.

## Non-goals

- No pricing, estimated-cost, billing, model-selection, or token-estimation
  change.
- No new usage endpoint, response field, pagination contract, or frontend
  behavior.
- No conversion from token counts to floating-point approximations and no
  replacement of exact provider counts with estimates when they are valid.

## Validation

- Provider parsing covers exact safe bounds plus unsafe, non-finite, negative,
  and fractional values for synchronous and streaming transports.
- Proposal, stream, and retry landings prove fallback and transactional
  all-or-nothing persistence.
- Direct store inputs and raw corrupt rows prove CHECK enforcement and
  fail-loud aggregation.
- Server gates, migration-channel validation, strict OpenSpec, and fixed-SHA
  evidence remain required before archive.
