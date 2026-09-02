# Tasks

## 1. Permit-owned guard

- [ ] 1.1 Add failing unit tests for default and injected app/project limits,
      fixed conflict priority, project deletion interaction, and failed-acquire
      immutability.
- [ ] 1.2 Replace target-based enter/exit with opaque token-bound permits whose
      release is idempotent and cannot release a later same-target owner.
- [ ] 1.3 Convert project-exclusive ownership to the same token-bound release
      contract and preserve deletion conflict behavior without consuming
      capacity.

## 2. Configuration and error protocol

- [ ] 2.1 Add failing configuration tests for defaults, both `API_` overrides,
      integer range 1..1024, per-project <= app, process-over-file precedence,
      and failure before persistence startup.
- [ ] 2.2 Wire one resolved capacity policy into each app-owned Studio guard,
      with a structured `AppOptions` test seam and no import-layer inversion.
- [ ] 2.3 Add `OPERATION_CAPACITY_EXCEEDED` to the error SSOT and agent catalog;
      emit its stable details plus controlled `Retry-After: 5`, expose that
      header through CORS, regenerate the deliberate OpenAPI snapshot and
      `frontend/generated/api-types.ts`, and pass API-types drift validation.

## 3. Workflow coverage and zero-side-effect refusal

- [ ] 3.1 Acquire one permit around synchronous and streaming proposal work and
      hold it through response/generator and Provider cleanup.
- [ ] 3.2 Acquire one permit around review, export, and retry work and hold it
      through outcome landing plus artifact/Provider cleanup.
- [ ] 3.3 Prove project and app refusal for distinct targets, identical-target
      and deletion 409 precedence, deletion of an idle project while other
      projects fill capacity, and pre-stream JSON refusal.
- [ ] 3.4 Prove refusal invokes no Provider and creates no job/event/usage,
      snapshot/review/export evidence, artifact, manifest, cleanup intent, or
      running retry job.

## 4. Release and evidence

- [ ] 4.1 Prove permits release after success, known and unexpected failure,
      stream disconnect/drain cleanup, Provider disposal failure, export
      rollback/ack failure, and retry cleanup; prove they do not release early.
- [ ] 4.2 Re-run existing deduplication, deletion, retry, stream lifecycle,
      configuration, error-code, CORS, and OpenAPI regressions plus all owning
      server validation surfaces and the frontend API-types drift/type checks.
- [ ] 4.3 Run strict OpenSpec and independent review, then record fixed-SHA
      evidence, every skipped external gate, and the required archive order:
      fail-loud environment loading first, capacity admission second.
