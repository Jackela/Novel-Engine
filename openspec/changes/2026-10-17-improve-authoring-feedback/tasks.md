## 1. Change contract

- [x] 1.1 Draft the approved authoring-feedback and Review-input requirements
  against baseline `45ad1afbf5660f0c1863246cae17cd0d6b372cad`.
- [x] 1.2 Pass strict OpenSpec validation for the change (`pnpm spec:validate`).

## 2. Saved-source and Review result feedback

- [x] 2.1 Add saved-chapter source text and derive the non-blocking notice from
  actual active-chapter Draft title/body changes.
- [x] 2.2 Verify waiting, saving, failed, conflicted, reverted, saved, and
  Document/Project-switch states without introducing a save prerequisite.
- [x] 2.3 Show the zero-finding statement only for successfully loaded Review
  detail and verify pending, failure, no-review, and nonzero-result boundaries.

## 3. Copy feedback

- [x] 3.1 Give Copilot and Jobs shared success and retryable manual-copy
  feedback while keeping unexpected failures observable.
- [x] 3.2 Verify missing Clipboard API, known permission refusal, successful
  retry, overlapping attempts, and text-identity changes in both consumers.

## 4. Volume deletion freshness

- [x] 4.1 Update Project modification time with a successful Volume deletion.
- [x] 4.2 Verify recent-project order and unchanged timestamp after refused
  or rolled-back deletion, preserving existing chapter reassignment behavior.

## 5. Review manuscript and prompt capacity

- [x] 5.1 Supply full captured saved chapter Markdown with identity and
  reading order, excluding non-chapter documents and stored document metadata.
- [x] 5.2 Enforce the complete system/user prompt byte limit before provider
  construction, without truncation and without fresh-refusal workflow evidence.
- [x] 5.3 Retain structured capacity failure on a reserved Review retry and
  replay the same key's 422 without repeated source/provider work.
- [x] 5.4 Verify complete prose, source identity, untrusted text boundaries,
  multibyte/escaped bytes, exact-limit admission, over-limit refusal, and
  same-key versus different-key retry behavior.
- [x] 5.5 Regenerate and check the OpenAPI baseline and frontend API types for
  the Review capacity-refusal response.
- [x] 5.6 Restrict the Review capacity response contract to prompt bytes and
  retain the separate validation-error alternative; verify the published schema.

## 6. Chinese trial Proposal completeness

- [x] 6.1 Reproduce the short Chinese trial narrative's refusal through the
  real prose guard and preserve the original failed stream evidence.
- [x] 6.2 Complete the deterministic Chinese narrative without weakening the
  existing prose guard; verify structured and streamed Rewrite and Continue.
- [x] 6.3 Verify a real Chinese Proposal preview and explicit author acceptance
  in the browser, including unchanged accepted text before Accept.

## 7. Integrated evidence

- [x] 7.1 Run the affected frontend and backend checks on the integrated
  candidate and inspect the complete diff.
- [x] 7.2 Exercise the affected authoring feedback in the browser and record
  actual results, skipped checks, fixed candidate identity, and remaining
  acceptance gates under the repository's change-evidence contract.

Local product validation completed on `186b3ff05167410aa2029ae37f82d1ea238b832b`.
CI, real-provider checks, and author acceptance remain separate. The change
remains live until its CI and archival gates close.


## 8. Captured-chapter finding identity

- [x] 8.1 Reproduce non-chapter findings at the public coercion boundary,
  retain a legal chapter finding, then apply the smallest identity filter.
- [x] 8.2 Verify fresh and retried HTTP Reviews reject captured non-chapter,
  absent, and foreign Document identities in detail, summary, and Job results.
- [x] 8.3 Verify zero admissible findings still completes and the complete
  Snapshot capture and ownership paths remain unchanged.
