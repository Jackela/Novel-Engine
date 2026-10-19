## Why

A Proposal can be accepted on the server while its follow-up body read remains
pending. If the author subsequently restores a historical Revision, the old
read can replace that restored text or its save baseline. A failed old read can
also publish an obsolete failure on a workbench that has already synchronized.

## What Changes

- Bind follow-up acceptance reads and their failures to the existing Document
  and accepted-Revision authority, for manual acceptance and whole-book runs.
- Retain later accepted text, Drafts, summaries and save state when an older
  follow-up completes; retain committed acceptance records and job accounting.
- Keep ordinary current refresh failures visible as accepted-but-unsynchronized
  failures, and preserve unexpected-error diagnostics.

## Impact

Local frontend reliability correction. No change to explicit author acceptance,
whole-book authorization, server transactions, API shapes, database, dependencies
or design language.
