## Research Log — Project Best-Practice Refactor

### 1. Bounded Context Segmentation
- **Decision**: Adopt four primary bounded contexts — Simulation Orchestration, Persona Intelligence, Narrative Delivery, Platform Operations — each anchored by a dedicated aggregate catalog and ADR (ARC-001).  
- **Rationale**: Mirrors constitution guidance, matches existing code ownership (e.g., `director_agent`, `persona_agent`, `chronicler_agent`, platform scripts) and reduces cross-context coupling discovered in current repo analysis.  
- **Alternatives Considered**:  
  - *Single monolith context*: rejected because it perpetuates ambiguity and violates Domain-Driven Narrative Core principle.  
  - *Fine-grained micro-contexts per agent*: rejected; increases coordination overhead without evidence of divergent business capabilities.

### 2. Aggregate & Port Mapping
- **Decision**: Document aggregates (Campaign, Persona module, Narrative Chronicle, Platform Control Plane) with associated commands/events and map ports/adapters (`DirectorAgent.turn_processor`, `PersonaAgent.gemini_client`, `ChroniclerAgent.storage_gateway`, `EventBus`) including anti-corruption layers for Gemini and CLI legacy tooling.  
- **Rationale**: Provides precise guardrails for refactor teams and clarifies adapter responsibilities for future CQRS adoption.  
- **Alternatives Considered**:  
  - *Ad-hoc service catalogs*: lack invariant documentation; risk regressions.  
  - *Delay port inventory until implementation*: would block contract-first workflow; principle I demands documentation upfront.

### 3. Experience API Contract Alignment
- **Decision**: Produce OpenAPI fragment (`contracts/openapi-refactor.yaml`) covering `/api/campaigns` and `/api/simulations` with rate limit headers, Idempotency-Key requirements, pagination, and RFC 7807 errors; run contract linting in CI.  
- **Rationale**: Satisfies Contract-First Experience APIs principle and ensures refactor does not break integrators (front-end dashboards, automation scripts).  
- **Alternatives Considered**:  
  - *GraphQL-only refactor*: front-end still depends on REST; forcing GraphQL now would expand scope.  
  - *Document contracts in prose only*: fails automated linting mandate and invites drift.

### 4. Data Stewardship & Persistence
- **Decision**: Maintain SQLite for local development while preparing PostgreSQL migration scripts (Alembic) for campaign metadata and runbooks; standardize Redis cache TTL (15 minutes persona prompt cache) and define tenant isolation strategy (enterprise tenants separated via schema, demo/internal via row filters).  
- **Rationale**: Enables staged rollout, aligns with constitution’s migration and tenancy requirements, and keeps current pipelines functional.  
- **Alternatives Considered**:  
  - *Immediate PostgreSQL cutover*: high risk without implementation capacity.  
  - *Continue without documented TTL/tenancy*: violates principle III and would fail audits.

### 5. Quality Engineering & Testing Workflow
- **Decision**: Expand CI to include Pact contract checks, mutation testing on aggregate mappers, Playwright regression suite for critical dashboards, and k6 smoke test for API throughput baseline; integrate checks into Constitution Gate.  
- **Rationale**: Direct response to principle IV, offers measurable assurances before code refactor begins.  
- **Alternatives Considered**:  
  - *Optional contract testing*: insufficient for preventing downstream regression; charter requires mandatory enforcement.  
  - *Manual regression notes*: do not scale, no automation.

### 6. Observability, Security & Reliability
- **Decision**: Standardize telemetry (OTel spans per aggregate interaction), structured logging fields (timestamp, level, service, traceId, spanId, userId), and define RED/USE metrics plus alert thresholds; adopt LaunchDarkly (or equivalent) feature flags for rollout with circuit breaker/resiliency patterns on HTTPX and EventBus interactions.  
- **Rationale**: Aligns with principle V and ensures refactor deliverables are deployable without compromising SLA.  
- **Alternatives Considered**:  
  - *Custom feature toggle scripts*: risk configuration drift, limited auditability.  
  - *Partial observability (logs only)*: fails to provide trace/metric correlation mandated by constitution.

### 7. Governance & Template Synchronization
- **Decision**: Update `/specs/*/plan.md`, `spec.md`, `tasks-template.md`, and Constitution Check references to embed new gates; ensure runbooks and onboarding docs reference refactor artifacts.  
- **Rationale**: Maintains single source of truth for governance (principles + documentation & knowledge stewardship).  
- **Alternatives Considered**:  
  - *Ad-hoc reminders*: susceptible to drift and bypass during crunch time.  
  - *Separate governance doc*: duplicates constitution, leading to inconsistency.
