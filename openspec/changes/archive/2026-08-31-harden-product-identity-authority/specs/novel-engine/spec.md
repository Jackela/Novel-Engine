## MODIFIED Requirements

### Requirement: One product and version authority
The server workspace package manifest MUST be the only editable
machine-readable authority for the product name `Novel Engine` and its
SemVer release version. Every other package manifest MUST omit product name
and version declarations. The API version and setup surfaces, OpenAPI,
operational CLI, Studio-visible identity, production frontend bundle, and
structured server logs MUST derive the same name and version from that
authority without an independent literal, override, or fallback. Missing,
blank, or malformed authority values MUST fail startup or build rather than
produce a fabricated identity. Product behavior MUST remain defined in the
`novel-engine` capability specification.

#### Scenario: Derived surfaces report the release version
- **GIVEN** the server manifest declares a valid product name and SemVer release version
- **WHEN** the API, setup surface, OpenAPI, CLI, Studio, production bundle, and server logs are produced
- **THEN** each surface reports the same manifest-derived name and version
- **AND** none requires an independent identity override

#### Scenario: Duplicate package authority is rejected
- **GIVEN** any non-server package manifest declares a product name or version
- **WHEN** repository SSOT validation runs
- **THEN** validation fails and identifies the duplicate declaration

#### Scenario: Invalid identity fails closed
- **GIVEN** the server manifest omits the product name or declares a blank name or malformed SemVer version
- **WHEN** the server starts or the Studio builds
- **THEN** the operation fails before serving or producing a bundle

#### Scenario: Studio and API identity cannot drift
- **GIVEN** a production Studio bundle and a running API from the same workspace
- **WHEN** their product identities are inspected
- **THEN** the visible Studio name and version equal the API identity
