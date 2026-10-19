## ADDED Requirements

### Requirement: Committed Proposal refresh ordering

After a Proposal acceptance commits, its follow-up reads MUST NOT replace a
later accepted Revision, its Document summary, the active Draft or the save
baseline. A superseded read failure MUST NOT replace the current workbench's
error or prevent subsequent saving. This ordering MUST hold for explicit
single-Proposal acceptance and the existing authorized whole-book run.

The committed acceptance and its Job accounting MUST remain recorded even when
the follow-up is superseded. A still-current read failure MUST remain visible
as an accepted Proposal whose local refresh failed. Existing unexpected-error
diagnostics MUST remain available. Switching Documents MUST NOT allow an older
acceptance read to roll back an already newer summary; returning to that
Document MUST use its committed Revision or a newer server Revision.

#### Scenario: History restore supersedes an acceptance read

- **GIVEN** a Proposal acceptance committed and its follow-up body read remains pending
- **AND** the author successfully restores an earlier historical Revision, creating a newer accepted Revision
- **WHEN** the old acceptance read succeeds or fails
- **THEN** the restored Revision and any subsequent Draft remain the current baseline and text
- **AND** the old result does not overwrite the Document summary, publish an obsolete error or block the next save

#### Scenario: Leaving the Document does not roll back its restored summary

- **GIVEN** a later restore has already advanced a Document beyond a pending acceptance read
- **WHEN** the author selects another Document and the old read completes
- **THEN** neither the active Document nor the restored Document's summary is replaced by the older result
- **AND** returning loads the restored Revision or a newer server Revision

#### Scenario: Current acceptance refresh failures remain actionable

- **GIVEN** a Proposal acceptance committed and no later accepted Revision superseded its refresh
- **WHEN** the follow-up read fails
- **THEN** the Studio reports that acceptance succeeded but local refresh failed
- **AND** the acceptance record and committed chapter count are retained
