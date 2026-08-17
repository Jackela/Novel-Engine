## MODIFIED Requirements

### Requirement: One product and version authority
The system MUST define Novel Engine as the only authoring product, MUST read
the product version from `pyproject.toml`, and MUST define product behavior in
this capability specification.

#### Scenario: Derived surfaces report the release version
- **GIVEN** the project version is `0.3.1`
- **WHEN** the API, Studio, logs, monitoring metadata, and OpenAPI are produced
- **THEN** each surface reports `0.3.1`
- **AND** none requires an independent version override
