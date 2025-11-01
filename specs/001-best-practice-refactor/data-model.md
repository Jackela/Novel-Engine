## Data Model — Project Best-Practice Refactor

### 1. Aggregates & Entities by Bounded Context

#### Simulation Orchestration Context
- **Campaign Aggregate**
  - **Identifiers**: `campaign_id` (UUID v4)
  - **State**: name, description, status (`draft|active|complete|archived`), turn_limit, participants (persona IDs), timeline snapshots, audit trail reference
  - **Commands**: `create_campaign`, `advance_turn`, `archive_campaign`
  - **Events**: `CampaignCreated`, `TurnAdvanced`, `CampaignArchived`
  - **Invariants**: must include ≥2 persona participants; cannot advance turns once archived
- **Turn Ledger Value Object**
  - Attributes: turn_number (int), timestamp (UTC ISO8601), action_log (list of persona actions), duration_seconds
  - Immutable; appended to campaign timeline via event sourcing stream

#### Persona Intelligence Context
- **Persona module Aggregate**
  - **Identifiers**: `persona_id` (UUID), `character_sheet_hash`
  - **State**: personality profile, decision weights, cached prompt responses (Redis key `persona:{id}:response:{turn}`), fallback policy metadata
  - **Commands**: `ingest_character_sheet`, `record_decision`
  - **Events**: `CharacterSheetBound`, `DecisionRecorded`
  - **Invariants**: prompt cache TTL 900s; fallback strategy required if Gemini API unavailable
- **Gemini Bridge Anti-Corruption Layer**
  - Ports: `PersonaAgent.gemini_client`
  - Adapters: HTTPX client with retries/backoff, graceful degradation path

#### Narrative Delivery Context
- **Narrative Chronicle Aggregate**
  - **Identifiers**: `chronicle_id` (UUID), `campaign_id`
  - **State**: narrative chapters (markdown), chronicler persona attribution, publication status, linked media assets
  - **Commands**: `compose_chapter`, `finalize_chronicle`
  - **Events**: `ChapterDrafted`, `ChroniclePublished`
  - **Invariants**: chapter ordering sequential; each chapter references at least one turn ledger entry
- **Media Asset Value Object**
  - Attributes: asset_id, storage_url (S3), media_type, checksum, accessibility_text

#### Platform Operations Context
- **Platform Control Plane Aggregate**
  - **Identifiers**: `control_plane_id` (singleton)
  - **State**: feature flags, rollout stages, SLO metrics catalogue, incident response contacts, ADR registry pointers
  - **Commands**: `toggle_flag`, `record_slo`, `register_runbook`
  - **Events**: `FlagUpdated`, `SLOBreached`, `RunbookUpdated`
  - **Invariants**: toggles require owner + rollback plan; every SLO entry links to measurement source

### 2. Relationships
- Campaign ↔ Persona module: many-to-many via campaign participant list (campaign stores persona IDs; persona aggregate records campaign memberships).  
- Campaign ↔ Narrative Chronicle: one-to-one; chronicle references campaign ID and turn ledger entries.  
- Platform Control Plane ↔ All Contexts: publishes feature flag and SLO policies consumed via read model projections.  
- Anti-Corruption Layers mediate between Persona Intelligence and external Gemini API; no other context directly accesses Gemini.

### 3. Validation & Policies
- All aggregates enforce `updated_at` timestamps (UTC) and maintain audit trail entries in event stream storage.  
- Multi-tenant isolation: enterprise tenants assigned dedicated schema/prefix; campaign and chronicle aggregates include `tenant_id` field validated on repository access.  
- Idempotency: write commands processed through idempotency table keyed by `Idempotency-Key` + tenant id.  
- Cache Keys: persona prompt caches prefixed with tenant and persona to avoid bleed (`tenant:{tenant_id}:persona:{persona_id}:turn:{turn}`).  
- Recovery: event streams persisted with PITR support; snapshot frequency every 10 turns to bound replay time.
