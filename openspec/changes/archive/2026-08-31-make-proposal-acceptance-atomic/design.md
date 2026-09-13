# Design: atomic proposal acceptance

## Ownership

Proposal acceptance is one semantic persistence command. The application
service owns authentication-to-scope mapping and response projection. The
store port owns the atomic invariant; the Drizzle adapter owns the transaction,
relational writes, FTS projection, and persisted job JSON.

## Transaction

The adapter begins an immediate SQLite transaction before it reads the job.
Inside that transaction it:

1. verifies project ownership and that the job is a completed proposal for a
   document in that project;
2. returns the job unchanged when it already names an accepted revision;
3. validates non-empty proposal content and its stored base revision;
4. repairs a legacy split state when an existing `ai-accepted` revision for the
   same document carries this job's `ai_job_id`;
5. otherwise checks the document base revision, inserts the next immutable
   revision, advances the document and project, refreshes FTS, and writes the
   accepted revision id into the job result.

An injected failure in the final job binding therefore rolls back the revision,
document pointer, project timestamp, and FTS refresh. Immediate transaction
entry serializes competing writers before either can make its idempotence
decision.

## Compatibility repair

Old process interruptions may already have committed the revision half of the
former split workflow. Before reporting a base-revision conflict, the command
looks for an `ai-accepted` revision whose metadata names the same job. It binds
that exact immutable revision to the job without creating another revision.
Author revisions cannot satisfy this repair rule.

## Error behavior

The command preserves the existing not-found, invalid-operation, and revision
conflict categories. Unexpected persistence errors remain visible and roll the
whole transaction back.
