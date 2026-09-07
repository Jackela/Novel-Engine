# Design: one proposal-context snapshot and an explicit retry anchor

## Coherent capture boundary

Add one focused application port operation, `readProposalContext`, returning an
immutable `ProposalContextSource`. The value contains the scoped project id,
the target document paired with its exact current revision, every project
document paired with the revision current at capture in the existing canonical
composite reading order, and the ordered volumes. That document order remains
volume position, document position, creation time, then id; it is captured once
and is the sole tie-break order consumed by resident and Lore derivation.
Document rows already carry the target beat reference, Lore aliases, and Lore
lifecycle status; outline/beat resolution, prior-story ordering, Lore selection,
matching, sanitization, and bounded rendering therefore remain pure
application work over the captured value.

The Drizzle adapter performs project scoping, document/current-revision reads,
and volume reads inside one read transaction. The transaction ends as soon as
the plain value is materialized. It is never held across prompt rendering,
Provider construction, network work, SSE delivery, or Job landing. SQLite's
read snapshot is the coherence authority: a concurrent commit may be wholly
before or wholly after capture, but cannot contribute only some prompt inputs.

`buildProposalTask` accepts the captured value rather than a store plus ids.
This deepens the module boundary: callers cannot accidentally add a late store
read, and the one captured target revision supplies manuscript bytes, task
metadata, request base, result base, and usage evidence. Existing incremental
prompt writing, the complete 8 MiB byte admission, prompt-data encoding, digest
bounds, and linear Lore plan remain downstream and byte-identical.

## Deterministic concurrency proof

The infrastructure test opens two connections to the same temporary SQLite
database in WAL mode. A focused proposal-context store part exposes the same
protected no-op test seam pattern already used for atomic landing failures. A
test subclass commits coordinated document, outline/Lore, beat, and volume
changes through connection B after connection A has made its first scoped read
but before A completes capture. The first capture must contain only epoch A;
the next capture must contain only epoch B. The test uses this explicit
checkpoint, not timing, polling, or sleeps.

Application tests also use a store whose legacy individual read methods fail if
called. Synchronous, streaming, and retry paths must each call the single
capture operation once and hand byte-identical task context to their Provider.
Fixtures with equal-rank Lore matches across volumes pin the captured canonical
document order so an unordered database result cannot silently change promotion.

## Entry-point ordering

For a fresh synchronous request the order is: validate operation/provider name,
acquire the existing in-process permit, capture context, assemble and admit the
bounded task, then construct the Provider. Any capture, source-invariant, or
capacity failure precedes durable Job evidence.

Streaming performs the same steps on the generator's first pull. The HTTP
adapter continues to pull once before hijacking the reply, so capture and all
admission checks can return their normal JSON error before SSE begins.

Retry may first reserve its durable running Job because keyed retry identity
must survive execution. Same-key terminal replay returns the stored Job before
context capture. Only a newly created proposal retry captures context and may
proceed to task assembly and Provider construction.

## Retry base policy

The inherited request payload is authoritative, matching the existing Job
retry contract. Its `base_revision_id` A is the immutable replay anchor; the
retry never rewrites it to a later revision. After coherent capture:

- If the captured target still points to A, every task field and terminal
  request/result/usage evidence uses A.
- If the target points to B, the retry transitions atomically from `running` to
  `failed` with the fixed error `Proposal retry base revision is no longer
  current.` Its proposal result remains empty with `base_revision_id: A` and
  `accepted_revision_id: null`. The failed event records only the fixed error,
  reason `base_revision_changed`, `base_revision_id: A`, and
  `current_revision_id: B`. The retry Job retains the provider/model identity
  inherited at claim time; the stale-base outcome does not fabricate a new
  model value or clear the source identity.

A target with no current revision is not an A/B mismatch. It retains the
existing explicit `Document has no current revision.` failure and does not
fabricate stale-base evidence without a captured revision B.

The stale-base outcome is an execution result, so the retry endpoint returns
the normal terminal Job response. It creates no proposal revision or usage
event and constructs no Provider. Same-key replay returns that exact stored Job
without recapture or new evidence. A different key is a distinct attempt but
is subject to the same immutable base check; generating from B requires a new
proposal request, not an audit-obscuring retry rebase.

Missing or malformed inherited request context remains the existing explicit
invalid-operation failure. A scoped project/document miss retains the existing
non-disclosing error behavior. Unexpected persistence or invariant defects stay
visible and are not converted into a fabricated stable outcome.

## Options rejected

- Comparing timestamps or rereading after assembly cannot prove which mixture
  was observed and adds retry loops around an avoidable race.
- Holding a transaction across Provider or SSE work would block database
  progress for unbounded external latency.
- Capturing documents and volumes separately and attaching a timestamp does not
  make those reads one snapshot.
- Silently rebasing retry request evidence from A to B contradicts the existing
  inherited-payload contract and hides which author text was retried.
- Generating from immutable A while calling B the current target produces a
  proposal that is already ineligible for acceptance and still mixes semantic
  epochs.
- A database-wide generation epoch or new snapshot table adds migration and
  persistence machinery when SQLite read isolation plus an immutable value is
  sufficient.
- Project and catalog pagination solve response-size concerns, not proposal
  read coherence, and remain separate changes.
