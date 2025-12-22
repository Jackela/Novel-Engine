# Design: Backend API Platform Refactor

## Principles (AI-friendly)
- **One way to do it**: one canonical app factory, one canonical place to register routers/middleware.
- **No import side effects**: importing modules should not start servers or mutate global state.
- **Explicit dependencies**: services depend on interfaces (repositories/stores), wired in the app factory.
- **Small modules, stable names**: predictable locations for routes, schemas, and services.

## Target Structure (illustrative)
```
src/api/
  app.py                  # create_app()
  settings.py             # typed settings/env
  deps.py                 # dependency providers
  errors.py               # error models + handlers
  routers/
    characters.py
    sessions.py
    simulations.py
    events.py
  services/
    character_service.py
    session_service.py
  stores/
    character_store.py    # interface
    filesystem_store.py   # impl (future change)
```

## Compatibility Strategy
- Keep existing launch scripts/files as thin wrappers that call `create_app()` until fully migrated.
- Prefer additive migration: move one router at a time, keep endpoints stable, and prove equivalence via tests.

## Contract Strategy
- Schemas: Pydantic models are the single source of truth for OpenAPI.
- Errors: provide a stable error envelope with codes so frontend can handle predictably.

