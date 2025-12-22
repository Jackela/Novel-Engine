## MODIFIED Requirements

### Requirement: Authenticated Character Management
- **CHANGE**: “authenticated” requests MAY be satisfied by a first-party guest session. Character CRUD MUST be scoped to the current session/workspace boundary.

#### Scenario: Guest session can create a character
- **GIVEN** a guest session is established
- **WHEN** the session POSTs to `/api/characters` with a valid payload
- **THEN** the API persists the character inside the guest workspace and returns 201 with the created record.

#### Scenario: Guest session lists only its own characters
- **GIVEN** two guest sessions exist and each has created characters
- **WHEN** one session GETs `/api/characters`
- **THEN** it receives only the characters owned by that session/workspace (plus any documented defaults), and never sees the other session’s characters.

