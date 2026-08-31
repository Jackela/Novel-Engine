# Design: atomic review outcomes

## Ownership

`ReviewService` owns provider lifecycle and converts one read-only source into
an uneffected evaluation DTO. A dedicated review-outcome store port owns the
atomic persistence invariant. The Drizzle adapter owns relational writes and
the persisted review-job JSON; HTTP code continues to project the returned job
and assessment records.

## Read, evaluate, land

The source read runs in one short read transaction and returns every current
document/revision pair plus captured title, metadata, content, and dense reading
position. It writes no snapshot row and holds no transaction while awaiting the
provider.

After a valid provider result, one immediate write transaction:

1. rechecks project ownership and every captured document/revision pair;
2. inserts the `review` project snapshot and its snapshot documents;
3. inserts the assessment and its validated issues;
4. either inserts a completed fresh job/event or transitions the named running
   review retry to completed with the actual model;
5. reloads and returns both persisted records.

Any failure rolls back the whole write transaction. Provider failures occur
before this transaction and therefore leave no provisional snapshot. Fresh
known failures create one failed terminal job; retry failures transition only
the already-running retry job.

## Concurrency

Edits after the source read do not rewrite the captured revision: immutable old
revisions remain eligible for the final snapshot. If a captured document or
revision is deleted first, finalization raises the dedicated source-invalidated
error and leaves no review evidence. If finalization commits first, the normal
snapshot foreign-key guard protects the successful evidence and the competing
document delete is refused. If the project is deleted first, scoping fails and
no job or review row is recreated.

## Failure classification

Known provider errors, the invalid top-level findings envelope, and a captured
source invalidated by concurrent deletion may become an honest failed job.
Invalid individual finding entries remain filtered by the existing closed
dimension/document rules. Unexpected programming, serialization, port, and
persistence errors remain visible; they are never relabeled as provider
failures. Provider disposal runs for both fresh and retry evaluation and its
failure is reported without replacing the selected workflow outcome.

## Legacy repair

A generated data migration deletes only `reason = 'review'` snapshots for which
no assessment references the snapshot. Cascading removal clears their snapshot
documents. Snapshots referenced by completed assessments remain immutable and
continue to protect their historical revisions.
