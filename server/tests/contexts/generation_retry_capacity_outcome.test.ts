import { describe, expect, it } from "vitest";

import { replayedGenerationCapacityError } from "../../src/contexts/studio/application/generation_retry_capacity_outcome.js";
import type { JobRecord } from "../../src/contexts/studio/application/ports/studio_store.js";

const FIXED_PROMPT_LIMIT = 8_388_608;

function capacityRetry(limit: number, observed: number): JobRecord {
  const now = new Date("2026-09-03T00:00:00.000Z");
  return {
    id: "retry-1",
    projectId: "project-1",
    documentId: "document-1",
    kind: "proposal",
    operation: "generate",
    status: "failed",
    provider: "mock",
    model: "",
    requestJson: '{"base_revision_id":"revision-1"}',
    resultJson: JSON.stringify({
      proposal_markdown: "",
      base_revision_id: "revision-1",
      accepted_revision_id: null,
      capacity_error: {
        code: "GENERATION_CAPACITY_EXCEEDED",
        resource: "prompt_bytes",
        limit,
        observed,
      },
    }),
    error: "Generation capacity exceeded.",
    retryOfJobId: "source-1",
    createdAt: now,
    updatedAt: now,
    events: [],
  };
}

describe("generation retry capacity replay", () => {
  it("replays only the fixed prompt-capacity evidence", () => {
    expect(
      replayedGenerationCapacityError(capacityRetry(FIXED_PROMPT_LIMIT, FIXED_PROMPT_LIMIT + 1)),
    ).toMatchObject({
      limit: FIXED_PROMPT_LIMIT,
      observed: FIXED_PROMPT_LIMIT + 1,
    });

    expect(replayedGenerationCapacityError(capacityRetry(1, 2))).toBeNull();
  });
});
