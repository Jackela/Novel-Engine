## 1. Protect current Draft state

- [x] 1.1 Add failing PageModel cases for pending and failed accepted-body reloads.
- [x] 1.2 Reuse the current owner's accepted baseline for guard/guidance and verify clean-owner/revert controls.

## 2. Reveal completed Review retries

- [x] 2.1 Reproduce stale Review history after a completed Jobs retry.
- [x] 2.2 Invalidate existing Review resources with no inactive prefetch; cover stale outcomes, non-Review/failed retries and Jobs refresh failure.

## 3. Reject synchronous provider non-completion

- [x] 3.1 Reproduce non-completed Responses landing as successful Proposals through the API.
- [x] 3.2 Reject the documented statuses without raw diagnostic leakage, automatic retry, or accepted Revision; preserve completed/legacy responses.

## 4. Verify before archiving

- [x] 4.1 Run affected regression, full applicable package/contract checks, emitted-backend browser workflows and isolated Docker persistence checks.
- [x] 4.2 Independently review the fixed candidate against standards and this change.
- [x] 4.3 Verify required CI on the exact implemented candidate before archiving this change.

After archiving, revalidate the final candidate and its required checks before merge.
Merged-main CI, recovery material, and task-only cleanup are recorded in the external closeout evidence.
