# STUDIO CONTEXT KNOWLEDGE

## OVERVIEW

The Studio bounded context owns author sessions, projects, documents, revisions, snapshots, AI jobs/proposals, reviews, imports, and exports. Root repository rules still apply.

## STRUCTURE

```text
domain/                  # Principals, DTOs, domain errors and value rules
application/
├── ports/               # Repository and provider contracts
└── services/            # Per-capability services plus thin StudioStore facade
infrastructure/
├── repository/          # SQLAlchemy implementation split by capability
└── exporters/           # Markdown, DOCX, EPUB writers
interface/http/          # FastAPI dependencies, schemas, errors, routers
```

## WHERE TO LOOK

| Concern | Location | Owner |
|---|---|---|
| Public application facade | `application/services/facade.py` | `StudioStore` |
| Service graph assembly | `application/services/facade_base.py` | `StudioServiceRegistry` |
| Projects/documents/revisions | `application/services/*_service.py` | Capability service |
| Persistence contract | `application/ports/studio_repository.py` | Application layer |
| ORM schema | `infrastructure/models.py` | Infrastructure only |
| Repository implementation | `infrastructure/repository/` | `SqlAlchemyStudioRepository` mixins |
| Runtime provider bridge | `infrastructure/ai_provider.py` | Adapts AI context factory |
| Auth/setup/providers | `interface/http/session_router.py` | Session and CSRF boundary |
| Projects/documents/search | `interface/http/project_router.py` | CRUD/read API |
| Jobs/reviews/exports/imports | `interface/http/workflow_router.py` | Workflow API |
| Store injection | `interface/http/dependencies.py` | `StudioStoreDependency` |

## CONVENTIONS

- `StudioStore` is a compatibility coordinator. Put business behavior in the narrow service, not a new facade god-method.
- Application code depends on ports and domain types only; never import SQLAlchemy, FastAPI, settings, or concrete providers there.
- Repository methods return application/domain DTOs or primitives, not live ORM objects.
- Keep ownership/visibility scoping in repository queries and authorization decisions in services; do not rely on route-only checks.
- Route handlers validate/shape HTTP input and delegate to the store. Translate known domain errors through the existing error adapter.
- Use app-owned dependency injection. Never create or cache a `StudioStore` inside this context at import time.
- Preserve optimistic revision checks, immutable revision/snapshot links, job event history, retry lineage, and export checksum/atomic-write behavior.
- Search accepts reduced tokens only and uses parameterized FTS5. Test malicious operators, quotes, prefixes, and field syntax when changing it.
- AI author instructions are untrusted content. Preserve prompt boundaries, output sanitization, provider error normalization, and usage evidence.

## ANTI-PATTERNS

- Importing `infrastructure` or `interface` from `application`/`domain`.
- Bypassing `StudioServiceRegistry` with independently constructed services.
- Duplicating ownership predicates across repository mixins or weakening guest/owner scoping.
- Returning raw model output, ORM entities, local filesystem paths, or private payload fields through HTTP.
- Writing exports directly to their final path before validation/checksum succeeds.
- Folding `services/`, `repository/`, or routers back into monolithic files.

## TEST TARGETS

- Service behavior: `tests/unit/contexts/studio/application/` and `tests/contexts/studio/`.
- HTTP/runtime/security: `tests/apps/api/test_studio.py`.
- Full workflow: `tests/e2e/test_studio_workflow.py`.
- Reuse canonical app/store fixtures; reset settings around environment-dependent tests.
