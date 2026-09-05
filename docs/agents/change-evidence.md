# Change Evidence

Use this contract when preparing, reviewing, or integrating a change. It keeps
the fixed comparison point, executed validation, CI state, and human judgment
separate. A candidate becomes verified only for the evidence levels that have
actually closed.

The command owners are the current package scripts and
`.github/workflows/ci.yml`. Read them at execution time. This document defines
evidence semantics; it does not cache their command lists.

## Evidence record

Every recorded check names:

- the candidate commit SHA;
- the exact command or human flow that ran;
- the result and relevant environment;
- a replayable log, artifact, or workflow link when one exists;
- any skipped portion and its reason.

A result from another SHA is historical evidence. Rebase, conflict resolution,
or follow-up edits require the affected checks to run again on the new
candidate.

## Evidence levels

### Targeted

Targeted evidence exercises the smallest surface that owns the change: a unit
or service test, API injection flow, schema gate, browser workflow, or other
focused reproduction. For a defect, capture the failing baseline or otherwise
record the previous behavior before the fix when practical. Completion means
the changed behavior and its nearest regression boundary pass on the candidate
SHA.

### Local full

Local-full evidence runs the repository's current full local validation
surfaces that apply to the change. Resolve them from live package scripts and
repository instructions, record what actually ran, and include failures or
omissions. A local-full pass is candidate evidence; it is not a CI result and
does not close a browser, platform, or human gate that was not exercised.

### CI required

CI-required evidence is a successful result for every check required by live
branch protection on the exact candidate SHA. Resolve that list from GitHub at
review time: repository workflows own what their jobs execute, while the
required-check list remains external state and must not be cached here. Record
each required context and its workflow or analysis URL. A green `validate` job
does not substitute for a required container or code-scanning context, and a
pending, cancelled, skipped, stale-SHA, or manually described run is not a
pass.

### Human acceptance

Human-acceptance evidence records judgment that automation cannot supply, such
as product-flow suitability, visual review, keyboard or screen-reader use,
target-player behavior, migration approval, or release authorization. Record
whether acceptance is required, the named owner, date, surface exercised, and
outcome. Automated checks, screenshots, and agent review remain supporting
evidence and never imply human acceptance.

## Skips and residual risk

Use `not run`, `blocked`, or `not applicable` explicitly. Every expected but
unfinished check needs a reason, the residual risk, an owner, and a concrete
closure condition. `Not applicable` names the scope fact that makes the check
irrelevant. Empty cells, absent rows, and future-tense plans do not count as
evidence.

## Multi-agent changes

One integrator owns the candidate and the final evidence record.

1. The integrator fixes the baseline SHA before dispatch and gives every
   subagent that same comparison point.
2. Each subagent declares a bounded read set and a unique write set. Read sets
   may overlap; write sets do not. A task without an assigned write set is
   read-only.
3. Shared governance, aggregation, or conflict-prone files stay in the
   integrator's write set. If overlap becomes necessary, subagents stop at a
   finding or patch proposal and the integrator performs the edit.
4. A moving HEAD never silently changes the baseline. The integrator either
   preserves the fixed comparison or records a new baseline and rechecks
   affected findings.
5. After integrating every wave, the integrator reviews the complete diff,
   reruns the affected targeted checks and applicable local-full surfaces, and
   records CI only after it completes on the final candidate SHA.

Subagent reports are observations until the integrator verifies them against
the shared candidate. Subagent completion, a clean diff, and a local commit do
not promote evidence status by themselves.

## Completion

A change is ready for review when the PR records one fixed baseline, one
candidate SHA, the actual targeted and applicable local-full evidence, every
skip with an owner, and the human-acceptance state. It is ready for protected
branch integration only when required CI is green on that candidate and every
release-blocking human gate is accepted or explicitly held by its owner.
