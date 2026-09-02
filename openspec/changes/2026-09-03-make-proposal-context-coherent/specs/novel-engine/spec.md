## ADDED Requirements

### Requirement: Coherent proposal context capture

Every synchronous, streaming, and retry proposal generation MUST derive its
target document and current revision, outline and linked beat, prior chapters,
ordered volumes, and Lore entry state from one coherent database read snapshot.
The Provider task MUST represent one database state: a concurrent commit MAY be
entirely included or excluded, but MUST NOT contribute only some context
components. After capture, task assembly MUST NOT perform another database read
for proposal context.

Context capture, source-invariant validation, prompt security processing, and
bounded prompt admission MUST finish before a Provider is constructed. A
streaming response MUST NOT begin before the same admission completes. A fresh
request refused during this admission MUST create no Job, event, usage,
proposal, or revision evidence. Existing prompt content, ordering, escaping,
digest, Lore, and capacity semantics MUST remain unchanged.

#### Scenario: Concurrent context commit is never mixed

- **GIVEN** a proposal-context read snapshot has observed project state A
- **AND** another SQLite connection commits document, revision, outline/beat,
  volume, or Lore state B before the remaining context reads finish
- **WHEN** the proposal context is captured
- **THEN** every captured component comes from state A
- **AND** the next capture may observe state B without either capture mixing A
  and B

#### Scenario: Every generation path uses one capture

- **GIVEN** the same coherent project state and proposal operation
- **WHEN** generation runs synchronously, by stream, or as a proposal retry
- **THEN** each path derives its Provider task from one proposal-context capture
- **AND** no path rereads individual context components during task assembly

#### Scenario: Admission precedes Provider and stream work

- **GIVEN** context capture, source validation, or bounded prompt admission
  refuses a fresh proposal request
- **WHEN** the request runs synchronously or through the streaming endpoint
- **THEN** no Provider is constructed and no streaming response begins
- **AND** no durable workflow evidence is created

### Requirement: Proposal retry base-revision fidelity

A proposal retry MUST preserve the inherited request's `base_revision_id` as
its immutable generation base and MUST NOT silently rebase onto a newer target
revision. If the coherently captured target still points to base revision A,
the Provider task, retry request, result, and usage evidence MUST consistently
name A.

If the captured target instead points to revision B, the new retry Job MUST
finish as `failed` before prompt assembly or Provider construction with fixed
error `Proposal retry base revision is no longer current.` Its result MUST keep
an empty proposal, `base_revision_id: A`, and `accepted_revision_id: null`; its
failed event MUST identify reason `base_revision_changed` and revisions A and
B. The attempt MUST create no usage event, proposal, or revision. Same-key
replay MUST return that stored failed Job without repeating context capture or
creating evidence. A different key MUST remain a distinct attempt subject to
the same base rule.

#### Scenario: Unchanged retry base is used consistently

- **GIVEN** a failed proposal Job records base revision A
- **AND** the target's coherent current revision is still A
- **WHEN** the Job is retried
- **THEN** the Provider task is assembled from A
- **AND** the retry request, result, and usage evidence all name A

#### Scenario: Advanced target fails without silent rebase

- **GIVEN** a failed proposal Job records base revision A
- **AND** the target's coherent current revision has advanced to B
- **WHEN** the Job is retried
- **THEN** the retry Job fails with the fixed stale-base error and closed A/B
  event evidence
- **AND** no prompt is assembled, no Provider is constructed, and no proposal,
  revision, or usage evidence is created

#### Scenario: Stale retry replay is evidence-only

- **GIVEN** a keyed proposal retry already failed because A was no longer
  current
- **WHEN** the same retry key is submitted again
- **THEN** the exact stored failed Job and its events are returned
- **AND** context capture, Provider construction, Jobs, events, usage,
  proposals, and revisions do not repeat

#### Scenario: Different key does not change the replay base

- **GIVEN** a proposal source Job records base A while the target is at B
- **AND** one keyed retry has already failed the base check
- **WHEN** the source Job is retried with a different valid key
- **THEN** a distinct retry Job fails under the same immutable-A rule
- **AND** generating from B requires a new proposal request rather than a retry
  rebase
