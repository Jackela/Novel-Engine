# Fail loudly when `.env.local` cannot be read

## Why

Configuration currently treats every `.env.local` read or parse exception as
if the file did not exist. A directory, permission failure, I/O fault, or
future parser defect can therefore boot the server with defaults and process
variables while hiding the failed configuration authority.

## What changes

- Treat only `ENOENT` as the optional-file case.
- Preserve every other filesystem error unchanged so startup fails before any
  database, backup, migration, reconciliation, or listener side effect.
- Keep parsing outside the filesystem catch boundary so parser defects remain
  visible and process variables override only a successfully read file.

## Impact

- Non-`ENOENT` configuration-file failures become startup errors for CLI
  commands that load operational configuration, including `serve` before it
  composes the API, instead of silently selecting defaults.
- No HTTP shape, database schema, migration, dependency, environment key, or
  configuration precedence changes.

## Non-goals

- No new `.env.local` syntax, stricter line validation, or alternate env file.
- No change to process-environment precedence or configuration defaults.
- No asynchronous configuration loader or dependency.

## Validation

- Missing-file, directory-path, and process-override configuration tests.
- Focused configuration and CLI startup tests, full server gates, strict
  OpenSpec, and fixed-SHA evidence.
