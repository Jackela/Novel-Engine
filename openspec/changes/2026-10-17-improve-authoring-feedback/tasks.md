## 1. Change contract

- [x] 1.1 Draft the approved authoring-feedback and Review-input requirements
  against baseline `45ad1afbf5660f0c1863246cae17cd0d6b372cad`.
- [x] 1.2 Pass strict OpenSpec validation for the change (`pnpm spec:validate`:
  3 passed, 0 failed; log: `/tmp/ne-feedback-20261017/spec/spec-validate.log`).

## 2. Saved-source and Review result feedback

- [ ] 2.1 Add saved-chapter source text and derive the non-blocking notice from
  actual active-chapter Draft title/body changes.
- [ ] 2.2 Verify waiting, saving, failed, conflicted, reverted, saved, and
  Document/Project-switch states without introducing a save prerequisite.
- [ ] 2.3 Show the zero-finding statement only for successfully loaded Review
  detail and verify pending, failure, no-review, and nonzero-result boundaries.

## 3. Copy feedback

- [ ] 3.1 Give Copilot and Jobs shared success and retryable manual-copy
  feedback while keeping unexpected failures observable.
- [ ] 3.2 Verify missing Clipboard API, known permission refusal, successful
  retry, overlapping attempts, and text-identity changes in both consumers.

## 4. Volume deletion freshness

- [ ] 4.1 Update Project modification time with a successful Volume deletion.
- [ ] 4.2 Verify recent-project order and unchanged timestamp after refused
  or rolled-back deletion, preserving existing chapter reassignment behavior.

## 5. Review manuscript and prompt capacity

- [ ] 5.1 Supply full captured saved chapter Markdown with identity and
  reading order, excluding non-chapter documents and stored document metadata.
- [ ] 5.2 Enforce the complete system/user prompt byte limit before provider
  construction, without truncation and without fresh-refusal workflow evidence.
- [ ] 5.3 Retain structured capacity failure on a reserved Review retry and
  replay the same key's 422 without repeated source/provider work.
- [ ] 5.4 Verify complete prose, source identity, untrusted text boundaries,
  multibyte/escaped bytes, exact-limit admission, over-limit refusal, and
  same-key versus different-key retry behavior.
- [ ] 5.5 Regenerate and check the OpenAPI baseline and frontend API types for
  the Review capacity-refusal response.

## 6. Integrated evidence

- [ ] 6.1 Run the affected frontend and backend checks on the integrated
  candidate and inspect the complete diff.
- [ ] 6.2 Exercise the affected authoring feedback in the browser and record
  actual results, skipped checks, fixed candidate identity, and remaining
  acceptance gates under the repository's change-evidence contract.
