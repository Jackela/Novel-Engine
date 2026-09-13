# Design: bounded exact export-source revalidation

## Existing failure boundary

The application captures one ordered source, renders its file, and then enters
one immediate SQLite transaction to revalidate that source and land every
discoverable database record. Revalidation currently sends the project id and
every captured revision id through one `IN` predicate. The project binding
means a collection of 32,766 revision ids already requires 32,767 variables,
one above this repository's SQLite build limit.

The publication protocol correctly compensates the file when database landing
throws, but parameter exhaustion is neither source invalidation nor an
operational artifact-write failure. It therefore escapes as an opaque 500 and
does not produce the intended valid export outcome.

## Chosen approach

Revalidation first checks the captured collection's structural identity, then
partitions its revision ids into fixed-size groups whose complete statement
parameter count stays below SQLite's supported budget. Every group is queried
through one shared production helper on the transaction handle already owned
by export landing. Results are accumulated by the compound document/revision
identity and compared with every captured source entry only after all groups
have completed.

The grouping is a query-execution detail, not partial validation:

- every group runs inside the same existing `IMMEDIATE` transaction;
- no group may commit, open a nested transaction, or return a partial source;
- every captured entry must have exactly one matching persisted revision owned
  by the requested project and document;
- persisted content and metadata must equal the captured values;
- aggregation must preserve full cardinality and reject duplicate document or
  revision identities as invariant defects instead of collapsing them in a set
  or map;
- only the complete aggregate decision may allow snapshot reuse or creation.

The production helper owns the binding budget. Tests inspect or instrument
that same helper so a later refactor cannot reintroduce an all-identifiers
statement while a copied test query remains green.

## Empty and duplicate collections

An empty collection issues no revision lookup. The surrounding export contract
still rejects a project with no chapter as 422 before any file or database
evidence is published.

A duplicate document identity, duplicate revision identity, or conflicting
compound document/revision identity cannot be produced by a valid internal
capture. It remains a visible invariant defect, not a fabricated
source-invalidated outcome. It is never deduplicated into an apparently valid
smaller collection and never reaches snapshot reuse or creation.

## Transaction and failure semantics

The immediate transaction continues to contain project scope validation,
complete source revalidation, snapshot reuse or creation, snapshot-document
inserts, artifact metadata, and the completed Job/event outcome. A missing or
wrongly scoped identity observed by any group invalidates the whole source. A
persisted immutable-content or metadata mismatch remains a visible invariant
defect. In either case no database evidence commits.

The rendered file remains outside SQLite and precedes database landing. Any
landing failure continues through the existing identity-aware rollback. A
cleanup failure is reported without replacing the original failure, and the
durable cleanup journal/recovery protocol remains unchanged.

Fresh and retry exports retain their current source-invalidated behavior. This
change does not classify arbitrary database or programming errors as valid
failed Jobs.

## Boundary evidence

The regression matrix uses complete production source records at 32,765,
32,766, and 32,767 revisions. The middle case is essential: one project
parameter plus 32,766 revision parameters is the first value that fails in the
current single-statement design. Every case exercises the actual export store
revalidation and completes without `too many SQL variables` when its source is
valid.

Focused failure cases delete or change an entry in a non-initial group to prove
the implementation does not validate only a prefix. Duplicate and empty
fixtures prove structural handling before query construction. Failure injection
after revalidation continues to prove snapshot, artifact, Job, and event writes
roll back together and the published file is compensated.

## Options rejected

- Raising SQLite's compile-time variable limit makes correctness depend on one
  binary build and merely moves the failure threshold.
- Truncating or sampling revision ids can publish a file whose complete source
  was never validated.
- Running each group in its own transaction permits source changes between
  groups and breaks the one-outcome publication contract.
- Persisting a snapshot before rendering avoids the late query but violates the
  established rule that failed rendering creates no snapshot evidence.
- A temporary-table redesign adds lifecycle and cleanup surface without being
  necessary for bounded reads under one existing transaction.
