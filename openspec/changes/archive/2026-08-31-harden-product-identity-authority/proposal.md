# Harden the product identity authority

## Why

The server manifest is declared as the release authority, but the SSOT gate
and API test repeat the current version, the frontend can fall back to a
fabricated version, and visible product names are copied across components.
The repository can therefore pass every current gate while shipping a Studio
whose name or version disagrees with the API.

## What Changes

- Make the server package manifest the only editable machine-readable source
  for both product name and SemVer release version.
- Fail server and frontend startup/build when that identity is missing or
  malformed; prohibit independent package declarations and fallbacks.
- Project the same identity into the API, setup surface, OpenAPI, CLI, Studio,
  production bundle, and structured server logs.
- Replace literal-version checks with relationship tests against the authority.

## Impact

- Adds a `productName` metadata field to `server/package.json`; no dependency
  or release version changes.
- Changes internal identity wiring and validation only; no response shape or
  database migration changes.
- Removes the previous unimplemented monitoring-metadata claim from the
  product contract while retaining observable log identity.
