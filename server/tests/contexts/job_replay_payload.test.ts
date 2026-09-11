import { describe, expect, it } from "vitest";

import { exportRetryCapacityOutcome } from "../../src/contexts/studio/application/export_retry_capacity_outcome.js";
import { generationRetryCapacityOutcome } from "../../src/contexts/studio/application/generation_retry_capacity_outcome.js";
import { replayedJobPayload } from "../../src/contexts/studio/application/job_replay_payload.js";
import { jobPayload } from "../../src/contexts/studio/application/payloads.js";
import type {
  JobRecord,
  MarkJobOutcomeInput,
} from "../../src/contexts/studio/application/ports/job_records.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
  GenerationCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../../src/contexts/studio/domain/generation_capacity_policy.js";

const RESERVED_AT = new Date("2026-09-10T00:00:00.000Z");
const SETTLED_AT = new Date("2026-09-10T00:00:01.000Z");

/** A retry row exactly as the store reserves it: running, linked, one event. */
function runningRetry(overrides: Partial<JobRecord>): JobRecord {
  const base: JobRecord = {
    id: "retry-1",
    projectId: "project-1",
    documentId: null,
    kind: "proposal",
    operation: "generate",
    status: "running",
    provider: "mock",
    model: "",
    requestJson: "{}",
    resultJson: "{}",
    error: null,
    retryOfJobId: "source-1",
    createdAt: RESERVED_AT,
    updatedAt: RESERVED_AT,
    events: [
      {
        id: "event-1",
        jobId: "retry-1",
        status: "running",
        detailsJson: '{"retry_of":"source-1"}',
        createdAt: RESERVED_AT,
      },
    ],
  };
  return { ...base, ...overrides };
}

/** Field-level mirror of the store's `applyJobOutcome` write. */
function settled(row: JobRecord, outcome: MarkJobOutcomeInput): JobRecord {
  return {
    ...row,
    status: outcome.status,
    ...(outcome.resultJson === undefined ? {} : { resultJson: outcome.resultJson }),
    ...(outcome.model === undefined ? {} : { model: outcome.model }),
    error: outcome.error,
    updatedAt: outcome.now,
    events: [
      ...row.events,
      {
        id: "event-2",
        jobId: row.id,
        status: outcome.status,
        detailsJson: outcome.eventDetailsJson,
        createdAt: outcome.now,
      },
    ],
  };
}

function thrownBy(build: () => unknown): unknown {
  try {
    build();
  } catch (error) {
    return error;
  }
  throw new Error("Expected the replay payload exit to throw.");
}

describe("capacity replay contract through the replay payload exit", () => {
  it("replays a writer-settled generation capacity row as its thrown capacity error", () => {
    const reserved = runningRetry({
      documentId: "document-1",
      requestJson: '{"instruction":"","provider":"mock","base_revision_id":"revision-1"}',
    });
    // The constructor saturates observed at limit + 1, like a real refusal.
    const refusal = new GenerationCapacityExceededError(
      "prompt_bytes",
      GENERATION_PROMPT_BYTE_LIMIT,
      Number.MAX_SAFE_INTEGER,
    );
    const row = settled(reserved, generationRetryCapacityOutcome(reserved, refusal, SETTLED_AT));

    const error = thrownBy(() => replayedJobPayload(row));
    expect(error).toBeInstanceOf(GenerationCapacityExceededError);
    expect(error).toMatchObject({
      resource: "prompt_bytes",
      limit: GENERATION_PROMPT_BYTE_LIMIT,
      observed: GENERATION_PROMPT_BYTE_LIMIT + 1,
    });
  });

  it("replays a writer-settled export capacity row as its thrown capacity error", () => {
    const reserved = runningRetry({
      kind: "export",
      operation: "export",
      provider: "studio",
      requestJson: '{"format":"markdown"}',
    });
    const refusal = new ExportCapacityExceededError(
      "source_bytes",
      EXPORT_CAPACITY_LIMITS.source_bytes,
      EXPORT_CAPACITY_LIMITS.source_bytes + 99,
    );
    const row = settled(reserved, exportRetryCapacityOutcome(reserved, refusal, SETTLED_AT));

    const error = thrownBy(() => replayedJobPayload(row));
    expect(error).toBeInstanceOf(ExportCapacityExceededError);
    expect(error).toMatchObject({
      resource: "source_bytes",
      limit: EXPORT_CAPACITY_LIMITS.source_bytes,
      observed: EXPORT_CAPACITY_LIMITS.source_bytes + 1,
    });
  });

  it("passes non-capacity and shape-drifted rows through unchanged", () => {
    const completed = runningRetry({
      status: "completed",
      resultJson: '{"proposal_markdown":"prose"}',
      error: null,
    });
    expect(replayedJobPayload(completed)).toEqual(jobPayload(completed));

    const ordinaryFailure = runningRetry({
      status: "failed",
      resultJson: '{"error":"provider"}',
      error: "Provider failed.",
    });
    expect(replayedJobPayload(ordinaryFailure)).toEqual(jobPayload(ordinaryFailure));

    // Recognition requires the retry linkage: a first-run row carrying a
    // capacity-shaped result is audit evidence, not a replayable refusal.
    const generationRequest = {
      requestJson: '{"instruction":"","provider":"mock","base_revision_id":"revision-1"}',
    } as const;
    const capacityRow = settled(
      runningRetry(generationRequest),
      generationRetryCapacityOutcome(
        runningRetry(generationRequest),
        new GenerationCapacityExceededError(
          "prompt_bytes",
          GENERATION_PROMPT_BYTE_LIMIT,
          Number.MAX_SAFE_INTEGER,
        ),
        SETTLED_AT,
      ),
    );
    const firstRun = { ...capacityRow, retryOfJobId: null };
    expect(replayedJobPayload(firstRun)).toEqual(jobPayload(firstRun));

    // One drifted key in the stored result must fall back to the plain payload.
    const result = JSON.parse(capacityRow.resultJson) as Record<string, unknown>;
    result.extra_key = null;
    const drifted = { ...capacityRow, resultJson: JSON.stringify(result) };
    expect(replayedJobPayload(drifted)).toEqual(jobPayload(drifted));
  });
});
