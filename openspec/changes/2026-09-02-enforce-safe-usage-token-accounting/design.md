# Design: exact safe-integer usage ledger

## Accepted numeric domain

One token count is valid only when `Number.isSafeInteger(value)` is true and
`value >= 0`. The closed range is therefore zero through
`Number.MAX_SAFE_INTEGER` (`9,007,199,254,740,991`). `MAX_SAFE_INTEGER` itself
is accepted exactly; `MAX_SAFE_INTEGER + 1`, `1e308`, `Infinity`, negative
numbers, fractions, strings, booleans, objects, and missing fields are not
accepted provider usage.

The provider adapter is the first normalization boundary. An invalid provider
field becomes `null`, preserving the established meaning of absent usage. The
application landing repeats the safe-integer check before resolving the token
count, so injected providers, stream outcome callbacks, retries, and future
adapters cannot bypass the fallback. Invalid reported usage falls back to the
existing unified word count; a valid reported count, including zero, is stored
unchanged.

## Persistence invariant and migration

The usage write helper asserts both counts are non-negative safe integers
before issuing SQL. Because the helper runs inside the caller-owned completed
job or retry transaction, an unsafe direct input rolls back the paired terminal
transition and usage insert together. This is an internal contract failure,
not a user-correctable provider error, and remains visible to the opaque 500
handler.

SQLite enforces the same invariant independently for every writer. Each token
column carries a CHECK equivalent to:

```sql
typeof(prompt_tokens) = 'integer'
AND prompt_tokens BETWEEN 0 AND 9007199254740991
```

and likewise for `completion_tokens`. The migration MUST be created only with
`pnpm --dir server db:generate --name enforce-safe-usage-tokens`; the migration
file is generated from the schema change and `server/drizzle/meta/*` is never
hand-edited. Copying existing rows into the constrained table preserves exact
values; an invalid historical row aborts migration rather than being rounded,
clamped, deleted, or replaced with zero.

## Exact aggregation and corruption behavior

SQL and JavaScript addition must not cross an implicit floating-point boundary.
Per-model SQL sums are read in an exact integer representation, validated
against the safe range, and only then converted to `number`. Project totals and
daily buckets use checked addition: every operand and result must remain a
non-negative safe integer. SQLite integer overflow, a non-integer stored value,
or a sum above `Number.MAX_SAFE_INTEGER` is ledger corruption for the public
number-based contract.

Corruption fails the usage request through the existing opaque HTTP 500
`INTERNAL_ERROR` envelope. The API never emits a rounded count, a non-finite
number, or JSON `null` in an integer field. The successful usage shape, model
breakdown, and 30-day buckets remain unchanged.

## Shared-path coverage

Synchronous OpenAI-compatible and DashScope responses, their streaming usage
tails, proposal landing, stream landing, and retry landing all converge on the
same safe-integer and fallback rules. Focused tests use the exact boundary and
the representative invalid values `MAX_SAFE_INTEGER + 1`, `1e308`, `Infinity`,
`-1`, and `1.5`. Direct persistence tests bypass adapters deliberately to prove
the final invariant and transaction rollback. Aggregate tests insert or expose
historical corrupt values through a migration-era/raw database seam and prove
fail-loud behavior without response-shape drift.

## Options rejected

- `Number.isInteger` alone admits values that JavaScript cannot represent or
  add exactly.
- Clamping to `MAX_SAFE_INTEGER`, rounding, or storing REAL values fabricates
  usage and violates exact accounting.
- Rejecting the whole provider result for a malformed optional usage field
  discards valid generated prose even though the established missing-usage
  fallback is available.
- Validating only in adapters leaves injected providers and direct store calls
  able to corrupt the ledger.
- A database CHECK without checked aggregation cannot prevent multiple valid
  rows from producing an unsafe total.
