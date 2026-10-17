## Why

Authors need to know which saved text Review and Export use, whether a Review
reported no findings, and whether copying generated text succeeded. Deleting a
Volume must also appear as project activity in the library's recent ordering.
Review currently supplies chapter statistics without the manuscript prose
needed for editorial assessment; supplying complete prose needs the existing
bounded generation-capacity contract to prevent oversized provider requests.
The trial provider also returns Chinese Proposal prose that its existing
validator refuses as incomplete, preventing an ordinary Chinese trial flow.

## What Changes

- Explain the saved-chapter source in Review and Export, with a non-blocking
  notice while the active chapter has unsaved title or body changes.
- Distinguish a successfully loaded Review with zero findings from an absent,
  pending, or failed result.
- Give Copilot and Jobs consistent copy success and manual-copy recovery
  feedback, scoped to the displayed text and latest attempt.
- Update the Project's modification time when Volume deletion succeeds, so
  recent-project ordering reflects that change.
- Send captured saved chapter Markdown, identity, and reading order to the
  Review provider as untrusted manuscript data; exclude non-chapter documents
  and stored document metadata from the prompt.
- Apply the existing 8,388,608-byte generation prompt budget to Review before
  provider construction, including structured, replayable keyed-retry
  capacity refusals.

- Complete the Chinese trial Proposal narrative so ordinary Rewrite and
  Continue outputs pass the existing prose guard without relaxing validation.

## Impact

Affected surfaces are the Review and Export panels, Copilot and Jobs copy
controls, Volume deletion and project listing, and fresh/retried Review
generation, and Chinese trial Proposal output. Review requests above the complete prompt limit now return the
existing HTTP 422 `GENERATION_CAPACITY_EXCEEDED` envelope; the public Review
response contract and generated API types must document that refusal.

No dependency, configuration, migration, deployment, or architectural change
is required. Existing autosave timing, explicit Proposal acceptance, Snapshot
identity, export behavior, and retry ownership remain in force. This change
adds neither a save prerequisite nor an automatic save before Review or Export.
